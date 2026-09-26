# Spike S3: overlay shapes

Houdini 22.0.429, 2026-09-26. Script: [s3_overlay.py](s3_overlay.py).

## Round 1: `editor.setOverlayShapes()` from outside — FAIL

| Check | Result |
|---|---|
| Outline on node | yes |
| Wire to input (`NetworkShapeConnection`, input end up, output end down) | yes, looks correct |
| Follows node moves | no: all shapes vanish as soon as the mouse enters the editor |
| Pan / zoom | untestable |
| Survives dive in/out | no |

Cause (`$HFS/houdini/python3.13libs/nodegraph.py`, `handleEventCoroutine`): every UI event builds a
fresh `EditorUpdates` and ends with `applyToEditor()`, which calls `setShapes()` and
`setOverlayShapes()` with only what the current handler and `pending_actions` supplied.
Shapes set from outside are overwritten on the next event.

## Round 2: persistent pending action — PASS

The same loop merges `editor_updates` from every object in `pending_actions` on each event, and
`nodegraphhooks.createEventHandler(uievent, pending_actions)` receives that list. Wrapping that
hook function (not shadowing the `nodegraphhooks.py` file, so other tools' hooks still run) lets us
insert one `PendingAction` that never completes and recomputes shapes from `itemRect()` each event.

| Check | Result |
|---|---|
| Stays when the mouse enters the editor | yes |
| Follows node drags | yes |
| Pan / zoom | yes |
| Survives dive in/out (hotkey) | yes |

Gotcha: restoring the hook is not enough to stop. The action stays in `pending_actions` until the
editor's event coroutine resets, so the wire came back after `s3_stop()`. Fix: `completeAction()`
returns `True` once stopped, which makes nodegraph drop the action.

Method for phase 3: overlay = one `PendingAction` per editor, injected by wrapping
`nodegraphhooks.createEventHandler`. No node callbacks needed for drags.
