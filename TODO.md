# TODO

Single source of truth for progress. Update it in the same commit as the work.
Milestones follow [docs/plan.md](docs/plan.md) §7–8.

## Start here (onboarding / handover)

1. Read, in order: [plan](docs/plan.md), [API notes](docs/houdini-api-notes.md)
   (overrides the plan where they differ), [CLAUDE.md](CLAUDE.md).
2. `pip install pytest && pytest` — must pass with no Houdini installed.
3. Find the first unchecked item below. That is the current task.
4. Handover: tick finished items, add a dated line under **Log**, and record
   anything half-done as an unchecked item with a note.

**Current milestone:** Phase 2 (adapter)

## Decisions

- [x] License: MIT
- [ ] Supported versions: Houdini 22 only, or 21 and 22
- [x] Project name: `attribute-helper`

## Phase 0: Repository setup

- [x] Layout skeleton, README stub, CLAUDE.md, LICENSE, .gitignore
- [x] pytest config + `core/` must-not-import-`hou` test
- [x] GitHub Actions workflow
- [ ] Push to GitHub and confirm CI is green

## Spikes (S1–S4 block phase 1; results go in `docs/spikes/`)

- [x] S1 data ID readable from Python for all four classes → [data_ids.md](docs/spikes/data_ids.md)
- [x] S2 false "Written" table → [data_ids.md](docs/spikes/data_ids.md)
- [x] S3 overlay shapes: follow moves, pan/zoom, dive → pending-action method ([s3_overlay.md](docs/spikes/s3_overlay.md))
- [x] S4 panel opens from New Pane Tab Type > Inspectors → [s4_s5](docs/spikes/s4_s5_panel_package.md)
- [x] S5 package JSON loads the panel from a clean user pref folder → [s4_s5](docs/spikes/s4_s5_panel_package.md)
- [x] S6 no cook event exists → poll cache keys with a QTimer ([s6_events.md](docs/spikes/s6_events.md))
- [x] S7 group data IDs in HOM → yes, same type ([data_ids.md](docs/spikes/data_ids.md))

## Phase 1: Core (pure Python)

- [x] Data model: `AttribKey`, `AttribInfo`, `Snapshot` (+ topology ID), `Graph`, `State`; data ID = 4-int tuple
- [x] `compute_states` per plan §4.1 + `REBUILT` state when topology ID changed (S2)
- [x] `lifetime`, `summary`
- [x] Fixtures: linear chain, branch + merge, generator, deleted attrib, same name in two classes
      (built in code by `snap()` in tests/core/test_states.py, not JSON files)
- [x] Every state rule unit-tested; `core/` coverage 100%, CI fails under 90%

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
- [ ] Redraw: QTimer poll of pwd + cache keys (S6); overlay via pending action (S3)
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
- 2026-09-26: S3 round 1 failed; cause found in nodegraph.py; round 2 script written.
- 2026-09-26: S3 passes with pending-action method. S4 needed PaneTabTypeMenu.xml.
- 2026-09-26: S4 done (menu XML in a subMenu; GUI reads Documents/houdini22.0 prefs).
- 2026-09-26: S6 done. All spikes done; phase 1 unblocked.
- 2026-09-26: Phase 1 done: model + states, 14 tests, 100% core coverage. CI on Python 3.13.
