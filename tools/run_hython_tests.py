"""Run tests/houdini/test_*.py inside hython (no pytest there).

Usage: hython tools/run_hython_tests.py
Each test_* function gets an empty scene. Exit code 1 if any test fails.
"""
import importlib
import sys
import traceback
from pathlib import Path

import hou

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python"), str(ROOT / "tests" / "houdini")]

failed = 0
for path in sorted((ROOT / "tests" / "houdini").glob("test_*.py")):
    module = importlib.import_module(path.stem)
    for name in (n for n in dir(module) if n.startswith("test_")):
        hou.hipFile.clear(suppress_save_prompt=True)
        try:
            getattr(module, name)()
            print(f"PASS {path.stem}.{name}")
        except Exception:
            failed += 1
            print(f"FAIL {path.stem}.{name}\n{traceback.format_exc()}")
print(f"{failed} failed")
sys.exit(1 if failed else 0)
