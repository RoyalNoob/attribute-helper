"""Spike S6: which node events fire for recooks and network edits, and what refresh costs.

Run: hython docs/spikes/s6_events.py
Results are summarized in docs/spikes/s6_events.md.
"""
import time

import hou

EVENTS = [getattr(hou.nodeEventType, n) for n in dir(hou.nodeEventType)
          if not n.startswith("_") and n != "thisown"]
log = []


def record(event_type, **kwargs):
    log.append((kwargs["node"].name(), event_type.name()))


def step(title, action):
    log.clear()
    action()
    fired = sorted(set(log))
    print(f"| {title} | {', '.join(f'{n}:{e}' for n, e in fired) or '-'} |")


def chain(parent, n):
    node = parent.createNode("box")
    for _ in range(n - 1):
        nxt = parent.createNode("xform")
        nxt.setInput(0, node)
        node = nxt
    return node


def main():
    geo = hou.node("/obj").createNode("geo", "net")
    box = geo.createNode("box")
    xf = geo.createNode("xform"); xf.setInput(0, box)
    tail = geo.createNode("null", "tail"); tail.setInput(0, xf)
    tail.setDisplayFlag(True)
    tail.geometry()
    for n in (geo, box, xf, tail):
        n.addEventCallback(EVENTS, record)

    print("| Action | Events (node:event) |")
    print("|---|---|")
    step("Change box size parm", lambda: box.parm("sizex").set(2))
    step("Cook tail after that change", lambda: tail.geometry())
    step("Force-cook box", lambda: box.cook(force=True))
    step("Read tail geometry after force-cook", lambda: tail.geometry())
    step("Move xform", lambda: xf.move(hou.Vector2(1, 0)))
    step("Rename xform", lambda: xf.setName("xf2"))
    step("Set display flag on xform", lambda: xf.setDisplayFlag(True))

    def insert():
        mid = geo.createNode("null", "mid")
        mid.setInput(0, box)
        xf.setInput(0, mid)
    step("Insert node between box and xform", insert)
    step("Delete inserted node", lambda: geo.node("mid").destroy())
    step("Rewire xform input to box", lambda: xf.setInput(0, box))

    print("\n## Cost of the per-refresh cache check (no geometry reads)\n")
    for n in (50, 200, 1000):
        net = hou.node("/obj").createNode("geo", f"cost{n}")
        end = chain(net, n)
        end.geometry()
        nodes = [end]
        nodes += list(end.inputAncestors())
        t = time.perf_counter()
        keys = [(x.sessionId(), x.cookCount(), x.needsToCook()) for x in nodes]
        walk = time.perf_counter() - t
        t = time.perf_counter()
        for x in nodes:
            g = x.geometry()
            for a in g.pointAttribs():
                a.dataId().vexAttribDataId()
        read = time.perf_counter() - t
        print(f"- {len(keys)} nodes: walk + cache keys {walk * 1000:.1f} ms, "
              f"full snapshot read {read * 1000:.1f} ms")


main()
