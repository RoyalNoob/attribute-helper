"""Scopes: a subnet, an HDA, or a network box (docs/attrib_scope_policy.md §7)."""
from __future__ import annotations

from dataclasses import dataclass

import hou

from ..core.policy import Declaration, Violation, check, from_comment, from_lists
from ..core.report import LeakReport, leak_report
from .snapshot import SnapshotCache

PARMS = ("scope_in", "scope_inout", "scope_out")


def declaration(scope) -> Declaration | None:
    """Subnet/HDA: spare parms scope_in/inout/out. Box: `in:`/`inout:`/`out:` comment lines."""
    if isinstance(scope, hou.NetworkBox):
        return from_comment(scope.comment())
    parms = [scope.parm(name) for name in PARMS]
    if all(p is None for p in parms):
        return None
    values = [p.evalAsString() if p else default for p, default in zip(parms, ("*", "", ""))]
    return from_lists(*values)


def _entries(exit: hou.Node, members: set[str]) -> list[hou.Node]:
    """Outside nodes wired into the box upstream of `exit`, in walk order."""
    found: dict[str, hou.Node] = {}
    seen: set[str] = set()
    stack = [exit]
    while stack:
        node = stack.pop()
        for up in (n for n in node.inputs() if n is not None):
            if up.path() not in members:
                found.setdefault(up.path(), up)
            elif up.path() not in seen:
                seen.add(up.path())
                stack.append(up)
    return list(found.values())


def _main_entry(exit: hou.Node, members: set[str]) -> hou.Node | None:
    """Follow first inputs from `exit` until the chain leaves the box."""
    node = exit
    while node is not None and node.path() in members:
        node = next(iter(n for n in node.inputs()[:1] if n is not None), None)
    return node


def boundaries(scope) -> list[tuple[hou.Node, list[hou.Node]]]:
    """(exit, entries) pairs, main entry first. Subnet/HDA: one pair. Box: one per exit."""
    if not isinstance(scope, hou.NetworkBox):
        return [(scope, [n for n in scope.inputs() if n is not None])]
    nodes = list(scope.nodes(recurse=True))
    members = {n.path() for n in nodes}
    exits = [n for n in nodes if any(o.path() not in members for o in n.outputs())]
    exits = exits or [n for n in nodes if not n.outputs()]  # nothing leaves: the last nodes
    pairs = []
    for exit in exits:
        entries = _entries(exit, members)
        main = _main_entry(exit, members)
        # ponytail: if the first-input chain starts inside the box (a generator), no entry is
        # "main" and entries[0] is a side input; deletes are then reported against it.
        if main is not None:
            entries = [main] + [e for e in entries if e.path() != main.path()]
        pairs.append((exit, entries))
    return pairs


@dataclass(frozen=True)
class ExitResult:
    exit: str
    report: LeakReport | None           # None when a snapshot is missing (see problems)
    violations: list[Violation] | None  # None when the scope has no declaration


def collect_scope(scope, cache: SnapshotCache, cook: bool = False
                  ) -> tuple[Declaration | None, list[ExitResult], dict[str, str]]:
    decl = declaration(scope)
    results: list[ExitResult] = []
    problems: dict[str, str] = {}
    for exit, entries in boundaries(scope):
        snaps = {}
        for node in [*entries, exit]:
            snap, reason = cache.get(node, cook)
            if snap is None:
                problems[node.path()] = reason
            else:
                snaps[node.path()] = snap
        if any(n.path() not in snaps for n in [*entries, exit]):
            results.append(ExitResult(exit.path(), None, None))
            continue
        entry_snaps, exit_snap = [snaps[n.path()] for n in entries], snaps[exit.path()]
        report = leak_report(entry_snaps, exit_snap)
        violations = check(decl, report, entry_snaps, exit_snap) if decl else None
        results.append(ExitResult(exit.path(), report, violations))
    return decl, results, problems
