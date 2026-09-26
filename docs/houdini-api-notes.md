# Houdini API notes: attribute-helper

Checked against **Houdini 22.0.429** with hython, 2026-09-26. These results come from
introspection and one small test network. They are not a full run of the spikes.

## What exists

| Plan item | Finding |
|---|---|
| S1 data ID | `hou.Attrib.dataId()` exists. Also on `hou.Geometry`: `topologyDataId()`, `primitiveIntrinsicsDataId()`, `vexAttribDataId()`. |
| S3 overlay | `hou.NetworkShapeBox`, `NetworkShapeLine`, `NetworkShapeConnection`, `NetworkShapeNodeShape`. `NetworkEditor.setOverlayShapes()` and `setShapes()`. Not yet drawn in a live editor. |
| S4 Qt | PySide6 6.8.3. With one binding, `qt_compat.py` is not needed. |
| Cook policy | `SopNode.needsToCook()`, `cookCount()`, `Node.sessionId()` all exist. |

## Findings that change the plan

1. **`dataId()` does not return an int.** It returns a `hou.AttribDataId` object
   (fields shown in repr: `id`, `session`). Methods: `isValid()`,
   `vexAttribDataId()`. It supports `==` and hashing: two reads of the same
   attribute compare equal and collapse to one entry in a set. The plan's
   `AttribInfo(data_id: int | None)` needs a conversion for JSON. `vexAttribDataId()`
   is the likely candidate. Not verified yet.
2. **Pass-through works as the plan expects.** Box → Attribute Wrangle (`f@mask = 1`):
   `P` keeps the same data ID (27 → 27), and `mask` is new.
3. **Transform works as the plan expects.** `P` gets a new ID (27 → 48), and `mask`
   keeps its ID (41 → 41).
4. **Topology changes make every attribute look "Written".** A Blast deleting one point
   changed every data ID, including `mask`, which the Blast did not edit
   (41 → 88). `topologyDataId()` also changed (30 → 91). This confirms the review
   point: if the topology ID changed, report "topology changed", not "Written".
5. **Reading geometry cooks the node.** `needsToCook()` was `True` before the first
   `geometry()` call and `False` after it. "Cooked only" mode must check
   `needsToCook()` *before* it calls `geometry()`.

## Not yet verified

- S2 across the full node list (Merge, Copy to Points, Pack, Clean, For-Each, Compile).
- Whether overlay shapes follow nodes when moved (S3), and event callbacks (S6).
- Group data IDs (S7).
- Whether `AttribDataId` equality holds across sessions or after a reload of the hip file.
