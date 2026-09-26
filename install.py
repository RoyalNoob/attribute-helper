"""Install attribute-helper for the current Houdini user.

In Houdini, open Windows > Python Shell and run (with your path to this file):

    import runpy; runpy.run_path(r"E:/Repo/attribute-helper/install.py")

It writes <your Houdini prefs>/packages/attribute_helper.json pointing at this folder. Running it
inside Houdini uses the prefs folder that Houdini actually reads. Restart Houdini afterwards.
To uninstall, delete the file it prints.
"""
import json
from pathlib import Path

import hou

repo = Path(__file__).resolve().parent
target = Path(hou.homeHoudiniDirectory()) / "packages" / "attribute_helper.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps({"package_path": (repo / "package").as_posix()}) + "\n", encoding="utf-8")
print(f"Installed: {target}\n"
      "Restart Houdini, then open New Pane Tab Type > Inspectors > Attribute Helper.")
