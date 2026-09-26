"""Leak report for a subnet or HDA (docs/plan.md §5.1, phase 4).

From outside, a subnet is one node: its output compared with its inputs. The state rules
already classify every key across one node, so the report is those states, grouped.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import AttribKey, Snapshot, State
from .states import state_of


@dataclass(frozen=True)
class LeakReport:
    leaked: list[AttribKey]   # born inside, alive at the output
    written: list[AttribKey]  # outer attributes changed inside (a hint, like Written)
    deleted: list[AttribKey]  # outer attributes deleted inside
    rebuilt: list[AttribKey]  # outer attributes through a topology change: write unknown


def leak_report(entries: list[Snapshot], exit: Snapshot) -> LeakReport:
    keys = set(exit.attribs).union(*(e.attribs for e in entries))
    states = {k: state_of(k, exit, entries) for k in keys}

    def with_state(state: State) -> list[AttribKey]:
        return sorted(k for k, s in states.items() if s is state)

    return LeakReport(with_state(State.BORN), with_state(State.WRITTEN),
                      with_state(State.DELETED), with_state(State.REBUILT))
