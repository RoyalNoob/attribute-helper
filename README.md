# attribute-helper

Python Panel for Houdini 22 that shows where each SOP attribute is born, written,
passed through, and deleted, drawn as a non-destructive overlay in the network editor.

Status: pre-alpha (phase 2 of 6 done). See [docs/plan.md](docs/plan.md).

## Install

Create `$HOUDINI_USER_PREF_DIR/packages/attribute_helper.json` (on Windows
`Documents/houdini22.0/packages/`) with the path to this repo's `package` folder:

    {"package_path": "E:/Repo/attribute-helper/package"}

Restart Houdini. The panel is in the New Pane Tab Type > Inspectors > **Attribute Helper**.

## Development

    pip install pytest pytest-cov
    pytest --cov=attribute_helper.core
