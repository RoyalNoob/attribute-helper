"""Data model. Pure Python: no hou import (see tests/core/test_no_hou.py)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

DataId = tuple[int, ...]  # hou.AttribDataId.vexAttribDataId(); see docs/spikes/data_ids.md


@dataclass(frozen=True, order=True)
class AttribKey:
    cls: str  # point | prim | vertex | detail
    name: str


@dataclass(frozen=True)
class AttribInfo:
    type: str
    size: int
    data_id: DataId | None


@dataclass(frozen=True)
class Snapshot:
    node_id: str
    attribs: dict[AttribKey, AttribInfo]
    topology_id: DataId | None = None


@dataclass(frozen=True)
class Graph:
    nodes: list[str]
    inputs: dict[str, list[str]] = field(default_factory=dict)  # node_id -> input node_ids

    def inputs_of(self, node_id: str) -> list[str]:
        return self.inputs.get(node_id, [])


class State(Enum):
    BORN = "born"
    WRITTEN = "written"  # a hint: some nodes change data IDs without changing values
    PASS = "pass"
    REBUILT = "rebuilt"  # survives, but topology changed, so the data ID says nothing
    DELETED = "deleted"
    ABSENT = "absent"


ALIVE = frozenset({State.BORN, State.WRITTEN, State.PASS, State.REBUILT})
