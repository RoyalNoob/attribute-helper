# Spikes S1, S2, S7: data IDs

Houdini 22.0.429, hython, 2026-09-26. Script: [data_ids.py](data_ids.py) (builds every network in code).

## S1: data ID from Python — PASS

- `hou.Attrib.dataId()` returns `hou.AttribDataId`. Use `.vexAttribDataId()`: a 4-int tuple
  `(session_hi, session_lo, 0, id)`. It is JSON-safe as a list and hashable as a tuple.
  Use it as `AttribInfo.data_id`.
- Works for point, prim, vertex, and detail. Two reads of the same geometry give equal tuples.
- Cross-session stability is not tested. Not needed: every comparison happens in one session.

## S7: group data IDs — PASS

`hou.PointGroup.dataId()` (and prim, vertex, edge groups) returns the same `AttribDataId` type.
Groups can use the same state rules as attributes in phase 5.

## S2: false "Written" — per node vs. its input

Base: a 3×3 grid with one attribute per class (`a`, `pa`, `va`, `da`) and a point and a prim group.

| Node | Topology ID changed | Result |
|---|---|---|
| Null | no | all pass-through |
| Attribute Wrangle (`@w = 1`) | no | `w` born, all others pass-through |
| Attribute Create | no | `c` born, all others pass-through |
| Attribute Delete (`a`) | no | `a` deleted, all others pass-through |
| Transform | no | only `P` changed |
| Merge, 1 input | no | all pass-through |
| Compile block (`@w = 1` inside) | no | `w` born, all others pass-through |
| Blast (1 point) | yes | every key changed |
| Merge, 2 inputs | yes | every key changed |
| Copy to Points | yes | every key changed except `detail:da` |
| For-Each by piece (empty body) | yes | every key changed |
| Clean (defaults, nothing to clean) | **yes** | every key changed |
| Pack | yes | everything except `P` deleted (moves into the packed prim) |

## Conclusions for the core

1. **When the topology ID does not change, data IDs are exact.** No false "Written" in any tested node.
2. **When the topology ID changes, every surviving key gets a new ID.** Its data ID says nothing.
   Add a state for this (for example `REBUILT`: "key survives, topology changed, write unknown").
   `Snapshot` must carry `topologyDataId()`.
3. **"Topology changed" can itself be a false positive.** Clean with defaults changed nothing
   on a clean grid but still changed the topology ID. Label it as a hint too.
4. Pack is a real delete of all attributes except `P` from the chain's view.
