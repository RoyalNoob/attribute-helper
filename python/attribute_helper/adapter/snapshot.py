"""Read cooked geometry into core Snapshots, with a cook-count cache and a cook policy."""
from __future__ import annotations

import hou

from ..core.model import AttribInfo, AttribKey, Graph, Snapshot
from ..core.report import LeakReport, leak_report
from .graph import walk

NEEDS_COOK = "needs cook"
_CLASSES = (
    ("point", hou.Geometry.pointAttribs),
    ("prim", hou.Geometry.primAttribs),
    ("vertex", hou.Geometry.vertexAttribs),
    ("detail", hou.Geometry.globalAttribs),
)


def _type(attrib: hou.Attrib) -> str:
    return attrib.dataType().name().lower() + ("[]" if attrib.isArrayType() else "")


_GROUPS = (
    ("group:point", hou.Geometry.pointGroups),
    ("group:prim", hou.Geometry.primGroups),
    ("group:vertex", hou.Geometry.vertexGroups),
    ("group:edge", hou.Geometry.edgeGroups),
)


def read(node_id: str, geo: hou.Geometry) -> Snapshot:
    attribs = {
        AttribKey(cls, a.name()): AttribInfo(_type(a), a.size(), a.dataId().vexAttribDataId())
        for cls, get in _CLASSES for a in get(geo)
    }
    # Groups follow the same rules (spike S7: they have data IDs too).
    attribs.update({
        AttribKey(cls, g.name()): AttribInfo("group", 1, g.dataId().vexAttribDataId())
        for cls, get in _GROUPS for g in get(geo)
    })
    return Snapshot(node_id, attribs, geo.topologyDataId().vexAttribDataId())


class SnapshotCache:
    """Snapshots keyed by node session id; valid while the node's cook count is unchanged."""

    def __init__(self) -> None:
        self._entries: dict[int, tuple[int, Snapshot]] = {}

    def get(self, node: hou.SopNode, cook: bool) -> tuple[Snapshot | None, str | None]:
        """(snapshot, None) or (None, reason). With cook=False this never starts a cook."""
        if not cook:
            # Errors before needsToCook: a failed node keeps needsToCook() == True, and
            # errors() reports the last cook without starting a new one.
            if node.errors():
                return None, node.errors()[0]
            if node.needsToCook():
                return None, NEEDS_COOK
        hit = self._entries.get(node.sessionId())
        if hit and hit[0] == node.cookCount() and not node.needsToCook():
            return hit[1], None
        geo = node.geometry()  # may cook
        if geo is None or node.errors():
            return None, (node.errors() or ("no geometry",))[0]
        snap = read(node.path(), geo)
        self._entries[node.sessionId()] = (node.cookCount(), snap)
        return snap, None


def collect(target: hou.SopNode, cache: SnapshotCache, cook: bool = False
            ) -> tuple[Graph, dict[str, Snapshot], dict[str, str]]:
    """Graph, snapshots, and a reason for every node without a snapshot."""
    graph, nodes = walk(target)
    snapshots: dict[str, Snapshot] = {}
    problems: dict[str, str] = {}
    for node_id in graph.nodes:
        snap, reason = cache.get(nodes[node_id], cook)
        if snap is None:
            problems[node_id] = reason
        else:
            snapshots[node_id] = snap
    return graph, snapshots, problems


def collect_leaks(scope: hou.SopNode, cache: SnapshotCache, cook: bool = False
                  ) -> tuple[LeakReport | None, dict[str, str]]:
    """Leak report for a subnet or HDA: its output compared with its inputs.

    Returns (None, problems) when the scope or one of its inputs has no snapshot.
    """
    inputs = [n for n in scope.inputs() if n is not None]
    snaps: dict[str, Snapshot] = {}
    problems: dict[str, str] = {}
    for node in [*inputs, scope]:
        snap, reason = cache.get(node, cook)
        if snap is None:
            problems[node.path()] = reason
        else:
            snaps[node.path()] = snap
    if problems:
        return None, problems
    return leak_report([snaps[n.path()] for n in inputs], snaps[scope.path()]), {}
