"""Walk the network upstream of a target node into a core Graph."""
from __future__ import annotations

import hou

from ..core.model import Graph


def _enterable(node: hou.Node) -> bool:
    """Editable SOP networks: plain subnets and unlocked HDAs. Locked HDAs (including
    SideFX SOPs built as HDAs, such as Attribute Wrangle) stay one node."""
    return (node.isNetwork() and not node.isLockedHDA()
            and node.childTypeCategory() == hou.sopNodeTypeCategory()
            and bool(node.subnetOutputs()))


def walk(target: hou.Node) -> tuple[Graph, dict[str, hou.Node]]:
    """Upstream chain of `target`, inputs before outputs, including the inside of subnets.

    The walk covers the target's level and every enterable subnet it meets (from the
    subnet's first output). An input in any other level (inside a subnet, an indirect input
    resolves to the node outside) is kept as a boundary node but not walked further.
    Returns the graph (node ids are paths) and a map from id to node.
    """
    levels = {target.parent().path()}
    containers: set[str] = set()
    order: list[str] = []
    inputs: dict[str, list[str]] = {}
    nodes: dict[str, hou.Node] = {}

    stack = [(target, False)]
    while stack:  # iterative post-order DFS; networks can be deeper than the recursion limit
        node, expanded = stack.pop()
        path = node.path()
        if expanded:
            order.append(path)
            continue
        if path in nodes:
            continue
        nodes[path] = node
        inside = node.parent().path() in levels
        ups = [n for n in node.inputs() if n is not None] if inside else []
        inputs[path] = [n.path() for n in ups]
        stack.append((node, True))
        stack.extend((n, False) for n in reversed(ups))
        if inside and _enterable(node):
            # ponytail: first output only; multi-output subnets show output 0's chain.
            levels.add(path)
            containers.add(path)
            stack.append((node.subnetOutputs()[0], False))
    return Graph(order, {k: v for k, v in inputs.items() if v}, frozenset(containers)), nodes
