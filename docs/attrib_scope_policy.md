# Attrib Scope: Policy for Attribute Management and Collision Resolution

Status: Draft. This policy replaces the v1 model ("declare locals, stash collisions").

## 1. Problem

Houdini has no attribute scope. An attribute that a node creates stays on the geometry and goes downstream. When you package a node network into a subnet or an HDA, this causes two errors:

1. **Leak:** Temporary attributes of the inner network go out of the subnet.
2. **Collision:** The inner network writes to an attribute that already exists outside, and damages the outer value.

## 2. Why v1 is not sufficient

The v1 tool declares the **locals**. Everything that is not declared leaks or is shared. A real function declares its **signature**. Everything that is not in the signature is local.

| Programming concept | v1 tool | Problem |
|---|---|---|
| Undeclared names are local | Locals must be declared or scanned | A missed name leaks, or overwrites an outer value. |
| Arguments are passed by value | Inner nodes can write any outer attribute | An accidental write to `Cd` goes downstream. |
| Shadowing: the callee reads the outer value, then assigns its own copy | A local name hides the outer value completely | The inner network cannot read `mask` and then change it locally. |
| The callee cannot destroy the caller's stack | The stash lives on the same geometry as the inner work | Attribute Delete `*`, Clean, Pack, or a VDB conversion destroys the stash. Restore fails. |
| The caller names the return value | An export keeps its inner name | An export can collide with an outer name. The collision is silent. |

## 3. Policy

**Rule: A scope is a function. It receives a copy of everything. It returns only what it declares. The caller names the return values.**

### 3.1 Declare the signature, not the locals

A scope has three lists:

| List | Meaning | Default |
|---|---|---|
| `in` | Outer attributes that the inner network can read | `*` (all) |
| `inout` | Outer attributes that the inner network can change (for example `P`, `Cd`) | empty |
| `out` | New attributes that the scope returns | empty |

All other names are local. You never declare locals. The heuristic scan is not necessary.

### 3.2 Pass all outer attributes by value

End does not trust the inner result. End builds its output from the original geometry (the Begin → End wire). End copies only the `inout` and `out` attributes from the inner result.

Results:

- A local can have the same name as an outer attribute. The inner network reads the outer value and writes its own copy. The outer value comes back unchanged. This is correct shadowing.
- An undeclared write to an outer attribute cannot leak. Collision of locals is not possible by construction.
- The outer values live on a side branch. The inner network cannot destroy them.
- Houdini geometry is copy-on-write. The side branch is cheap.

### 3.3 Resolve collisions only at the return boundary

An `out` entry can rename at the call site:

```
mask -> fx_mask
height
```

If an `out` name already exists outside and is not in `inout`, End applies the collision action:

| Action | Behavior |
|---|---|
| `error` (default) | End stops the cook and names the attribute. |
| `overwrite` | The returned value replaces the outer value. |
| `rename` | End adds a suffix and gives a warning with the new name. |

This boundary is the only place where a collision can occur.

### 3.4 Warn about undeclared writes

End compares `attribdataid()` between the Begin output and the inner result. If an outer attribute changed and is not in `inout`, End discards the change and gives a warning.

Data IDs can give false positives. Some nodes change the data ID without a change of values. For this reason, the result is a warning, not an error.

## 4. Changes to topology

Pass-by-value needs element correspondence. If the inner network adds, deletes, or reorders elements, End cannot copy values back by element number.

| Mode | Condition | End behavior |
|---|---|---|
| Attribute function (default) | Topology does not change | End copies `inout` and `out` back onto the original by element number. End checks the element counts and gives an error if they differ. |
| Geometry function | Topology changes | The inner result becomes the new geometry. Outer attributes travel through normal Houdini interpolation. Locals are discarded. |

Protection of outer attributes in geometry-function mode:

1. Copy back by a matching `id` attribute, if the geometry has one.
2. Stash with a reserved prefix (the v1 method). The inner network can still destroy the stash.

Limit: When a node creates new elements, "the outer value" has no single correct meaning for those elements. The policy does not hide this limit.

## 5. Groups and other data

- Groups follow the same rules as attributes. Groups use their own lists (`in_groups`, `inout_groups`, `out_groups`) or a `group:` prefix in the same lists.
- Detail attributes follow the same rules. Element correspondence is always true for detail.
- Intrinsics (packed transforms, volume names) are not in scope for this policy.

## 6. Implementation notes

- End uses native SOPs: Attribute Copy (by element number, or by `id`) for `inout` and `out`, with rename. The per-type VEX copy of v1 is not necessary.
- One Detail wrangle does the checks: element counts, `out` collisions, and undeclared writes (data IDs).
- Python is only necessary for the wrap tool and the UI. The cook does not need Python. HDAs stay portable.

## 7. Open questions

1. Which mode is most frequent in real work: attribute function or geometry function?
2. Must `in` be enforced (strip undeclared inputs), or is `in` documentation only?
3. Is the data ID warning reliable enough in Houdini 22? This needs a test on typical nodes.
4. Must the collision action be set per `out` entry, or per scope?
