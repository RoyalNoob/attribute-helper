# attribute-helper

A Python Panel for Houdini 22 that shows where each SOP attribute is born, written, passed
through, and deleted, drawn as an overlay on the network editor. It also reports what a subnet,
HDA, or network box leaks to the rest of the network, and lets you mark each finding as intended.

Houdini has no attribute scope: whatever a node creates travels downstream. This panel makes that
visible, so temporary attributes that escape a subnet, or outer attributes that get overwritten,
are easy to spot.

Status: pre-alpha. All six phases of [docs/plan.md](docs/plan.md) are done. Houdini 22 only.

## Install

1. Get this repository onto your machine (clone or download), anywhere you like.
2. In Houdini, open **Windows** > **Python Shell** and run this line, with your path to
   `install.py`:

   ```python
   import runpy; runpy.run_path(r"E:/Repo/attribute-helper/install.py")
   ```

   It prints where it installed. It only writes one small file,
   `<Houdini prefs>/packages/attribute_helper.json`, which points Houdini at this folder.
3. Restart Houdini.
4. Open the panel: on any pane, click **+** > **New Pane Tab Type** > **Inspectors** >
   **Attribute Helper**. Put it next to a network editor.

If you move the repository, run the install line again from the new place.

<details>
<summary>Install by hand instead</summary>

Create `attribute_helper.json` in the `packages` folder of your Houdini preferences
(`$HOUDINI_USER_PREF_DIR`: on Windows usually `Documents/houdini22.0`, on Linux `~/houdini22.0`,
on macOS `~/Library/Preferences/houdini/22.0`), with your path and forward slashes:

```json
{"package_path": "E:/Repo/attribute-helper/package"}
```

On Windows, Houdini started from the Start menu reads `Documents/houdini22.0`, but a shell with
`HOME` set (Git Bash) makes it read `$HOME/houdini22.0` instead. The install script avoids this by
asking the running Houdini where its preferences are.

</details>

## Quick start

1. Dive into a SOP network with a few nodes and a display flag.
2. The **Lifetime** tab lists every attribute of the chain above the display node.
3. Tick an attribute. Its lifetime is drawn on the network editor.
4. To check a subnet, select it, open the **Leak report** tab, and click
   **Use selected subnet / HDA / box**.

## The Lifetime tab

### Target

The panel looks at one **target** node and everything upstream of it in the same network.

- **Follow display node** (default): the target is the display node of the network the editor
  shows. It follows you when you dive in and out, or move the display flag.
- **Use selected**: pin the selected SOP as the target. Tick **Follow display node** again to
  unpin.

The line under the filters shows the target and how many nodes were read.

### Cook on demand

Reading a node's geometry can start a cook, which can be slow in heavy scenes.

- **Off** (default): only nodes that are already cooked are read. Nodes that need a cook are left
  out, and the status line says how many. Display the node, or turn the option on, to include them.
- **On**: nodes are cooked when needed.

**Refresh** clears the panel's cache and reads everything again. You rarely need it: the panel
checks for changes four times a second while it is visible, and re-reads only the nodes that
cooked again.

### Table

One row per attribute (and per group) in the chain:

| Column | Meaning |
|---|---|
| Show | Tick to draw this attribute's lifetime on the network editor. The tick shows its color. |
| Name, Class, Type | `point`, `prim`, `vertex`, `detail`, or `group:point`, `group:prim`, `group:vertex`, `group:edge` for groups. |
| Born | The node(s) that create it. Nodes inside a subnet show as `subnet1/node`. |
| Deleted | The node(s) that remove it. |
| Written | How many nodes change it. A hint: see [States](#states). |
| Rebuilt | How many nodes rebuild the topology while it survives (a write cannot be detected there). |

Filters:

- **Name filter**: plain text matches anywhere in the name (`mas` finds `mask`); `*`, `?`, and
  `[...]` work as wildcards.
- **Class**: show one class only.
- **Hide standard** (default on): hides common attributes such as `P`, `N`, `Cd`, `uv`, `v`,
  `id`, `pscale`, `orient`, `name`.

Click a column header to sort. Click a row's name to select the node where the attribute is born;
if it was born inside a subnet, the editor goes there.

### Overlay

Each ticked attribute gets its own color (eight colors, then they repeat). For that attribute:

| On the network editor | Meaning |
|---|---|
| Filled outline | **Born** here |
| Solid outline | **Written** here |
| Lighter outline | **Rebuilt** here (topology changed) |
| Faint outline | **Passed through** unchanged |
| Outline with a cross | **Deleted** here |
| Colored wire | The attribute travels along this wire |

With several attributes ticked, outlines nest and wires sit side by side. The overlay follows
nodes as you drag them, and only shows in the network that holds the target. It never changes
node colors or anything else in the scene. Closing the panel removes it.

### Subnets and HDAs

The chain includes the inside of **editable** networks: plain subnets and unlocked HDAs. An
attribute created inside shows its real birthplace (`subnet1/attribwrangle1`), and at the outer
level the subnet's outline shows its overall effect (for example, "born" if something is created
inside).

