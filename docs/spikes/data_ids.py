"""Spikes S1, S2, S7: data IDs on attributes and groups.

Run: hython docs/spikes/data_ids.py
Prints a Markdown report. Results are summarized in docs/spikes/data_ids.md.
"""
import hou

CLASSES = {
    "point": lambda g: g.pointAttribs(),
    "prim": lambda g: g.primAttribs(),
    "vertex": lambda g: g.vertexAttribs(),
    "detail": lambda g: g.globalAttribs(),
}
GROUPS = {
    "point": lambda g: g.pointGroups(),
    "prim": lambda g: g.primGroups(),
    "vertex": lambda g: g.vertexGroups(),
    "edge": lambda g: g.edgeGroups(),
}


def snapshot(node):
    g = node.geometry()
    snap = {}
    for cls, get in CLASSES.items():
        for a in get(g):
            snap[(cls, a.name())] = a.dataId().vexAttribDataId()
    for cls, get in GROUPS.items():
        for grp in get(g):
            snap[(f"group:{cls}", grp.name())] = grp.dataId().vexAttribDataId()
    return snap, g.topologyDataId()


def wrangle(parent, src, code, cls=None, name="w"):
    n = parent.createNode("attribwrangle", name)
    n.setInput(0, src)
    n.parm("snippet").set(code)
    if cls is not None:
        n.parm("class").set(cls)
    return n


def build(geo):
    grid = geo.createNode("grid")
    grid.parmTuple("size").set((2, 2))
    grid.parm("rows").set(3)
    grid.parm("cols").set(3)
    base = wrangle(geo, grid, "", name="base")
    # One attribute per class and one group per class, all untouched downstream.
    base.parm("snippet").set(
        'f@a = @ptnum;\n'
        'setprimattrib(0, "pa", 0, 1.0);\n'
        'setvertexattrib(0, "va", 0, -1, 1.0);\n'
        'setdetailattrib(0, "da", 1.0);\n'
        'setpointgroup(0, "grp", 0, 1);\n'
        'setprimgroup(0, "pgrp", 0, 1);\n'
    )
    cases = {}  # name -> (node, {keys the node is meant to touch})

    null = geo.createNode("null"); null.setInput(0, base)
    cases["Null"] = (null, set())

    cases["Attribute Wrangle (writes @w)"] = (
        wrangle(geo, base, "f@w = 1;"), {("point", "w")})

    ac = geo.createNode("attribcreate::2.0"); ac.setInput(0, base)
    ac.parm("name1").set("c")
    cases["Attribute Create (c)"] = (ac, {("point", "c")})

    ad = geo.createNode("attribdelete"); ad.setInput(0, base)
    ad.parm("ptdel").set("a")
    cases["Attribute Delete (a)"] = (ad, {("point", "a")})

    xf = geo.createNode("xform"); xf.setInput(0, base)
    xf.parm("tx").set(1)
    cases["Transform"] = (xf, {("point", "P")})

    bl = geo.createNode("blast"); bl.setInput(0, base)
    bl.parm("group").set("0"); bl.parm("grouptype").set("points")
    cases["Blast (1 point)"] = (bl, None)

    m1 = geo.createNode("merge"); m1.setInput(0, base)
    cases["Merge (1 input)"] = (m1, set())

    m2 = geo.createNode("merge"); m2.setInput(0, base); m2.setInput(1, xf)
    cases["Merge (2 inputs)"] = (m2, None)

    pts = geo.createNode("add"); pts.parm("points").set(2)
    pts.parm("usept0").set(1); pts.parm("usept1").set(1)
    pts.parmTuple("pt1").set((5, 0, 0))
    ctp = geo.createNode("copytopoints::2.0")
    ctp.setInput(0, base); ctp.setInput(1, pts)
    cases["Copy to Points"] = (ctp, None)

    pk = geo.createNode("pack"); pk.setInput(0, base)
    cases["Pack"] = (pk, None)

    cl = geo.createNode("clean"); cl.setInput(0, base)
    cases["Clean (defaults)"] = (cl, set())

    fb = geo.createNode("block_begin", "foreach_begin")
    fe = geo.createNode("block_end", "foreach_end")
    fb.setInput(0, base)
    fb.parm("method").set(1)  # piece
    fb.parm("blockpath").set("../foreach_end")
    fe.setInput(0, fb)
    fe.parm("itermethod").set(1)  # pieces
    fe.parm("method").set(1)  # merge
    fe.parm("useattrib").set(0)
    fe.parm("blockpath").set("../foreach_begin")
    fe.parm("templatepath").set("../foreach_begin")
    cases["For-Each piece (empty body)"] = (fe, None)

    cb = geo.createNode("compile_begin", "compile_begin")
    ce = geo.createNode("compile_end", "compile_end")
    cb.setInput(0, base)
    cb.parm("blockpath").set("../compile_end")
    ce.setInput(0, wrangle(geo, cb, "f@w = 1;", name="compiled_w"))
    cases["Compile block (writes @w)"] = (ce, {("point", "w")})

    return base, cases


def diff(before, after, touched):
    b, b_topo = before
    a, a_topo = after
    born = sorted(k for k in a if k not in b)
    deleted = sorted(k for k in b if k not in a)
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    false = [] if touched is None else [k for k in changed if k not in touched]
    return born, deleted, changed, false, b_topo != a_topo


def fmt(keys):
    return ", ".join(f"{c}:{n}" for c, n in keys) or "-"


def main():
    geo = hou.node("/obj").createNode("geo")
    base, cases = build(geo)
    before = snapshot(base)

    print("## S1: one data ID per class on the base geometry\n")
    for k, v in sorted(before[0].items()):
        print(f"- {k[0]}:{k[1]} -> {v}")
    s1 = {k[0] for k in before[0]} >= set(CLASSES)
    print(f"\nAll four attribute classes readable: {s1}")
    print(f"Two reads equal: {snapshot(base) == before}\n")

    print("## S2: per node, compared with its first input (base)\n")
    print("| Node | Topology ID changed | Born | Deleted | ID changed | False 'Written' |")
    print("|---|---|---|---|---|---|")
    for name, (node, touched) in cases.items():
        errs = node.errors()
        if errs:
            print(f"| {name} | ERROR: {errs[0]} | | | | |")
            continue
        born, deleted, changed, false, topo = diff(before, snapshot(node), touched)
        flag = "n/a (topology/merge)" if touched is None else fmt(false)
        print(f"| {name} | {topo} | {fmt(born)} | {fmt(deleted)} | {fmt(changed)} | {flag} |")


main()
