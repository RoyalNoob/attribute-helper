# Contributing

**Pull requests are not accepted.** This is a personal tool shared as is. I don't have time to
review code or run it as a community open-source project, so pull requests will be closed
without review.

What you can do instead:

- **Report a bug or request a feature:** open an [issue](https://github.com/RoyalNoob/attribute-helper/issues). Include your Houdini build
  (Help > About Houdini) and, for bugs, the smallest network that shows the problem.
- **Change it yourself:** fork or clone the repository and make any changes you like. The MIT
  license allows this, including in commercial work.

The rest of this file is for anyone working on their own copy.

## Before you start

- Read [docs/plan.md](docs/plan.md) for the architecture, and
  [docs/houdini-api-notes.md](docs/houdini-api-notes.md) before you use a `hou` API. The notes
  record what was actually verified in Houdini 22 and override the plan where they differ.
- [TODO.md](TODO.md) shows what is done and what is open.

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

Run both after each change.

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
[docs/ui_checklist.md](docs/ui_checklist.md) in the Houdini GUI.

## Keeping your copy tidy

- Track your changes in [TODO.md](TODO.md) and [CHANGELOG.md](CHANGELOG.md).
- If behavior that users see changes, update [README.md](README.md).
