# Spike S6: redraw triggers and cost

Houdini 22.0.429, hython, 2026-09-26. Script: [s6_events.py](s6_events.py).
Callbacks for every `hou.nodeEventType` on a network `box → xform → null(tail)` and its parent.

## Which events fire

| Action | Events (node:event) |
|---|---|
| Change box size parm | box:ParmTupleChanged, xform:InputDataChanged, tail:InputDataChanged |
| Cook tail after that change | **none** |
| Force-cook box | box, xform, tail: InputDataChanged |
| Move xform | net:PositionChanged, xform:PositionChanged |
| Rename xform | xform:NameChanged |
| Set display flag on xform | net:ChildSwitched, xform:FlagChanged, tail:FlagChanged |
| Insert node between box and xform | net:ChildCreated, xform:InputRewired, tail:InputDataChanged |
| Delete inserted node | net:ChildDeleted, xform:InputRewired |
| Rewire xform input | xform:InputRewired |

There is no cook event. `InputDataChanged` fires when a node is dirtied, **before** it recooks.
When the viewport cooks the display node afterwards, nothing fires. So callbacks alone cannot tell
the panel that new geometry is ready.

## Cost (hython, chain of Transform SOPs, already cooked)

| Nodes | Walk + cache keys (`sessionId`, `cookCount`, `needsToCook`) | Read every snapshot |
|---|---|---|
| 50 | 0.7 ms | 2.3 ms |
| 200 | 0.9 ms | 4.6 ms |
| 1000 | 2.1 ms | 23.4 ms |

## Decision

Poll, do not subscribe. A `QTimer` in the panel (about 250 ms, only while the panel is visible):

1. Read the editor's `pwd()` and the target node. If either changed, rebuild the chain.
2. Walk the chain and compare the cache keys. Re-read snapshots only for nodes whose key changed
   (and, in "cooked only" mode, that no longer need a cook).
3. If anything changed, recompute states and push the overlay with `editor.setOverlayShapes()`.
   The S3 pending action keeps it alive and follows drags between polls.

This covers every row above, including the after-cook case that no event reports, and it has no
callbacks to register or remove when the chain changes. Cost is about 2 ms per 1000 nodes when
nothing changed. Callbacks can be added later as a wake-up signal if polling shows up in a profile.
