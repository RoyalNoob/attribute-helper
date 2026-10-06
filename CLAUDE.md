# attribute-helper

Python Panel for Houdini 22 that shows attribute lifetimes in the network editor.
Read docs/plan.md before you change the architecture.
Read docs/houdini-api-notes.md before you use a hou API; it overrides the plan where they differ.

## Rules
- python/attribute_helper/core/ must not import hou. Keep it pure Python. (tests/core/test_no_hou.py enforces this.)
- Track progress in TODO.md: tick items and add a Log line in the same commit as the work.
- Do not change geometry, node colors, or parameters from the tool. Only exception: the hidden
  `attribute_helper_intended` parameter, written when the user ticks a finding (one undo step).
- Do the spikes (plan, section 7) before phase 1. Write each result to docs/spikes/.
- If you are not sure of a hou or Qt API, write a spike. Do not guess.
- Houdini 22 ships PySide6 only: import PySide6 directly, no qt_compat layer.

## Commands
- Core tests (run before every commit; no CI): pytest --cov=attribute_helper.core --cov-fail-under=90
- Houdini tests: "C:/Program Files/Side Effects Software/Houdini <version>/bin/hython.exe" tools/run_hython_tests.py
  (use the installed build; 22.0.459 as of 2026-10-06). The command must fail loudly: do not pipe it into tail.

## Style
- Python 3, type hints, dataclasses for the data model.
- Short functions. One responsibility for each module.
