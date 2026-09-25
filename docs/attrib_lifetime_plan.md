# Attribute Lifetime Viewer: Project Plan

Working name: `attrib-lifetime`
Target: Houdini 22 (primary). Houdini 21 support is a stretch goal.
Type: Open source Python Panel for the Houdini network editor.
Related document: `attrib_scope_policy.md` (the future scope policy).

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
3. Give a leak report for a subnet or an HDA.
4. Keep the core logic independent of Houdini, so that unit tests run without a Houdini license.
5. Collect data that helps to design the scope policy (see `attrib_scope_policy.md`).

### Non-goals

1. The tool does not change geometry, node colors, or parameters.
2. The tool does not enforce a scope policy. Enforcement is a different project.
3. The tool does not find attribute **reads**. Reads are not visible in cooked geometry. (A later phase can add a heuristic.)
4. The tool does not support contexts other than SOPs in v1.

## 3. Glossary

| Term | Meaning |
|---|---|
| Target node | The node where the upstream walk starts. Default: the display node of the current network. |
| Chain | All nodes upstream of the target node, in the current network level. |
| Snapshot | The list of attributes on the cooked geometry of one node: class, name, type, size, data ID. |
| Attribute key | The pair (class, name). Point `mask` and primitive `mask` are two different keys. |
| State | The status of one attribute key on one node: born, written, pass-through, deleted, absent. |
| Leak | An attribute that is born inside a subnet or an HDA and is alive at its output. |

## 4. Core concepts

### 4.1 State rules

For each node N and each attribute key K, compare the snapshot of N with the snapshots of the inputs of N.

| State | Condition |
|---|---|
| Born | K is not on any input of N. K is on N. |
| Written | K is on at least one input. K is on N. The data ID on N is different from the data ID on all inputs that have K. |
| Pass-through | K is on at least one input. K is on N. The data ID on N is the same as the data ID on one input that has K. |
| Deleted | K is on at least one input. K is not on N. |
| Absent | K is not on any input. K is not on N. |

A node with no inputs (a generator) gives "Born" for all its attributes.

### 4.2 Written is a hint, not a proof

Some nodes change a data ID with no change of values. Example: a Merge node can make new attribute data from all inputs. The UI must show "Written" as a hint. The UI must not describe it as a confirmed change.

### 4.3 Lifetime

The lifetime of K is the set of nodes where the state of K is Born, Written, or Pass-through. The overlay draws this set.

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

Data model (Python dataclasses, frozen where possible):

```python
AttribKey(cls: str, name: str)               # cls: point | prim | vertex | detail
AttribInfo(type: str, size: int, data_id: int | None)
Snapshot(node_id: str, attribs: dict[AttribKey, AttribInfo])
Graph(nodes: list[str], inputs: dict[str, list[str]])   # node_id -> input node_ids
State(Enum): BORN, WRITTEN, PASS, DELETED, ABSENT
```

Functions:

```python
compute_states(graph, snapshots) -> dict[node_id, dict[AttribKey, State]]
lifetime(states, key) -> set[node_id]
summary(states) -> list[AttribSummary]      # one row per key for the UI list
leak_report(graph, snapshots, inner_nodes, entry, exit) -> LeakReport
```

`LeakReport` has three lists:

1. Leaked locals: born inside, alive at the exit.
2. Outer writes: alive at the entry, written inside.
3. Deleted outer attributes: alive at the entry, deleted inside.

### 5.2 Layer 2: adapter

Responsibilities:

1. **Graph walk:** Start at the target node. Walk the inputs. Collect the chain for the current network level. Record the input order of each node.
2. **Snapshot:** Read `node.geometry()` and convert each attribute to `AttribInfo`.
3. **Cache:** Key = (`node.sessionId()`, `node.cookCount()`). A cache hit skips the geometry read.
4. **Cook policy:** Two modes:
   - "Cooked only" (default for heavy scenes): skip nodes that need a cook. Mark them as "not available" in the UI.
   - "Cook on demand": read the geometry, which can start a cook.
5. **Errors:** A node that fails to cook gives an empty snapshot and an error flag. The walk continues.

### 5.3 Layer 3: overlay

Converts states to network editor shapes for the toggled keys.

- Each toggled key gets one color from a fixed palette.
- Node outline: shows the state of that node (Born, Written, Deleted). Pass-through nodes get a thin outline.
- Wire line: a line along each wire between two nodes in the lifetime.
- Several toggled keys on one node: offset the outlines, so that all are visible.

### 5.4 Layer 4: ui (Python Panel)

- **Header:** target node field, "Use display node" button, "Pick" button, cook-mode toggle, "Refresh" button.
- **Table:** one row per attribute key. Columns: visibility toggle, color swatch, name, class, type, born node, deleted node, write count.
- **Filters:** name search (glob), class filter, "hide standard attributes" toggle (`P`, `N`, `Cd`, and so on; the list is configurable).
- **Row click:** selects the born node in the network editor.
- **Leak report tab:** select a subnet or an HDA, then show the three lists of section 5.1.
- Use a Qt model/view (`QAbstractTableModel` + `QSortFilterProxyModel`). Do not use a plain table widget.

