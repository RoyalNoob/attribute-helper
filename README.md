# attrib-lifetime

Python Panel for Houdini 22 that shows where each SOP attribute is born, written,
passed through, and deleted, drawn as a non-destructive overlay in the network editor.

Status: pre-alpha (phase 0). See [docs/attrib_lifetime_plan.md](docs/attrib_lifetime_plan.md).

## Install

Create `$HOUDINI_USER_PREF_DIR/packages/attrib_lifetime.json` (for example
`Documents/houdini22.0/packages/`) with the path to this repo's `package` folder:

    {"package_path": "E:/Repo/attribute-helper/package"}

Restart Houdini. The panel is in the pane-tab menu as **Attribute Lifetime**.

## Development

    pip install pytest
    pytest
