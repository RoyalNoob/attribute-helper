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

## S4: Python Panel — partial

- Qt binding: PySide6 (see houdini-api-notes.md).
- `python_panels/*.pypanel` under a `HOUDINI_PATH` entry is found automatically, and the panel
  script can `import attribute_helper` from the package.
- **Not yet checked in the GUI:** the panel opens from the pane-tab menu and shows the table.
