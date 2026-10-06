# Attribute Lifetime Viewer: Project Plan

Name: `attribute-helper`
Target: Houdini 22 only (decided 2026-10-07).
Type: Open source Python Panel for the Houdini network editor.
Related document: `attrib_scope_policy.md` (the future scope policy).
Status: built and released as 0.1.0. Sections 4–6 and 8 describe what was built (updated
2026-10-07); where a spike changed the original plan, the section says so.

---

## 1. Purpose

Houdini has no attribute scope. An attribute that a node creates stays on the geometry and goes downstream. In large networks, subnets, and HDAs, it is difficult to see:

- where an attribute starts,
- which nodes change it,
- where it ends,
- which temporary attributes leak out of a subnet or an HDA.

This tool shows the lifetime of each attribute in the network editor. The user toggles an attribute in a list. The tool draws the scope of that attribute on the network as a non-destructive overlay.

## 2. Goals and non-goals

### Goals

1. Show the lifetime of attributes (born, written, pass-through, deleted) for each node of a chain.
2. Show the lifetime in the network editor with overlay shapes. The overlay does not change the scene.
3. Give a leak report for a subnet, an HDA, or a network box.
4. Keep the core logic independent of Houdini, so that unit tests run without a Houdini license.
5. Collect data that helps to design the scope policy (see `attrib_scope_policy.md`).

### Non-goals

1. The tool does not change geometry, node colors, or parameters. One exception (2026-09-26): ticking
   a finding "intended" in the leak report writes one hidden string parameter, as one undo step.
2. The tool does not enforce a scope policy. Enforcement is a different project.
3. The tool does not find attribute **reads**. Reads are not visible in cooked geometry. (A later phase can add a heuristic.)
4. The tool does not support contexts other than SOPs in v1.

## 3. Glossary

| Term | Meaning |
|---|---|
| Target node | The node where the upstream walk starts. Default: the display node of the current network. |
| Chain | All nodes upstream of the target node, in its network level and inside editable subnets it passes. |
| Snapshot | The list of attributes on the cooked geometry of one node: class, name, type, size, data ID. |
| Attribute key | The pair (class, name). Point `mask` and primitive `mask` are two different keys. |
| State | The status of one attribute key on one node: born, written, pass-through, rebuilt, deleted, absent. |
| Leak | An attribute that is born inside a scope (subnet, HDA, or network box) and is alive at its output. |

## 4. Core concepts

### 4.1 State rules

For each node N and each attribute key K, compare the snapshot of N with the snapshots of the inputs of N.

