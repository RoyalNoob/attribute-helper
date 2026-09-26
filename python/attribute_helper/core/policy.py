"""Intended findings: which leak-report findings the user marked as intended.

Stored as text, one finding per line: `<scope> <kind> <class> <name>`, where scope is `.` for
the subnet/HDA that holds the list, or a network box name. Names never contain spaces.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import AttribKey
from .report import LeakReport

KINDS = ("leaked", "written", "deleted", "rebuilt")  # the LeakReport fields
SELF = "."


@dataclass(frozen=True, order=True)
class Finding:
    kind: str  # one of KINDS
    key: AttribKey


def findings(report: LeakReport) -> list[Finding]:
    return [Finding(kind, key) for kind in KINDS for key in getattr(report, kind)]


def parse(text: str) -> dict[str, set[Finding]]:
    """scope -> intended findings. Malformed lines are ignored."""
    out: dict[str, set[Finding]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[1] in KINDS:
            scope, kind, cls, name = parts
            out.setdefault(scope, set()).add(Finding(kind, AttribKey(cls, name)))
    return out


def dump(by_scope: dict[str, set[Finding]]) -> str:
    return "\n".join(f"{scope} {f.kind} {f.key.cls} {f.key.name}"
                     for scope in sorted(by_scope) for f in sorted(by_scope[scope]))


def toggle(text: str, scope: str, finding: Finding, intended: bool) -> str:
    """The stored text with `finding` added to or removed from `scope`'s intended set."""
    by_scope = parse(text)
    found = by_scope.setdefault(scope, set())
    (found.add if intended else found.discard)(finding)
    return dump({s: f for s, f in by_scope.items() if f})