### 5.5 Redraw and events

The overlay must update when:

1. the user toggles a key,
2. the user changes the target node,
3. a node in the chain cooks again,
4. the user moves nodes or changes the network,
5. the user changes the network level (enters or leaves a subnet).

Method: node event callbacks on the chain nodes, plus a light panel timer as a fallback. The spike in section 7 decides the final method.

## 6. Repository layout

```
attrib-lifetime/
  README.md
  LICENSE
  CONTRIBUTING.md
  CHANGELOG.md
  CLAUDE.md                       # instructions for Claude Code (see appendix A)
  docs/
    plan.md                       # this document
    attrib_scope_policy.md
    spikes/                       # results of the spikes in section 7
  package/
    attrib_lifetime.json          # Houdini package file
  python/
    attrib_lifetime/
      __init__.py
      core/
        model.py
        states.py
        report.py
      adapter/
        graph.py
        snapshot.py
        cache.py
      overlay/
        shapes.py
        palette.py
      ui/
        qt_compat.py              # one import point for PySide
        panel.py
        table_model.py
  python_panels/
    attrib_lifetime.pypanel
  tests/
    core/                         # pytest, no Houdini
      fixtures/                   # JSON graphs and snapshots
    houdini/                      # hython tests, run locally
  tools/
    run_hython_tests.py
```

### 6.1 Installation (Houdini package)

The user copies `package/attrib_lifetime.json` into `$HOUDINI_USER_PREF_DIR/packages/` and sets the path of the repository in the file. The package adds the repository to `HOUDINI_PATH` and the `python/` folder to `PYTHONPATH`. Spike S5 confirms the package syntax.

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
- pytest runs on `tests/core/` in CI (GitHub Actions). CI does not need Houdini.

Done when: CI passes with one placeholder test.

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
4. The scene has no changes after use (no undo entries, no changed parameters).

### Phase 4: Leak report

- Leak report tab for a selected subnet or an HDA.

Done when: a test subnet with one leaked local, one outer write, and one deleted outer attribute gives exactly these three results.

### Phase 5: Depth

- Enter subnets and HDAs (a tree of network levels).
- Groups (if S7 passes) and detail attributes in the table.

### Phase 6: Policy link (later)

- Read the declared `in`, `inout`, and `out` lists of a scope (see `attrib_scope_policy.md`).
- Flag violations in the table.

## 9. Testing strategy

| Level | Tool | Runs where |
|---|---|---|
| Core unit tests | pytest | CI and local |
| Adapter tests | hython scripts that build networks with code | Local (needs a Houdini license) |
| UI checks | Manual checklist in `docs/ui_checklist.md` | Local |

Rules:

1. `core/` never imports `hou`. A CI test checks this rule.
2. Every bug fix adds a fixture or a hython test.

## 10. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Geometry reads start cooks | Slow UI on heavy scenes | "Cooked only" mode as default. Cache by cook count. |
| False "Written" from data IDs | Wrong hints | Result of S2 in the docs. Label "Written" as a hint. |
| Overlay API limits | No overlay, or no update on node move | S3 first. Fallback: highlight in the table and select nodes. |
| Redraw cost | Slow network editor | Redraw only for toggled keys. Throttle the updates. |
| Qt binding changes between versions | Panel does not load | One import point (`qt_compat.py`). |

## 11. Open-source items

Decisions for the maintainer:

1. **License:** MIT or Apache-2.0. (Apache-2.0 adds a patent grant.)
2. **Supported versions:** Houdini 22 only, or 21 and 22.
3. **Name:** `attrib-lifetime` is a working name.

Files for the first public release: README with a GIF of the overlay, install steps, a list of known limits (section 4.2, non-goals), CONTRIBUTING with the test commands, and CHANGELOG.

## 12. Future work

- Heuristic detection of reads (VEX scan) to show where the inner network uses an attribute.
- Export of the lifetime as a report (Markdown or JSON) for code review of HDAs.
- The scope tool itself (`attrib_scope_policy.md`), with this viewer as its debug view.

---

## Appendix A: Starter content for CLAUDE.md

```markdown
# attrib-lifetime

Python Panel for Houdini 22 that shows attribute lifetimes in the network editor.
Read docs/plan.md before you change the architecture.

## Rules
- python/attrib_lifetime/core/ must not import hou. Keep it pure Python.
- Do not change geometry, node colors, or parameters from the tool.
- Do the spikes (docs/plan.md, section 7) before phase 1. Write each result to docs/spikes/.
- If you are not sure of a hou or Qt API, write a spike. Do not guess.

## Commands
- Core tests: pytest tests/core
- Houdini tests: hython tools/run_hython_tests.py

## Style
- Python 3, type hints, dataclasses for the data model.
- Short functions. One responsibility for each module.
```
