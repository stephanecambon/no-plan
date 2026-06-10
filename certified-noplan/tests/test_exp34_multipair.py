"""E3 (multi-pair certified disconnection) + E4 (learned barrier) regression, plus
the mandatory negative control (soundness). References: docs/CAMPAGNE-E1-E4-
RESULTATS.md and the live sandbox run.

  E3: certified=True, 46 leaves (38 collision: UP 12 / DOWN 12 / MID 14, 8 outside,
      0 fail). The three pairs relay along the slab.
  Negative control (obstacles shrunk 30% => false premise): certifier REFUSES.
  E4: certified=True, 78 leaves (76 collision).
"""
import numpy as np

from regref import certify_slab, in_collision, teval


def _counts(leaves):
    col = sum(1 for l in leaves if l[1] == "collision")
    out = sum(1 for l in leaves if l[1] == "outside")
    used = {}
    for l in leaves:
        if l[1] == "collision":
            used[l[2]] = used.get(l[2], 0) + 1
    return col, out, used


def test_e3_condition_i_holds(e3_scene):
    """Theorem condition (i): phi(start) <= -delta, phi(goal) >= +delta; endpoints free."""
    phi, delta = e3_scene["phi"], e3_scene["delta"]
    start, goal, boxes = e3_scene["start"], e3_scene["goal"], e3_scene["boxes"]
    s_start = [np.tan(start[0] / 2), np.tan(start[1] / 2)]
    s_goal = [np.tan(goal[0] / 2), np.tan(goal[1] / 2)]
    assert teval(phi, s_start) <= -delta
    assert teval(phi, s_goal) >= delta
    assert not in_collision(*start, boxes)
    assert not in_collision(*goal, boxes)


def test_e3_certifies_disconnection(e3_scene):
    ok, leaves, failed = certify_slab(
        e3_scene["phi"], e3_scene["delta"], e3_scene["boxes"], e3_scene["names"])
    assert ok is True
    assert len(failed) == 0
    assert len(leaves) == 46
    col, out, used = _counts(leaves)
    assert (col, out) == (38, 8)
    assert used == {"UP": 12, "DOWN": 12, "MID": 14}


def test_e3_negative_control_refuses(e3_negative_scene):
    """Soundness: with a false premise the certifier must NOT certify (CLAUDE.md
    rule 1). Shrinking the obstacles opens free samples inside the slab."""
    ok, leaves, failed = certify_slab(
        e3_negative_scene["phi"], e3_negative_scene["delta"],
        e3_negative_scene["boxes"], e3_negative_scene["names"])
    assert ok is False
    assert len(failed) > 0


def test_e4_learned_barrier_certifies(e4_scene):
    ok, leaves, failed = certify_slab(
        e4_scene["phi"], e4_scene["delta"], e4_scene["boxes"], e4_scene["names"])
    assert ok is True
    assert len(failed) == 0
    assert len(leaves) == 78
    col, _out, _used = _counts(leaves)
    assert col == 76
