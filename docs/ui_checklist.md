# UI checklist

Manual checks in the Houdini GUI. Run after any change to `ui/` or `overlay.py`.
Restart Houdini first (the panel module is imported once per session).

## Setup

In a Geometry node, build: Box → Attribute Wrangle (`f@mask = @P.y > 0;`) → Transform →
Attribute Delete (delete point `mask`) → Null, with the display flag on the Null.
Open New Pane Tab Type > Inspectors > Attribute Helper next to the network editor.

## Checks

1. **Table:** with "Hide standard" on, the table lists `mask` (point, born at the wrangle,
   deleted at the Attribute Delete). Turn "Hide standard" off: `P` appears, born at the box,
   Written = 1 (the Transform).
2. **Filters:** type `mas` → only `mask`. Pick "prim" in the class list → empty. Reset.
3. **Toggle:** tick `mask`. Orange outlines appear: filled on the wrangle (born), faint on the
   Transform (pass-through), a cross on the Attribute Delete (deleted). Orange wires run
   wrangle → Transform → Attribute Delete, none after it. Untick: all gone.
4. **Two keys:** turn "Hide standard" off, tick `mask` and `P`. Two colors, nested outlines,
   side-by-side wires.
5. **Follows moves:** drag nodes; outlines and wires follow. Pan and zoom.
6. **Live update:** change the wrangle to `f@mask2 = 1;`. Within a second the table shows
   `mask2` instead of `mask`, without clicking Refresh.
7. **Cook mode:** add a new Transform after the Null without displaying it, select it, click
   "Use selected". The status line says nodes need a cook, and the new node is not in the
   overlay. Tick "Cook on demand": it is included.
8. **Levels:** dive out of the Geometry node: overlay gone, the table clears (no SOP target).
   Dive back in: both return.
9. **Row click:** click a row's name: its born node gets selected.
10. **No scene changes:** after all of the above, Edit > Undo History shows only your own edits,
    none from the panel.
11. **Close:** close the panel tab. Overlay gone; moving the mouse over the editor does not bring
    it back.

## Leak report tab

Setup: Box → Attribute Wrangle (`f@a = 1; f@b = 2;`) → Subnet (display flag on the Subnet). Inside
the subnet: input 1 → Attribute Wrangle (`f@a = 5; f@tmp = 1;`) → Attribute Delete (point `b`),
with the display flag on the Attribute Delete.

12. **Report:** select the Subnet, open the Leak report tab, click "Use selected subnet / HDA".
    Sections show: Leaked locals 1 (`tmp`), Outer writes 1 (`a`), Deleted outer 1 (`b`), Unknown 0.
13. **Live:** inside the subnet, add `f@tmp2 = 1;` to the wrangle. Leaked locals becomes 2 without
    clicking anything.
14. **Topology:** add a Blast inside (delete point 0) before the output. `a` moves from Outer writes
    to Unknown.
15. **Deleted scope:** delete the Subnet. The tab says the node was deleted.

## Depth: subnets and groups

Setup: Box → Subnet → Null (display flag on the Null). Inside the subnet: input 1 → Attribute
Wrangle (`f@tmp = 1;`) → Group Create (group name `top`), display flag on the Group Create.

16. **Born inside:** on the Lifetime tab, `tmp` shows Born = `subnet1/attribwrangle1`, and the
    point group `top` appears (class `group:prim`). Each is listed once, not also at the subnet.
17. **Overlay at the outer level:** tick `tmp`. The Subnet gets the filled "born" outline, and the
    Null a pass-through outline.
18. **Row click dives in:** click the `tmp` row. The editor enters the subnet and selects the
    wrangle. (With "Follow display node" on, the table now shows the inside of the subnet.)
19. **Locked HDAs stay closed:** an Attribute Wrangle outside the subnet is one row source, not
    expanded (its internals never appear in Born).
