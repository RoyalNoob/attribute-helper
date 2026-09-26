"""State rules (docs/plan.md §4, plus REBUILT from docs/spikes/data_ids.md)."""
from __future__ import annotations

from dataclasses import dataclass

from .model import ALIVE, AttribKey, Graph, Snapshot, State

States = dict[str, dict[AttribKey, State]]  # node_id -> key -> state (ABSENT keys omitted)


def state_of(key: AttribKey, snap: Snapshot, inputs: list[Snapshot]) -> State:
    """State of `key` on `snap`, given the snapshots of its inputs (plan §4.1)."""
    have = [i for i in inputs if key in i.attribs]
    if key not in snap.attribs:
        return State.DELETED if have else State.ABSENT
    if not have:
        return State.BORN
    data_id = snap.attribs[key].data_id
    if data_id is not None and any(i.attribs[key].data_id == data_id for i in have):
        return State.PASS
    if snap.topology_id is not None and all(i.topology_id != snap.topology_id for i in have):
        return State.REBUILT
    return State.WRITTEN


def compute_states(graph: Graph, snapshots: dict[str, Snapshot]) -> States:
    """Nodes without a snapshot, or with an input that has none, are left out (unknown)."""
    states: States = {}
    for node in graph.nodes:
        ids = graph.inputs_of(node)
        if node not in snapshots or any(i not in snapshots for i in ids):
            continue
        snap, inputs = snapshots[node], [snapshots[i] for i in ids]
        # Every key is on the node or an input, so ABSENT never appears here.
        keys = set(snap.attribs).union(*(i.attribs for i in inputs))
        states[node] = {k: state_of(k, snap, inputs) for k in keys}
    return states


def lifetime(states: States, key: AttribKey) -> set[str]:
    return {node for node, keys in states.items() if keys.get(key) in ALIVE}


def wires(graph: Graph, states: States, key: AttribKey) -> list[tuple[str, str]]:
    """(input, node) wires that carry `key`: alive at the input, and the node has a state for it."""
    return [(src, node) for node in graph.nodes if key in states.get(node, {})
            for src in graph.inputs_of(node) if states.get(src, {}).get(key) in ALIVE]


@dataclass(frozen=True)
class AttribSummary:
    key: AttribKey
    type: str
    born: list[str]
    deleted: list[str]
    writes: int
    rebuilt: int


def summary(graph: Graph, states: States, snapshots: dict[str, Snapshot]) -> list[AttribSummary]:
    """One row per key for the UI table, sorted by key. Node lists follow graph order."""
    by_key: dict[AttribKey, dict[State, list[str]]] = {}
    for node in graph.nodes:
        if node in graph.containers:
            continue
        for key, state in states.get(node, {}).items():
            by_key.setdefault(key, {}).setdefault(state, []).append(node)
    rows = []
    for key in sorted(by_key):
        found = by_key[key]
        info = next(s.attribs[key] for s in snapshots.values() if key in s.attribs)
        rows.append(AttribSummary(
            key, info.type, found.get(State.BORN, []), found.get(State.DELETED, []),
            len(found.get(State.WRITTEN, [])), len(found.get(State.REBUILT, []))))
    return rows
