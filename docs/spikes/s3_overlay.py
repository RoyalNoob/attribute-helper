"""Spike S3 (round 2): overlay shapes that survive network editor events.

In Houdini, select one SOP that has an input, then in Windows > Python Shell:

    exec(open(r"<path-to-attribute-helper>/docs/spikes/s3_overlay.py").read())

Draws an orange outline on the node and an orange wire to its first input.
Clear with:  s3_stop()

Why round 1 failed: nodegraph.py builds a fresh EditorUpdates on every UI event and
applyToEditor() calls editor.setOverlayShapes(), wiping shapes set from outside.
Fix: the same loop merges editor_updates from every object in `pending_actions`,
and nodegraphhooks.createEventHandler() receives that list. We wrap that hook to
insert one PendingAction that never completes and recomputes our shapes on every event.
"""
import hou
import nodegraphbase
import nodegraphhooks

COLOR = hou.Color((1.0, 0.5, 0.0))


def _shapes(editor, node):
    if editor.pwd() != node.parent():
        return []
    rect = editor.itemRect(node)
    pad = 0.15
    outline = hou.BoundingRect(rect.min()[0] - pad, rect.min()[1] - pad,
                               rect.max()[0] + pad, rect.max()[1] + pad)
    shapes = [hou.NetworkShapeNodeShape(outline, node.userData("nodeshape") or "rect",
                                        COLOR, 1.0, fill=False, screen_space=False)]
    if node.inputs():
        up = editor.itemRect(node.inputs()[0])
        # Wire runs from the bottom of the input node to the top of this node.
        shapes.append(hou.NetworkShapeConnection(
            hou.Vector2(rect.center()[0], rect.max()[1]), hou.Vector2(0, 1),
            hou.Vector2(up.center()[0], up.min()[1]), hou.Vector2(0, -1),
            COLOR, 1.0))
    return shapes


class OverlayAction(nodegraphbase.PendingAction):
    """Never completes, so nodegraph merges its shapes into every event."""

    def __init__(self, node):
        super().__init__()
        self.node = node

    def completeAction(self, uievent):
        if not _S3:
            return True  # stopped: completing removes us from pending_actions
        self.editor_updates.setOverlayShapes(_shapes(uievent.editor, self.node))
        return False


def _hook(uievent, pending_actions):
    if _S3 and not any(isinstance(a, OverlayAction) for a in pending_actions):
        pending_actions.append(OverlayAction(_S3["node"]))
    return _S3_ORIG(uievent, pending_actions)


def s3_stop():
    nodegraphhooks.createEventHandler = _S3_ORIG
    _S3.clear()
    hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).setOverlayShapes([])


_S3 = globals().setdefault("_S3", {})
# Keep the true original across re-runs of this script.
_S3_ORIG = globals().get("_S3_ORIG") or nodegraphhooks.createEventHandler
sel = hou.selectedNodes()
if len(sel) != 1:
    raise RuntimeError("S3: select exactly one node first")
_S3["node"] = sel[0]
nodegraphhooks.createEventHandler = _hook
editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
editor.setOverlayShapes(_shapes(editor, sel[0]))  # draw now, before the next event
print("S3 overlay on. Move nodes, pan, zoom, dive in and out. s3_stop() to clear.")