| State | Condition |
|---|---|
| Born | K is not on any input of N. K is on N. |
| Written | K is on at least one input. K is on N. The data ID on N is different from the data ID on all inputs that have K. |
| Pass-through | K is on at least one input. K is on N. The data ID on N is the same as the data ID on one input that has K. |
| Rebuilt | K is on an input and on N, the data ID changed, and the topology ID differs from every input that has K: a write cannot be detected (spike S2). |
| Deleted | K is on the **first** input. K is not on N. (Other inputs are read, not passed on: a wrangle's second input. Changed 2026-09-26.) |
| Absent | K is not on N, and not on the first input. |

A node with no inputs (a generator) gives "Born" for all its attributes.

### 4.2 Written is a hint, not a proof

Some nodes change a data ID with no change of values. Example: a Merge node can make new attribute data from all inputs. The UI must show "Written" as a hint. The UI must not describe it as a confirmed change.

### 4.3 Lifetime

The lifetime of K is the set of nodes where the state of K is Born, Written, Pass-through, or Rebuilt. The overlay draws this set.

## 5. Architecture

The project has four layers. Only layers 2 to 4 import `hou`.

```
+------------------------------------------------------+
| 4. ui       Python Panel (Qt): list, filters, toggles |
+------------------------------------------------------+
| 3. overlay  Converts lifetime data to network shapes  |
+------------------------------------------------------+
| 2. adapter  Walks the graph, reads hou.Geometry,      |
|             caches snapshots, controls cooking        |
+------------------------------------------------------+
| 1. core     Pure Python: data model, state rules,     |
|             lifetime, leak report. No hou import.     |
+------------------------------------------------------+
```

### 5.1 Layer 1: core (no `hou`)

Data model (`core/model.py`, frozen dataclasses):

```python
AttribKey(cls: str, name: str)   # cls: point | prim | vertex | detail | group:point|prim|vertex|edge
AttribInfo(type: str, size: int, data_id: tuple[int, ...] | None)  # vexAttribDataId(), spike S1
Snapshot(node_id: str, attribs: dict[AttribKey, AttribInfo], topology_id: tuple[int, ...] | None)
Graph(nodes: list[str], inputs: dict[str, list[str]], containers: frozenset[str])
State(Enum): BORN, WRITTEN, PASS, REBUILT, DELETED, ABSENT
```

`Graph.containers` are subnets whose inside is also in the graph. Their own state is their overall
effect, so `summary` skips them to avoid counting twice.

Functions:

```python
# core/states.py
state_of(key, snapshot, input_snapshots) -> State          # the rules of section 4.1
compute_states(graph, snapshots) -> dict[node_id, dict[AttribKey, State]]
lifetime(states, key) -> set[node_id]
wires(graph, states, key) -> list[tuple[input_id, node_id]]  # wires that carry the key
summary(graph, states, snapshots) -> list[AttribSummary]   # one row per key for the table
# core/report.py
leak_report(entries, exit) -> LeakReport                    # entries[0] is the main input
# core/policy.py
findings(report) -> list[Finding]; parse(text); dump(by_scope); toggle(text, scope, finding, on)
```

`LeakReport` has four lists: leaked locals (born inside, alive at the exit), outer writes,
deleted outer attributes (from the main input only), and rebuilt ("unknown": the topology changed
inside, so a write cannot be detected). It is `state_of` applied across the scope as one node.

`policy.py` stores which findings the user marked intended (section 8, phase 6).

### 5.2 Layer 2: adapter

1. **Graph walk** (`adapter/graph.py`): start at the target node and walk the inputs, inputs before
   outputs. Network dots resolve. The walk enters editable SOP networks (plain subnets and unlocked
   HDAs) from their first output; locked HDAs stay one node. An input from another level is kept as
   a boundary node and not walked further.
2. **Snapshot and cache** (`adapter/snapshot.py`): read `node.geometry()` into a `Snapshot`
   (attributes and groups). Cache by `sessionId()`, valid while `cookCount()` is unchanged.
3. **Cook policy:** "cooked only" (default) never starts a cook: it checks `errors()`, then
   `needsToCook()`, before `geometry()`. "Cook on demand" may cook.
4. **Errors:** a node that fails to cook gets no snapshot and a reason. It and its direct outputs
   have no state (an empty snapshot would fake Born and Deleted). The walk continues.
5. **Scopes** (`adapter/scope.py`): entries and exits of a subnet, HDA, or network box, the leak
   report per exit, and reading and writing the intended-findings parameter.

### 5.3 Layer 3: overlay

`overlay.py` converts states to network editor shapes for the toggled keys.

- Each toggled key gets one color from a fixed palette of eight.
- Node outline by state: Born filled, Written solid, Rebuilt lighter, Pass-through faint, Deleted
  with a cross. Several keys on one node get nested outlines; their wires sit side by side.
- Method (spike S3): the network editor rebuilds its overlay on every UI event, so shapes set once
  are wiped. The overlay wraps `nodegraphhooks.createEventHandler` to add one pending action that
  never completes; nodegraph merges its shapes into every redraw. Closing the panel restores the hook.

### 5.4 Layer 4: ui (Python Panel)

- **Header (both tabs):** "Cook on demand" toggle, "Refresh" button.
- **Lifetime tab:** "Follow display node" (default) or "Use selected" to pin a target. Table with
  columns Show (toggle and color), Name, Class, Type, Born, Deleted, Written, Rebuilt.
  Filters: name (text or glob), class, "Hide standard" (a fixed list in `ui/table_model.py`).
  Row click selects the born node, entering its subnet if needed.
- **Leak report tab:** pick a subnet, HDA, or network box. One group per exit for boxes. Each
  finding has a tickbox for "intended"; unticked findings are red.
- Qt model/view for the table (`QAbstractTableModel` + `QSortFilterProxyModel`). PySide6 only.

### 5.5 Redraw and events

Method (spike S6): **poll, do not subscribe.** There is no "cooked" node event; `InputDataChanged`
fires before the recook. A 250 ms `QTimer`, active while the panel is visible, reads the target and
the cache keys of the chain, and re-reads only nodes whose cook count changed. A check with no
changes costs about 2 ms per 1000 nodes. Node drags are handled by the overlay's pending action.

## 6. Repository layout

```
attribute-helper/
  README.md, README.ja.md, README.zh-TW.md
  LICENSE, CONTRIBUTING.md, CHANGELOG.md, TODO.md
  CLAUDE.md                       # instructions for Claude Code
  install.py                      # one-line install from Houdini's Python Shell
  PaneTabTypeMenu.xml             # adds the panel to New Pane Tab Type > Inspectors
  docs/
    plan.md                       # this document
    attrib_scope_policy.md
    houdini-api-notes.md          # verified hou behavior; overrides this plan
    ui_checklist.md               # manual GUI checks
    spikes/                       # results of the spikes in section 7
    images/                       # README screenshots
  package/
    attribute_helper.json         # Houdini package file
  python/
    attribute_helper/
      core/        model.py, states.py, report.py, policy.py   # no hou
      adapter/     graph.py, snapshot.py, scope.py
      overlay.py
      ui/          panel.py, table_model.py, leak_tab.py
  python_panels/
    attribute_helper.pypanel
  tests/
    core/                         # pytest, no Houdini; fixtures built in code
    houdini/                      # hython tests, networks built in code
  tools/
    run_hython_tests.py
```

### 6.1 Installation (Houdini package)

`install.py`, run from Houdini's Python Shell, writes `<prefs>/packages/attribute_helper.json`
containing `{"package_path": "<repo>/package"}`. The prefs folder comes from
`hou.homeHoudiniDirectory()`, so it is the one the running Houdini reads (spike S5 found two
candidates on Windows). The repo's package file sets `HOUDINI_PATH` and `PYTHONPATH` relative to
itself, so nothing in the repo holds a local path.

## 7. Spikes (do these first)

Each spike is a small hython or UI test. Each spike writes a short result file in `docs/spikes/`. Do not start phase 1 until S1 to S4 are complete.

| ID | Question | Pass condition |
|---|---|---|
| S1 | Does `hou.Attrib` give a data ID in Houdini 22? If not, what is the alternative (for example a hidden wrangle with `attribdataid()`)? | A data ID can be read from Python for all four classes. |
| S2 | Are data IDs reliable? Test typical nodes: Attribute Wrangle, Attribute Create, Merge, Blast, Transform, Copy to Points, Pack, Clean, For-Each, Compile block. | A table of nodes that give false "Written" results. |
| S3 | Which network editor API draws overlay shapes (`hou.NetworkShape*` and the editor shape functions)? Can shapes follow nodes when the user moves them? | A test panel draws an outline on one node and a line on one wire. |
| S4 | Which Qt binding does Houdini 22 use (PySide6 or PySide2)? How does a `.pypanel` file load a module from a package? | A test panel with one table opens from the pane menu. |
| S5 | Confirm the package JSON syntax for `HOUDINI_PATH` and `PYTHONPATH`. | A clean user preference folder loads the panel from the package. |
| S6 | Which event callbacks detect a new cook and a network change? What is the cost? | A list of callbacks and a recommended redraw method. |
| S7 | Do groups have data IDs in HOM? | Result recorded. Decides the group support in phase 3. |

## 8. Phases and acceptance criteria

### Phase 0: Repository setup

- Repository layout of section 6, license, README stub, `CLAUDE.md`.
- pytest runs on `tests/core/` locally. No CI (decided 2026-09-26).

Done when: pytest passes with one placeholder test.

### Phase 1: Core

- `core/` with the data model and the state rules of section 4.
- Fixtures: linear chain, branch and merge, generator node, deleted attribute, same name in two classes.

Done when: all state rules have unit tests. Coverage of `core/` is 90% or more.

### Phase 2: Adapter

- Graph walk, snapshot, cache, cook policy.
- hython tests build test networks with code. Do not commit binary .hip files for tests.

Done when: the hython tests give the correct states for the phase 1 cases on real geometry.

### Phase 3: MVP panel

- Table, filters, toggles, overlay for one network level. Attributes only.

Done when:

1. The user opens the panel, uses the display node as the target, and sees all attributes of the chain.
2. A toggle shows and hides the overlay for one attribute.
3. The overlay follows the nodes when the user moves them.
4. The scene has no changes after use (no undo entries, no changed parameters), except the hidden
   intended-findings parameter when the user ticks a finding.

### Phase 4: Leak report

- Leak report tab for a selected subnet or an HDA.

Done when: a test subnet with one leaked local, one outer write, and one deleted outer attribute gives exactly these three results.

### Phase 5: Depth

- Enter editable subnets and unlocked HDAs. Locked HDAs, including SideFX nodes built as HDAs, stay
  one node (checked from outside with the leak report).
- Groups (if S7 passes) and detail attributes in the table.

### Phase 6: Policy link

- Planned: read declared `in`, `inout`, and `out` lists of a scope and flag violations.
- Built instead (2026-09-26, after trying the lists): the user ticks each leak-report finding that is
  intended (leaked, changed, or deleted); unticked findings are the problems. Ticks are stored in one
  hidden string parameter, `attribute_helper_intended`. See `attrib_scope_policy.md` §7.

## 9. Testing strategy

| Level | Tool | Runs where |
|---|---|---|
| Core unit tests | pytest | Local |
| Adapter tests | hython scripts that build networks with code | Local (needs a Houdini license) |
| UI checks | Manual checklist in `docs/ui_checklist.md` | Local |

Rules:

1. `core/` never imports `hou`. A test checks this rule.
2. Every bug fix adds a fixture or a hython test.

## 10. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Geometry reads start cooks | Slow UI on heavy scenes | "Cooked only" mode as default. Cache by cook count. |
| False "Written" from data IDs | Wrong hints | Result of S2 in the docs. Label "Written" as a hint. |
| Overlay API limits | No overlay, or no update on node move | S3 first. Fallback: highlight in the table and select nodes. |
| Redraw cost | Slow network editor | Redraw only for toggled keys. Throttle the updates. |
| Qt binding changes between versions | Panel does not load | Houdini 22 ships PySide6 only (spike S4). Add a compat import only if a second binding appears. |

## 11. Open-source items

Decisions for the maintainer:

1. **License:** MIT (decided).
2. **Supported versions:** Houdini 22 only (decided).
3. **Name:** `attribute-helper` (decided).

First public release (0.1.0, 2026-10-06): README in three languages with screenshots, install script, known limits, CONTRIBUTING, and CHANGELOG.

## 12. Future work

- Heuristic detection of reads (VEX scan) to show where the inner network uses an attribute.
- Export of the lifetime as a report (Markdown or JSON) for code review of HDAs.
- The scope tool itself (`attrib_scope_policy.md`), with this viewer as its debug view.
