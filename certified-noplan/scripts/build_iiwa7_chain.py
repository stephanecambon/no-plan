"""S10-bis Tâche 1 — build the RATIONALIZED exact KUKA iiwa7 chain in verify.py's form.

The Drake iiwa7 SDF FK at q*=0 is rational up to the SDF's own ~3.67e-6 rad quaternion rounding
(joints 2 & 6 axes ~[−2.65e-6, 3.67e-6, 1]; inter-link rotations deviate 3.67e-6 from a signed
permutation). Per the ratified Option A (Stéphane 18/06) we SNAP to exact coordinate axes /
signed-permutation rotations and rationalize translations: a model FAITHFUL to the published iiwa7
within ~4e-6 rad, INTERNALLY exact and verify-exact (same rationalization doctrine as φ/obstacles
and A21, applied to the kinematics).

Composition (Tâche 1, per-joint parity exact): each joint i is X_PF_i · Rot(z,θ_i) · X_ML_i (the
joint sub-frames, z the joint axis in frame F). Folding the constants between variable rotations:
FK = G_0 · Rot(z,θ_1) · G_1 · Rot(z,θ_2) · … · Rot(z,θ_7) · G_7, with G_0 = X_W_L0·X_PF_1,
G_i = X_ML_i·X_PF_{i+1}, G_7 = X_ML_7 — each a rational translation + signed-permutation rotation
(snapped). The variable axis is z (a rational coordinate axis); each fixed G rotation decomposes
into elementary 90°/180° coordinate rotations carried as LOCKED joints (S9c, cos/sin ∈ {0,±1}).
⟹ chain = {offset, axis, optional locked cos/sin}, all rational, verify.py UNTOUCHED.

Run (needs Drake + cached iiwa7 SDF): ``python scripts/build_iiwa7_chain.py`` →
writes scripts/iiwa7_chain.json (frozen chain) and prints the Drake parity (~3.67e-6, faithful).
"""
from __future__ import annotations

import json
import os
from fractions import Fraction as F

import numpy as np

OUT = os.path.join(os.path.dirname(__file__), "iiwa7_chain.json")
SDF = "package://drake_models/iiwa_description/sdf/iiwa7_no_collision.sdf"


def _Rint(ax, k):  # k quarter-turns about coordinate axis ax (0=x,1=y,2=z), exact int matrix
    u, v = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[ax]
    M = np.eye(3, dtype=int)
    for _ in range(k % 4):
        N = np.eye(3, dtype=int)
        N[u, u] = 0; N[u, v] = -1; N[v, u] = 1; N[v, v] = 0
        M = M @ N
    return M


_GENS = [(ax, k) for ax in (0, 1, 2) for k in (1, 2, 3)]
_AXVEC = {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)}
_CS = {1: (0, 1), 2: (-1, 0), 3: (0, -1)}            # (cos, sin) of k quarter-turns


def _decompose(Rsnap):
    """Signed-perm rotation (int 3x3) -> [(axisvec, cos, sin)] whose LEFT-TO-RIGHT product == R."""
    R = np.rint(Rsnap).astype(int)
    if np.array_equal(R, np.eye(3, dtype=int)):
        return []
    frontier = [((), np.eye(3, dtype=int))]
    for _ in range(3):
        nxt = []
        for facs, M in frontier:
            for ax, k in _GENS:
                M2 = M @ _Rint(ax, k)                # APPEND on the right: product order
                nf = facs + ((_AXVEC[ax], *_CS[k]),)
                if np.array_equal(M2, R):
                    return list(nf)
                nxt.append((nf, M2))
        frontier = nxt
    raise RuntimeError("no <=3 coordinate-rotation decomposition")


def _frac3(v):
    return [str(F(float(x)).limit_denominator(10 ** 6)) for x in v]


def _extract():
    from pydrake.multibody.parsing import Parser
    from pydrake.multibody.plant import MultibodyPlant
    from pydrake.multibody.tree import JointIndex, RevoluteJoint
    plant = MultibodyPlant(0.0)
    Parser(plant).AddModels(url=SDF)
    plant.WeldFrames(plant.world_frame(), plant.GetFrameByName("iiwa_link_0"))
    plant.Finalize()
    ctx = plant.CreateDefaultContext()
    plant.SetPositions(ctx, np.zeros(7))
    rev = [plant.get_joint(JointIndex(j)) for j in range(plant.num_joints())]
    rev = [j for j in rev if isinstance(j, RevoluteJoint)]

    def Xwb(b):
        return plant.EvalBodyPoseInWorld(ctx, b).GetAsMatrix4()

    def Xwf(f):
        return f.CalcPoseInWorld(ctx).GetAsMatrix4()

    XPF = [np.linalg.inv(Xwb(j.parent_body())) @ Xwf(j.frame_on_parent()) for j in rev]
    XML = [np.linalg.inv(Xwf(j.frame_on_child())) @ Xwb(j.child_body()) for j in rev]
    XWL0 = Xwb(rev[0].parent_body())
    bodies = [rev[0].parent_body()] + [j.child_body() for j in rev]
    return XWL0, XPF, XML, plant, ctx, bodies, Xwb


