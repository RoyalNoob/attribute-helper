"""Draw attribute lifetimes on the network editor (method: docs/spikes/s3_overlay.md).

The network editor rebuilds its overlay layer on every UI event, so shapes set once are wiped.
install() wraps nodegraphhooks.createEventHandler to add one pending action that never
completes; nodegraph merges its shapes into every redraw. nodegraph* modules exist only in
the GUI, so they are imported inside install().
"""
from __future__ import annotations

from typing import Callable

import hou

from .core.model import AttribKey, Graph, State
from .core.states import States, wires

Provider = Callable[[hou.NetworkEditor], list]
_MARK = "_attribute_helper_overlay"  # attribute on the action and the wrapped hook
_provider: Provider | None = None

# Outline alpha per state. Born also gets a light fill; Deleted also gets a cross.
_ALPHA = {State.BORN: 1.0, State.WRITTEN: 1.0, State.REBUILT: 0.6, State.PASS: 0.3, State.DELETED: 1.0}
_PAD, _PAD_STEP, _WIRE_STEP = 0.12, 0.1, 0.06


def _grow(rect: hou.BoundingRect, pad: float) -> hou.BoundingRect:
    return hou.BoundingRect(rect.min()[0] - pad, rect.min()[1] - pad,
                            rect.max()[0] + pad, rect.max()[1] + pad)


def _visible(editor: hou.NetworkEditor, node_id: str) -> hou.Node | None:
    node = hou.node(node_id)
    return node if node is not None and node.parent() == editor.pwd() else None


def shapes(editor: hou.NetworkEditor, graph: Graph, states: States,
           colors: dict[AttribKey, tuple[float, float, float]]) -> list:
    """Shapes for every toggled key. Several keys on one node get nested outlines."""
    out = []
    for k, (key, rgb) in enumerate(colors.items()):
        color, pad = hou.Color(rgb), _PAD + _PAD_STEP * k
        for node_id, keys in states.items():
            state, node = keys.get(key), _visible(editor, node_id)
            if state is None or node is None:
                continue
            rect = _grow(editor.itemRect(node), pad)
            shape = node.userData("nodeshape") or node.type().defaultShape() or "rect"
            out.append(hou.NetworkShapeNodeShape(rect, shape, color, _ALPHA[state],
                                                 fill=False, screen_space=False))
            if state is State.BORN:
                out.append(hou.NetworkShapeNodeShape(rect, shape, color, 0.2,
                                                     fill=True, screen_space=False))
            if state is State.DELETED:
                lo, hi = rect.min(), rect.max()
                out.append(hou.NetworkShapeLine(lo, hi, color, 1.0, 2.0, screen_space=False))
                out.append(hou.NetworkShapeLine(hou.Vector2(lo[0], hi[1]), hou.Vector2(hi[0], lo[1]),
                                                color, 1.0, 2.0, screen_space=False))
        for src_id, dst_id in wires(graph, states, key):
            src, dst = _visible(editor, src_id), _visible(editor, dst_id)
            if src is None or dst is None:
                continue
            # ponytail: wire ends at the top centre, not the exact input connector of multi-input nodes.
            dx = _WIRE_STEP * k
            up, down = editor.itemRect(src), editor.itemRect(dst)
            out.append(hou.NetworkShapeConnection(
                hou.Vector2(down.center()[0] + dx, down.max()[1]), hou.Vector2(0, 1),
                hou.Vector2(up.center()[0] + dx, up.min()[1]), hou.Vector2(0, -1),
                color, 1.0))
    return out


def _safe(editor: hou.NetworkEditor) -> list:
    try:
        return _provider(editor) if _provider else []
    except hou.Error:  # a node was deleted or renamed between polls; the next poll fixes it
        return []
    except RuntimeError:  # the panel's Qt widget is gone (closed without onDestroy)
        return []


def install(provider: Provider) -> None:
    global _provider
    import nodegraphbase
    import nodegraphhooks

    _provider = provider
    if getattr(nodegraphhooks.createEventHandler, _MARK, False):
        return
    original = nodegraphhooks.createEventHandler

    class Action(nodegraphbase.PendingAction):
        def completeAction(self, uievent):
            if _provider is None:
                return True  # completing removes the action (see s3_overlay.md)
            self.editor_updates.setOverlayShapes(_safe(uievent.editor))
            return False

    setattr(Action, _MARK, True)

    def hook(uievent, pending_actions):
        if _provider is not None and not any(getattr(a, _MARK, False) for a in pending_actions):
            pending_actions.append(Action())
        return original(uievent, pending_actions)

    setattr(hook, _MARK, True)
    hook.original = original
    nodegraphhooks.createEventHandler = hook


def uninstall() -> None:
    global _provider
    import nodegraphhooks

    _provider = None
    hook = nodegraphhooks.createEventHandler
    if getattr(hook, _MARK, False):
        nodegraphhooks.createEventHandler = hook.original
    push()


def push() -> None:
    """Redraw now in every network editor, without waiting for the next UI event."""
    for pane in hou.ui.paneTabs():
        if pane.type() == hou.paneTabType.NetworkEditor:
            pane.setOverlayShapes(_safe(pane))
