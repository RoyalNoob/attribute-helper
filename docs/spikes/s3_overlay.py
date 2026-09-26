"""Spike S3: overlay shapes in a live network editor.

In Houdini, select one SOP that has an input, then in Windows > Python Shell:

    exec(open(r"E:/Repo/attribute-helper/docs/spikes/s3_overlay.py").read())

Draws an orange outline on the node and an orange wire to its first input.
Moving either node redraws via a PositionChanged callback.
Clear with:  s3_stop()
"""
import hou

COLOR = hou.Color((1.0, 0.5, 0.0))
_EVENTS = (hou.nodeEventType.PositionChanged,)


def _editor():
    return hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)


def _draw(node):
    editor = _editor()
    rect = editor.itemRect(node)
    pad = 0.15
    outline = hou.BoundingRect(rect.min()[0] - pad, rect.min()[1] - pad,
                               rect.max()[0] + pad, rect.max()[1] + pad)
    shapes = [hou.NetworkShapeNodeShape(outline, node.userData("nodeshape") or "rect",
                                        COLOR, 1.0, fill=False, screen_space=False)]
    src = node.inputs()[0] if node.inputs() else None
    if src is not None:
        up = editor.itemRect(src)
        # Wire runs from the bottom of the input node to the top of this node.
        shapes.append(hou.NetworkShapeConnection(
            hou.Vector2(rect.center()[0], rect.max()[1]), hou.Vector2(0, 1),
            hou.Vector2(up.center()[0], up.min()[1]), hou.Vector2(0, -1),
            COLOR, 1.0))
    editor.setOverlayShapes(shapes)
    return src


def _on_move(**kwargs):
    _draw(_S3["node"])


def s3_stop():
    for n in _S3.get("watched", ()):
        try:
            n.removeEventCallback(_EVENTS, _on_move)
        except hou.OperationFailed:
            pass
    _editor().setOverlayShapes([])
    _S3.clear()


_S3 = globals().setdefault("_S3", {})
if _S3:
    s3_stop()
sel = hou.selectedNodes()
if len(sel) != 1:
    raise RuntimeError("S3: select exactly one node first")
_S3["node"] = sel[0]
src = _draw(sel[0])
_S3["watched"] = [n for n in (sel[0], src) if n is not None]
for n in _S3["watched"]:
    n.addEventCallback(_EVENTS, _on_move)
print("S3 overlay drawn. Move the nodes, pan, zoom. s3_stop() to clear.")