def _snap(X):
    """4x4 with rotation snapped to nearest integer signed-perm; assert within SDF tolerance."""
    R = X[:3, :3]
    Rs = np.rint(R)
    assert abs(R - Rs).max() < 5e-6, abs(R - Rs).max()
    assert np.allclose(Rs @ Rs.T, np.eye(3)) and round(np.linalg.det(Rs)) == 1
    Y = np.eye(4); Y[:3, :3] = Rs; Y[:3, 3] = X[:3, 3]
    return Y


def build():
    XWL0, XPF, XML, plant, ctx, bodies, Xwb = _extract()
    G = [_snap(XWL0 @ XPF[0])] + [_snap(XML[i] @ XPF[i + 1]) for i in range(6)] + [_snap(XML[6])]

    joints, locked = [], {}

    def add(offset, axis, name, cs=None):
        if cs is not None:
            locked[len(joints)] = {"cos": str(cs[0]), "sin": str(cs[1])}
        joints.append({"offset": _frac3(offset), "axis": [str(int(a)) for a in axis], "name": name})

    def add_fixed(X, tag):
        t = X[:3, 3]
        fac = _decompose(X[:3, :3])
        if not fac:
            add(t, (0, 0, 1), tag + "_t", cs=(1, 0))
        else:
            for k, (axv, c, s) in enumerate(fac):
                add(t if k == 0 else (0, 0, 0), axv, f"{tag}_{k}", cs=(c, s))

    add_fixed(G[0], "G0")
    link_after = {}
    for i in range(7):
        add((0, 0, 0), (0, 0, 1), f"q{i+1}")            # variable joint i+1, axis z
        link_after[i + 1] = len(joints) - 1
        add_fixed(G[i + 1], f"G{i+1}")
    joints[-1]["name"] = "L7end"

    chain = {"note": "iiwa7 rationalized (faithful to Drake SDF ~4e-6 rad, internally exact), verify.py form",
             "joints": joints, "locked": {str(k): v for k, v in locked.items()},
             "variable_indices": [p for p in range(len(joints)) if p not in locked],
             "link_after_joint": {str(k): v for k, v in link_after.items()}}
    with open(OUT, "w") as f:
        json.dump(chain, f, indent=2)

    err = _parity(chain, plant, ctx, bodies, Xwb)
    print(f"chain: {len(joints)} entries, {len(chain['variable_indices'])} variable (attendu 7), "
          f"{len(locked)} locked")
    print(f"Drake parity (max pos error / 1500 configs): {err:.2e}  "
          f"(fidèle au SDF ~3.67e-6 ; modèle interne EXACT)")
    print(f"frozen chain -> {OUT}")
    return err


def check_parity():
    """Load the frozen chain + Drake and return the max FK position error (test entry-point)."""
    with open(OUT) as f:
        chain = json.load(f)
    _, _, _, plant, ctx, bodies, Xwb = _extract()
    return _parity(chain, plant, ctx, bodies, Xwb)


def _parity(chain, plant, ctx, bodies, Xwb):
    from cnp.ratfk import SympyRatFK, RevoluteJoint

    def Tr(o):
        M = np.eye(4); M[:3, 3] = [float(F(x)) for x in o]; return M

    rj = [RevoluteJoint(name=j["name"], X_pj=Tr(j["offset"]),
                        axis=np.array([float(x) for x in j["axis"]])) for j in chain["joints"]]
    lk = {int(k): float(np.arctan2(int(v["sin"]), int(v["cos"])))
          for k, v in chain["locked"].items()}
    fk = SympyRatFK(rj, locked=lk)
    var = chain["variable_indices"]
    rng = np.random.default_rng(7)
    err = 0.0
    for _ in range(1500):
        qi = rng.uniform(-2.9, 2.9, 7)
        qf = np.zeros(len(rj))
        for p, q in zip(var, qi):
            qf[p] = q
        W = fk.body("L7end").eval_world_point([0, 0, 0], fk.s_value(qf))
        plant.SetPositions(ctx, qi)
        err = max(err, float(np.linalg.norm(W - Xwb(bodies[7])[:3, 3])))
    return err


if __name__ == "__main__":
    build()
