# TODO

Single source of truth for progress. Update it in the same commit as the work.
Milestones follow [docs/attrib_lifetime_plan.md](docs/attrib_lifetime_plan.md) §7–8.

## Start here (onboarding / handover)

1. Read, in order: [plan](docs/attrib_lifetime_plan.md), [API notes](docs/houdini-api-notes.md)
   (overrides the plan where they differ), [CLAUDE.md](CLAUDE.md).
2. `pip install pytest && pytest` — must pass with no Houdini installed.
3. Find the first unchecked item below. That is the current task.
4. Handover: tick finished items, add a dated line under **Log**, and record
   anything half-done as an unchecked item with a note.

**Current milestone:** Spikes

## Decisions

- [x] License: MIT
- [ ] Supported versions: Houdini 22 only, or 21 and 22
- [ ] Final project name (`attrib-lifetime` is a working name)

## Phase 0: Repository setup

- [x] Layout skeleton, README stub, CLAUDE.md, LICENSE, .gitignore
- [x] pytest config + `core/` must-not-import-`hou` test
- [x] GitHub Actions workflow
- [ ] Push to GitHub and confirm CI is green

## Spikes (S1–S4 block phase 1; results go in `docs/spikes/`)

- [x] S1 data ID readable from Python for all four classes → [data_ids.md](docs/spikes/data_ids.md)
- [x] S2 false "Written" table → [data_ids.md](docs/spikes/data_ids.md)
- [ ] S3 overlay shapes: outline on a node, line on a wire, follow node moves
      — script ready: [s3_overlay.py](docs/spikes/s3_overlay.py); GUI check pending
- [ ] S4 test panel with one table opens from the pane menu
      — partial: found + imports OK in hython; GUI check pending ([s4_s5](docs/spikes/s4_s5_panel_package.md))
- [x] S5 package JSON loads the panel from a clean user pref folder → [s4_s5](docs/spikes/s4_s5_panel_package.md)
- [ ] S6 cook / network-change callbacks and cost; pick redraw method
- [x] S7 group data IDs in HOM → yes, same type ([data_ids.md](docs/spikes/data_ids.md))

## Phase 1: Core (pure Python)

- [ ] Data model: `AttribKey`, `AttribInfo`, `Snapshot` (+ topology ID), `Graph`, `State`; data ID = 4-int tuple
- [ ] `compute_states` per plan §4.1 + `REBUILT` state when topology ID changed (S2)
- [ ] `lifetime`, `summary`
- [ ] Fixtures: linear chain, branch + merge, generator, deleted attrib, same name in two classes
- [ ] Every state rule unit-tested; `core/` coverage ≥ 90%

## Phase 2: Adapter

- [ ] Graph walk (current network level, input order)
- [ ] Snapshot from `node.geometry()`
- [ ] Cache keyed on (`sessionId()`, `cookCount()`)
- [ ] Cook policy: "cooked only" checks `needsToCook()` before `geometry()`; "cook on demand"
- [ ] Cook errors → empty snapshot + error flag, walk continues
- [ ] hython tests building networks in code (no committed .hip files)

## Phase 3: MVP panel

- [ ] Header: target field, use display node, pick, cook-mode toggle, refresh
- [ ] Table (`QAbstractTableModel` + `QSortFilterProxyModel`) with filters
- [ ] Overlay for toggled keys on one network level
- [ ] Redraw on toggle / target change / recook / node move / level change
- [ ] Acceptance: overlay follows moved nodes; no undo entries or param changes after use
- [ ] `docs/ui_checklist.md`

## Phase 4: Leak report

- [ ] `leak_report` in core (leaked locals, outer writes, deleted outer attribs)
- [ ] Leak report tab
- [ ] Acceptance: test subnet with exactly one of each gives exactly three results

## Phase 5: Depth

- [ ] Enter subnets and HDAs (tree of network levels)
- [ ] Groups (if S7 passes) and detail attributes in the table

## Phase 6: Policy link

- [ ] Read `in` / `inout` / `out` lists (see [scope policy](docs/attrib_scope_policy.md))
- [ ] Flag violations in the table

## First public release

- [ ] README: overlay GIF, install steps, known limits
- [ ] CONTRIBUTING.md with test commands
- [ ] CHANGELOG.md

## Log

- 2026-09-26: Phase 0 skeleton, MIT license, TODO.md. API notes already cover part of S1/S2/S4.
- 2026-09-26: S1, S2, S7 done (hython). Topology change invalidates data IDs → new `REBUILT` state.
- 2026-09-26: S5 done. S3 script and S4 panel written; both wait for a GUI check.
