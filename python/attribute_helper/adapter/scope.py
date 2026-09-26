"""Scopes: a subnet, an HDA, or a network box (docs/attrib_scope_policy.md §7).

Intended findings live in one hidden string parameter, PARM. A subnet/HDA keeps its own list
on itself (scope id "."). A network box has no parameters, so its list lives on the network
that contains it, under the box name (renaming the box loses its ticks).
"""
from __future__ import annotations

from dataclasses import dataclass

import hou

from ..core.policy import SELF, Finding, parse, toggle
from ..core.report import LeakReport, leak_report
from .snapshot import SnapshotCache

PARM = "attribute_helper_intended"


def _home(scope) -> tuple[hou.Node, str]:
    """The node that stores the scope's list, and the scope id used in it."""
    if isinstance(scope, hou.NetworkBox):
        return scope.parent(), scope.name()
    return scope, SELF


def intended(scope) -> set[Finding]:
    node, scope_id = _home(scope)
    parm = node.parm(PARM)
    return parse(parm.evalAsString()).get(scope_id, set()) if parm else set()


def set_intended(scope, finding: Finding, on: bool) -> None:
    """Tick or untick one finding. Creates the hidden parameter on first use. One undo step."""
    node, scope_id = _home(scope)
    with hou.undos.group("Attribute Helper: mark finding intended"):
        parm = node.parm(PARM)
        if parm is None:
            node.addSpareParmTuple(hou.StringParmTemplate(
                PARM, "Intended findings (Attribute Helper)", 1, is_hidden=True))
            parm = node.parm(PARM)
        parm.set(toggle(parm.evalAsString(), scope_id, finding, on))


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
    report: LeakReport | None  # None when a snapshot is missing (see problems)


def collect_scope(scope, cache: SnapshotCache, cook: bool = False
                  ) -> tuple[set[Finding], list[ExitResult], dict[str, str]]:
    """Intended findings, one leak report per exit, and a reason for each missing snapshot."""
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
        report = None
        if all(n.path() in snaps for n in [*entries, exit]):
            report = leak_report([snaps[n.path()] for n in entries], snaps[exit.path()])
        results.append(ExitResult(exit.path(), report))
    return intended(scope), results, problems
