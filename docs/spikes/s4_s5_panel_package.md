# Spikes S4, S5: panel and package

Houdini 22.0.429, 2026-09-26.

## S5: package JSON — PASS (hython, clean prefs folder)

[package/attribute_helper.json](../../package/attribute_helper.json) sets `ATTRIBUTE_HELPER` to
`$HOUDINI_PACKAGE_PATH/..` (the repo root), prepends `python/` to `PYTHONPATH`, and adds the repo
to `HOUDINI_PATH`. No hard-coded path in the repo.

Because the path is relative to the JSON file, do not copy it into prefs. Install with a
one-line redirect in `$HOUDINI_USER_PREF_DIR/packages/attribute_helper.json`:

    {"package_path": "E:/Repo/attribute-helper/package"}

Checked with `HOUDINI_USER_PREF_DIR=<empty dir>/houdini__HVER__` (the `__HVER__` token is required,
otherwise Houdini ignores the variable): `import attribute_helper` works, the repo is on
`HOUDINI_PATH`, and `hou.pypanel.interfaces()` lists `attribute_helper`.

## S4: Python Panel — PASS (GUI)

- Qt binding: PySide6 (see houdini-api-notes.md).
- `python_panels/*.pypanel` under a `HOUDINI_PATH` entry is found automatically, and the panel
  script can `import attribute_helper` from the package.
- `includeInPaneTabMenu` in the `.pypanel` does **not** add it to New Pane Tab Type; it only puts it
  in the Python Panel drop-down. The pane-tab menu needs an `actionItem id="pythonpanel::<name>"`
  in a `PaneTabTypeMenu.xml` on `HOUDINI_PATH` (see the header of `$HFS/houdini/PaneTabTypeMenu.xml`).
  Added at the repo root. Items must go inside an existing `<subMenu>` (as Labs and KineFX do);
  ours is under Inspectors after Node Info.
- GUI check: the entry appears in New Pane Tab Type > Inspectors and in the Python Panel drop-down,
  and the table shows the package import path.

## Gotcha: two prefs folders on Windows

Houdini started from the Start menu uses `Documents/houdini22.0`. hython started from a shell with
`HOME` set (Git Bash) uses `$HOME/houdini22.0`. The package pointer must be in the folder the GUI
uses; checking in hython alone gave a false pass. Put it in both if you run hython from Git Bash.
