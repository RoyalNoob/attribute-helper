"""Walk the network upstream of a target node into a core Graph."""
from __future__ import annotations

import hou

from ..core.model import Graph


def walk(target: hou.Node) -> tuple[Graph, dict[str, hou.Node]]:
    """Upstream chain of `target` in its own network level, inputs before outputs.

    An input in another level (a subnet's indirect input resolves to the node outside)
    is kept as a boundary node so its snapshot can be compared, but not walked further.
    Returns the graph (node ids are paths) and a map from id to node.
    """
    level = target.parent()
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
        ups = [n for n in node.inputs() if n is not None]
        inputs[path] = [n.path() for n in ups] if node.parent() == level else []
        stack.append((node, True))
        stack.extend((n, False) for n in reversed(ups) if node.parent() == level)
    return Graph(order, {k: v for k, v in inputs.items() if v}), nodes