**Locked HDAs stay one node**, including SideFX nodes built as HDAs (Attribute Wrangle, Solver,
and many more), so their internals do not flood the table. Use the Leak report to check a locked
HDA from outside.

## States

For each node and each attribute, the panel compares the node's geometry with its inputs, using
Houdini's per-attribute data IDs:

| State | Meaning |
|---|---|
| Born | Not on any input, present here. |
| Written | On an input, present here, and its data changed. **A hint**: a few nodes change data without changing values. |
| Pass-through | Unchanged from an input. |
| Rebuilt | Present here, but the node changed the topology (Blast, Merge of two inputs, Copy to Points, Pack, Clean, For-Each…). Every attribute gets new data then, so a write cannot be told apart from a copy. |
| Deleted | On the node's **first** input, gone here. Attributes that only exist on other inputs (a wrangle's second input, the points of Copy to Points) are read, not passed on, so they are not "deleted". |

A node that failed to cook, or that needs a cook while **Cook on demand** is off, has no state.
The nodes right after it have none either, since there is nothing to compare with.

## The Leak report tab

The leak report treats one **scope** as a single step and compares what comes out with what went
in.

### Choosing a scope

Select a scope in the network editor and click **Use selected subnet / HDA / box**:

- **Subnet or HDA** (locked or not): compared from its inputs to its output.
- **Network box**: the nodes inside the box (including nested boxes). The inputs are the wires
  coming into the box; the output is each node whose output leaves the box. A box with several
  outputs gets one report per output ("Exit: …"). If nothing leaves the box, its last nodes are
  the outputs.

If both a box and a node are selected, the box is used. The report updates live while the tab is
visible.

### Findings

| Section | Meaning |
|---|---|
| Leaked locals | Created inside, still there at the output. |
| Outer writes | Came in from outside and were changed inside (a hint, like Written). |
| Deleted outer attributes | Came in on the main input and were removed inside. |
| Unknown | Came in from outside, but the topology changed inside, so a write cannot be detected. |

### Marking findings as intended

Not every finding is a mistake: a subnet is often meant to produce an attribute. Tick each finding
that is **intended**. Unticked findings stay red, and the status line counts them. What is left
red is what to fix.

- A tick means one of three intents: **leaked**, **changed**, or **deleted**. An outer write and
  an unknown both count as "changed", so adding a Merge later (which turns writes into unknowns)
  keeps your ticks.
- Ticks that no longer match anything (for example, you removed the node that created the
  attribute) are listed under **Marked intended, no longer found**. Untick them to forget them.
- Each tick is one undo step: "Attribute Helper: mark finding intended".

Where ticks are saved:

- **Subnet or HDA**: in a hidden string parameter `attribute_helper_intended` on that node. It is
  created on your first tick and saved with the hip file. On an HDA it is a spare parameter of
  that node, not part of the HDA definition, so each instance keeps its own ticks. It does not
  appear in the parameter pane; Edit Parameter Interface lists it.
- **Network box**: boxes have no parameters, so the same hidden parameter is created on the
  network that contains the box, one line per finding, under the box name. **Renaming the box
  loses its ticks.**

The stored text is one line per finding, `<scope> <intent> <class> <name>`, for example
`. leaked point tmp`. The panel writes it; you should not need to edit it by hand.

This is the only change the tool ever makes to a scene.

## Known limits

- SOPs only.
- Reads are not detected: an attribute that a node only reads looks like pass-through.
- "Written" is a hint, and "Rebuilt" / "Unknown" cannot say whether a value changed.
- On nodes with several inputs (Merge), overlay wires end at the top centre of the node, not at
  the exact input connector.
- A subnet with several outputs is followed from its first output only.
- Renaming a network box loses its intended ticks.
- With several network editors open, the target follows the first one.

## Uninstall

Delete the `attribute_helper.json` file that the install script printed (in your Houdini
preferences `packages` folder) and restart Houdini.
Nodes where you ticked findings keep the hidden `attribute_helper_intended` parameter; remove it
in Edit Parameter Interface if you want to.

## Development

- Architecture, decisions, and progress: [docs/plan.md](docs/plan.md), [TODO.md](TODO.md),
  [docs/attrib_scope_policy.md](docs/attrib_scope_policy.md),
  [docs/houdini-api-notes.md](docs/houdini-api-notes.md), and spike results in
  [docs/spikes/](docs/spikes/).
- `python/attribute_helper/core/` is pure Python (no `hou`), tested with pytest:

  ```bash
  pip install pytest pytest-cov
  python -m pytest --cov=attribute_helper.core --cov-fail-under=90
  ```

- Adapter and UI tests run in hython (they build their networks in code):

  ```bash
  "C:/Program Files/Side Effects Software/Houdini 22.0.429/bin/hython.exe" tools/run_hython_tests.py
  ```

- GUI checks: [docs/ui_checklist.md](docs/ui_checklist.md).

MIT license. See [LICENSE](LICENSE).
