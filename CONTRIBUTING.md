# Contributing

Thanks for helping. This is a small project: issues and pull requests are both welcome.

## Before you start

- Read [docs/plan.md](docs/plan.md) for the architecture, and
  [docs/houdini-api-notes.md](docs/houdini-api-notes.md) before you use a `hou` API. The notes
  record what was actually verified in Houdini 22 and override the plan where they differ.
- [TODO.md](TODO.md) shows what is done and what is open.
- For a larger change (a new state, a new scope type, a change to the leak rules), open an issue
  first so we can agree on the behavior.

## Setup

1. Install the panel from your clone, as in the [README](README.md#install).
2. Install the test tools for the core tests (any Python 3.11+):

   ```bash
   pip install pytest pytest-cov
   ```

Houdini 22 is needed for the adapter and UI tests and for GUI checks.

## Layout

| Folder | What | May import `hou`? |
|---|---|---|
| `python/attribute_helper/core/` | Data model, state rules, leak report, intended findings | **No** |
| `python/attribute_helper/adapter/` | Graph walk, geometry snapshots, cache, scopes | Yes |
| `python/attribute_helper/overlay.py` | Network editor overlay | Yes (GUI only) |
| `python/attribute_helper/ui/` | The Python Panel (PySide6) | Yes |
| `tests/core/` | pytest, no Houdini | — |
| `tests/houdini/` | hython tests, build their networks in code | — |
| `docs/spikes/` | Small experiments that settled a Houdini API question | — |

## Rules

- `core/` never imports `hou`. `tests/core/test_no_hou.py` fails if it does.
- The tool must not change the scene: no geometry, node colors, or parameters. The one exception
  is the hidden `attribute_helper_intended` parameter, written only when the user ticks a finding,
  as one undo step.
- Not sure how a `hou` or Qt API behaves? Write a small spike (a hython script) and record the
  result in `docs/spikes/` or `docs/houdini-api-notes.md`. Do not guess.
- Import PySide6 directly. Houdini 22 ships no other binding.
- Python 3, type hints, dataclasses for the data model, short functions.
- Every bug fix adds a test (core or hython) that fails without the fix.
- Files use LF line endings (`.gitattributes` enforces this).

## Tests

Run both before you open a pull request.

Core (no Houdini):

```bash
python -m pytest --cov=attribute_helper.core --cov-fail-under=90
```

Adapter and UI (Houdini 22; use your installed build):

```bash
"<Houdini install>/bin/hython" tools/run_hython_tests.py
```

The runner prints `PASS` / `FAIL` per test and exits non-zero on failure. Do not pipe it into
something that hides the exit code.

If you changed `ui/` or `overlay.py`, also run the relevant parts of
[docs/ui_checklist.md](docs/ui_checklist.md) in the Houdini GUI, and say in the pull request which
checks you ran.

## Pull requests

- One topic per pull request.
- Update [TODO.md](TODO.md) (tick items, add a Log line) and [CHANGELOG.md](CHANGELOG.md) in the
  same pull request.
- If behavior that users see changes, update [README.md](README.md). The Japanese and Traditional
  Chinese READMEs can follow later; mention it in the pull request if you did not update them.
- Say which Houdini build you tested with (Help > About Houdini).

By contributing, you agree that your contribution is licensed under the [MIT license](LICENSE).
