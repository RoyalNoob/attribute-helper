# TODO

Single source of truth for progress. Update it in the same commit as the work.
Milestones follow [docs/plan.md](docs/plan.md) §7–8.

## Start here (onboarding / handover)

1. Read, in order: [plan](docs/plan.md), [API notes](docs/houdini-api-notes.md)
   (overrides the plan where they differ), [CLAUDE.md](CLAUDE.md).
2. `pip install pytest pytest-cov && pytest --cov=attribute_helper.core --cov-fail-under=90`
   — must pass with no Houdini installed.
3. Find the first unchecked item below. That is the current task.
4. Handover: tick finished items, add a dated line under **Log**, and record
   anything half-done as an unchecked item with a note.

**Current milestone:** 0.1.0 released. Next: the open decision below, or Future work in [plan §12](docs/plan.md).

## Decisions

- [x] License: MIT
- [x] No CI: run `pytest` locally before committing
- [ ] Supported versions: Houdini 22 only, or 21 and 22
- [x] Project name: `attribute-helper`

## Phase 0: Repository setup

- [x] Layout skeleton, README stub, CLAUDE.md, LICENSE, .gitignore
- [x] pytest config + `core/` must-not-import-`hou` test

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
- [x] Every state rule unit-tested; `core/` coverage 100%

## Phase 2: Adapter

- [x] Graph walk (current network level; stops at subnet boundary, resolves dots)
- [x] Snapshot from `node.geometry()`
- [x] Cache keyed on (`sessionId()`, `cookCount()`)
- [x] Cook policy: "cooked only" never cooks (tested with cook counts); "cook on demand"
- [x] Cook errors → no snapshot + reason (not an empty snapshot, which would fake Born/Deleted); walk continues
- [x] hython tests building networks in code: `hython tools/run_hython_tests.py`

## Phase 3: MVP panel

- [x] Header: follow display node, use selected, cook on demand, refresh
- [x] Table (`QAbstractTableModel` + `QSortFilterProxyModel`) with filters
- [x] Overlay for toggled keys on one network level
- [x] Redraw: QTimer poll of pwd + cache keys (S6); overlay via pending action (S3)
- [x] Acceptance: overlay follows moved nodes; no undo entries or param changes after use
- [x] `docs/ui_checklist.md`
- [x] Run the checklist in the GUI (all 11 pass)

## Phase 4: Leak report

- [x] `leak_report` in core: the state rules across the subnet as one node (+ Unknown for topology changes)
- [x] Leak report tab (GUI checks 12–15 pass)
- [x] Acceptance: test subnet with exactly one of each gives exactly three results (hython test)

## Phase 5: Depth

- [x] Enter subnets and unlocked HDAs (locked HDAs stay one node); GUI checks 16–19 pass
- [x] Groups (`group:point|prim|vertex|edge`) and detail attributes in the table

## Phase 6: Policy link

- [x] Decisions in [scope policy §7](docs/attrib_scope_policy.md): scope = subnet / HDA / network box
- [x] ~~in/inout/out lists~~ replaced (too clunky) by ticking findings "intended", saved in a hidden parm
- [x] Leak tab tickboxes, unticked = red; GUI checks 20–26 pass
- [x] Rule fix: only the first input's keys can be Deleted (side inputs are read, not passed on)

## First public release

- [x] README: user manual, install steps, known limits
- [x] README: screenshots + navigation GIF (docs/images/), in all three languages
- [x] CONTRIBUTING.md with test commands
- [x] CHANGELOG.md (0.1.0)

## Log

- 2026-09-26: Phase 0 skeleton, MIT license, TODO.md. API notes already cover part of S1/S2/S4.
- 2026-09-26: S1, S2, S7 done (hython). Topology change invalidates data IDs → new `REBUILT` state.
- 2026-09-26: S5 done. S3 script and S4 panel written; both wait for a GUI check.
- 2026-09-26: S3 round 1 failed; cause found in nodegraph.py; round 2 script written.
- 2026-09-26: S3 passes with pending-action method. S4 needed PaneTabTypeMenu.xml.
- 2026-09-26: S4 done (menu XML in a subMenu; GUI reads Documents/houdini22.0 prefs).
- 2026-09-26: S6 done. All spikes done; phase 1 unblocked.
- 2026-09-26: Phase 1 done: model + states, 14 tests, 100% core coverage. CI on Python 3.13.
- 2026-09-26: Dropped CI (decision); tests run locally.
- 2026-09-26: Phase 2 done: adapter (walk, snapshot, cache, cook policy), 9 hython tests.
- 2026-09-26: Phase 3 built (panel, table, overlay, poll). Waiting on docs/ui_checklist.md in the GUI.
- 2026-09-26: Phase 3 done: GUI checklist passes (close bug fixed: hook is onDestroyInterface).
- 2026-09-26: Phase 4 built: leak report (core, adapter, tab). Acceptance test passes in hython.
- 2026-09-26: Phase 4 done: GUI checks 12–15 pass.
- 2026-09-26: Phase 5 built: walk enters editable subnets; groups tracked. hython tests pass.
- 2026-09-26: Phase 5 done: GUI checks 16–19 pass.
- 2026-09-26: Phase 6 built: declarations, violation checks, box scopes. Deleted rule now first-input only.
- 2026-09-26: Replaced in/inout/out with per-finding "intended" ticks (hidden parm `attribute_helper_intended`).
- 2026-09-26: Ticks record intent (leaked / changed / deleted); written and unknown share "changed", so a Merge no longer makes ticks stale.
- 2026-09-26: User manual in README.md.
- 2026-09-26: install.py: one line in Houdini's Python Shell installs the package pointer.
- 2026-10-06: README translations: README.ja.md, README.zh-TW.md.
- 2026-10-06: Released 0.1.0 (tag v0.1.0).
- 2026-10-06: hython tests pass on Houdini 22.0.459; docs no longer pin the build path.
- 2026-10-06: CONTRIBUTING.md.
- 2026-10-07: Screenshots and GIF in the READMEs.
- 2026-10-07: Docs audit: plan updated to match 0.1.0; stale checklist, API notes, and CLAUDE.md lines fixed; .coverage untracked.
