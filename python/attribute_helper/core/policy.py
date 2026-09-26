"""Scope declarations and violation checks (docs/attrib_scope_policy.md §7)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase

from .model import AttribKey, Snapshot
from .report import LeakReport

_RENAME = re.compile(r"\s*->\s*")
_LINE = re.compile(r"^\s*(in|inout|out)\s*:(.*)$", re.IGNORECASE)


@dataclass(frozen=True)
class OutEntry:
    name: str                  # name (or pattern) inside the scope
    rename: str | None = None  # "a -> b": returned as b


@dataclass(frozen=True)
class Declaration:
    in_: list[str]
    inout: list[str]
    out: list[OutEntry]


def parse_list(text: str) -> list[str]:
    return _RENAME.sub("->", text).replace(",", " ").split()


def _out(tokens: list[str]) -> list[OutEntry]:
    return [OutEntry(*t.split("->", 1)) if "->" in t else OutEntry(t) for t in tokens]


def from_lists(in_: str, inout: str, out: str) -> Declaration:
    """From the three spare parameters of a subnet or HDA."""
    return Declaration(parse_list(in_), parse_list(inout), _out(parse_list(out)))


def from_comment(comment: str) -> Declaration | None:
    """From a network box comment: `in:`, `inout:`, `out:` lines. None if there are none."""
    found: dict[str, str] = {}
    for line in comment.splitlines():
        m = _LINE.match(line)
        if m:
            found[m.group(1).lower()] = m.group(2)
    if not found:
        return None
    return from_lists(found.get("in", "*"), found.get("inout", ""), found.get("out", ""))


def _is_pattern(name: str) -> bool:
    return any(c in name for c in "*?[")


def matches(key: AttribKey, patterns: list[str]) -> bool:
    """Houdini-style: later entries win; `^x` excludes; `group:x` only matches groups."""
    is_group = key.cls.startswith("group:")
    hit = False
    for p in patterns:
        exclude = p.startswith("^")
        p = p[1:] if exclude else p
        wants_group = p.startswith("group:")
        if wants_group != is_group:
            continue
        if fnmatchcase(key.name, p[len("group:"):] if wants_group else p):
            hit = not exclude
    return hit


@dataclass(frozen=True)
class Violation:
    kind: str  # undeclared leak | undeclared write | undeclared delete | missing output | collision
    name: str
    cls: str = ""


def check(decl: Declaration, report: LeakReport, entries: list[Snapshot], exit: Snapshot
          ) -> list[Violation]:
    """Violations of one exit's leak report. Unknown (rebuilt) keys are never violations."""
    out_names = [e.name for e in decl.out]
    # Literal out names that are written or deleted are reported once, as a collision or a
    # missing output below, not also as an undeclared write or delete.
    literal_out = {n for n in out_names if not _is_pattern(n)}
    found = [Violation("undeclared leak", k.name, k.cls) for k in report.leaked
             if not matches(k, out_names)]
    found += [Violation(kind, k.name, k.cls)
              for kind, keys in (("undeclared write", report.written),
                                 ("undeclared delete", report.deleted))
              for k in keys if not matches(k, decl.inout) and _display(k) not in literal_out]
    at_exit = {_display(k) for k in exit.attribs}
    at_entry = {_display(k) for e in entries for k in e.attribs}
    inout_keys = {_display(k) for e in entries for k in e.attribs if matches(k, decl.inout)}
    for entry in decl.out:
        if _is_pattern(entry.name):
            continue
        if entry.name not in at_exit:
            found.append(Violation("missing output", entry.name))
        elif entry.rename is None and entry.name in at_entry and entry.name not in inout_keys:
            found.append(Violation("collision", entry.name))
    return found


def _display(key: AttribKey) -> str:
    """The name an out entry uses for a key: `group:x` for groups."""
    return f"group:{key.name}" if key.cls.startswith("group:") else key.name

