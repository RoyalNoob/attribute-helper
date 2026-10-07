# Changelog

## 0.1 — 2026-10-07

First release. Houdini 22 only, SOPs only.

### Lifetime tab
- Table of every attribute and group upstream of a target node (the display node, or a pinned
  node): class, type, where it is born and deleted, how many nodes write or rebuild it.
- Filters: name (text or glob), class, hide standard attributes.
- Overlay on the network editor for ticked attributes: born, written, rebuilt, pass-through, and
  deleted nodes, plus the wires that carry the attribute. Follows node drags; never changes the scene.
- Walks into editable subnets and unlocked HDAs; locked HDAs stay one node.
- "Cooked only" by default (never starts a cook); optional cook on demand.
- Live update: polls cook counts four times a second and re-reads only nodes that cooked again.

### Leak report tab
- Scopes: a subnet, an HDA, or a network box (one report per exit).
- Findings: leaked locals, outer writes, deleted outer attributes, unknown (topology changed).
- Tick findings as intended; unticked findings stay red. Ticks are stored in a hidden parameter
  (`attribute_helper_intended`), one undo step each.

### Install and docs
- `install.py`: one line in Houdini's Python Shell writes the package pointer to the right prefs folder.
- READMEs in English, Japanese, and Traditional Chinese, with screenshots and a GIF.
- CONTRIBUTING.md: issues are welcome; pull requests are not accepted (fork or clone instead).
