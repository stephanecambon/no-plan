"""S10-ter Tâche 2 — faithful convex body (level 1) for the REAL iiwa7 flagship scene.

Derives the certified body of the flagship from the Drake VISUAL mesh of a proximal iiwa7
link (level-1 fidelity = ONE convex hull per body; multi-piece decomposition = level 2, out
of scope), expressed in the FROZEN chain's body frame and RATIONALIZED (limit_denominator 1e6)
so verify.py re-counts it exactly.

Body link choice: chain index 7 = the variable joint ``q3``. Drake link 3's frame is rigidly
related to the chain frame after ``q3`` by the constant ``X_ML_3`` (the folded chain hides Drake
link frames as intermediate frames — the G_i mix X_ML_i with X_PF_{i+1}), so the body hull,
expressed in the chain frame via the q*=0 poses, tracks the real link 3 for ALL q. Because the
body frame is set by joints up to q3, only the variable joints {q1,q2,q3} (s-indices {0,1,2}) can
move it — the 4 distal joints are geometrically downstream and CANNOT move the proximal body
(the "robust to redundancy" thesis, automatic for a proximal link). Active dims are RE-MEASURED
downstream via engine.pair_views (NOT presumed {0,1,2}; A30) once the scene exists.

The K-vertex silhouette: support points of the link hull along ~K spread directions (each a true
hull vertex), convex-hulled and rationalized — a faithful convex silhouette of the rounded link.

Run (needs Drake + cached iiwa7 visual mesh):
    python scripts/build_iiwa7_scene.py            # diagnostics: hull, parity, link-3 sweep
"""
from __future__ import annotations

import json
import os
from fractions import Fraction as F

import numpy as np

HERE = os.path.dirname(__file__)
CHAIN = os.path.join(HERE, "iiwa7_chain.json")
SDF = "package://drake_models/iiwa_description/sdf/iiwa7_no_collision.sdf"
BODY_JOINT = "q3"          # chain frame after q3 == rigid offset of Drake link 3
DRAKE_LINK = "iiwa_link_3"
K_DIRS = 40                # support directions; dedup yields the K-vertex silhouette
BODY_OUT = os.path.join(HERE, "iiwa7_body_link3.json")


def _plant():
    """iiwa7 plant welded to world, with SceneGraph (for the visual hull) + a context."""
    from pydrake.multibody.parsing import Parser
    from pydrake.multibody.plant import MultibodyPlant
    from pydrake.geometry import SceneGraph
    from pydrake.systems.framework import DiagramBuilder
    builder = DiagramBuilder()
    plant = MultibodyPlant(0.0)
    sg = builder.AddSystem(SceneGraph())
    plant.RegisterAsSourceForSceneGraph(sg)
    Parser(plant).AddModels(url=SDF)
    plant.WeldFrames(plant.world_frame(), plant.GetFrameByName("iiwa_link_0"))
    plant.Finalize()
    ctx = plant.CreateDefaultContext()
    return plant, sg, ctx


def _chain_fk():
    from cnp.ratfk import SympyRatFK, RevoluteJoint
    chain = json.load(open(CHAIN))

    def Tr(o):
        M = np.eye(4); M[:3, 3] = [float(F(x)) for x in o]; return M

    rj = [RevoluteJoint(name=j["name"], X_pj=Tr(j["offset"]),
                        axis=np.array([float(x) for x in j["axis"]])) for j in chain["joints"]]
    lk = {int(k): float(np.arctan2(int(v["sin"]), int(v["cos"])))
          for k, v in chain["locked"].items()}
    fk = SympyRatFK(rj, locked=lk)
    return fk, chain


def _link_hull_vertices(plant, sg):
    """The 1301-vertex Drake convex hull of iiwa_link_3's visual mesh, in the link frame
    (Drake convention; the mesh geom pose in the link frame is identity)."""
    insp = sg.model_inspector()
    for gid in insp.GetAllGeometryIds():
        fid = insp.GetFrameId(gid)
        if insp.GetName(fid).endswith(DRAKE_LINK):
            hull = insp.GetShape(gid).GetConvexHull()
            return np.array([hull.vertex(i) for i in range(hull.num_vertices())])
    raise RuntimeError(f"no visual geometry for {DRAKE_LINK}")


def _support_silhouette(verts, n_dirs):
    """K-vertex silhouette: argmax support point along n_dirs spread directions (Fibonacci
    sphere), deduplicated. Each is a true hull vertex ⇒ their hull is a faithful inner
    convex silhouette of the rounded link with a controlled vertex count."""
    i = np.arange(n_dirs) + 0.5
    phi = np.arccos(1 - 2 * i / n_dirs)
    theta = np.pi * (1 + 5 ** 0.5) * i
    dirs = np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]
    keep = sorted({int(np.argmax(verts @ d)) for d in dirs})
    return verts[keep]


def _Xchain0(fk):
    """4x4 pose of the chain body frame (after q3) at q*=0, from eval_world_point."""
    z = fk.s_value(np.zeros(19))
    o = fk.body(BODY_JOINT).eval_world_point([0, 0, 0], z)
    cols = [fk.body(BODY_JOINT).eval_world_point(e, z) - o
            for e in ([1, 0, 0], [0, 1, 0], [0, 0, 1])]
    X = np.eye(4); X[:3, 0], X[:3, 1], X[:3, 2] = cols; X[:3, 3] = o
    return X


def build():
    plant, sg, ctx = _plant()
    fk, chain = _chain_fk()
    var = chain["variable_indices"]

    Xdrake0 = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(DRAKE_LINK)).GetAsMatrix4()
    Xchain0 = _Xchain0(fk)
    C = np.linalg.inv(Xchain0) @ Xdrake0          # link-frame -> chain-body-frame (constant)

    hull_link = _support_silhouette(_link_hull_vertices(plant, sg), K_DIRS)
    hull_body = (C[:3, :3] @ hull_link.T).T + C[:3, 3]   # body-frame, float

    # rationalize (limit_denominator 1e6) — verify recounts in Fraction
    hull_rat = [[F(float(x)).limit_denominator(10 ** 6) for x in v] for v in hull_body]

    # parity on the BODY: chain FK of the rationalized hull vertex vs Drake link-3 world point
    def s_of(qi):
        qf = np.zeros(len(chain["joints"]))
        for p, q in zip(var, qi):
            qf[p] = q
        return fk.s_value(qf)

    rng = np.random.default_rng(11)
    err = 0.0
    for _ in range(400):
        qi = rng.uniform(-2.0, 2.0, 7)
        plant.SetPositions(ctx, qi)
        Xd = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(DRAKE_LINK)).GetAsMatrix4()
        s = s_of(qi)
        for vlink, vrat in zip(hull_link, hull_rat):
            w_chain = fk.body(BODY_JOINT).eval_world_point([float(x) for x in vrat], s)
            w_drake = (Xd[:3, :3] @ vlink) + Xd[:3, 3]
            err = max(err, float(np.linalg.norm(w_chain - w_drake)))

    print(f"K-vertex silhouette: {len(hull_rat)} vertices (from {K_DIRS} support dirs)")
    hb = np.array(hull_body)
    print(f"body-frame bbox  min {hb.min(0).round(4)}  max {hb.max(0).round(4)}")
    print(f"BODY parity (rationalized hull vs Drake link3 world / 400 cfg x {len(hull_rat)} v): "
          f"{err:.2e}  (attendu ~2e-6, plancher SDF)")

    # link-3 world sweep over the active box (q1,q2,q3 in +-70deg), distal=0 — informs the panel
    print("\nlink-3 world AABB swept over active box q1,q2,q3 in +-70deg (q4..q7=0):")
    lo = np.full(3, np.inf); hi = -lo
    g = np.linspace(-70 * np.pi / 180, 70 * np.pi / 180, 7)
    for a in g:
        for b in g:
            for c in g:
                plant.SetPositions(ctx, np.array([a, b, c, 0, 0, 0, 0]))
                Xd = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(DRAKE_LINK)).GetAsMatrix4()
                W = (Xd[:3, :3] @ hull_link.T).T + Xd[:3, 3]
                lo = np.minimum(lo, W.min(0)); hi = np.maximum(hi, W.max(0))
    print(f"  swept world bbox  min {lo.round(4)}  max {hi.round(4)}")
    return hull_rat, err


def freeze_body():
    """Write the frozen, rationalized faithful convex body (verify.py form) to JSON, the
    S10-ter deliverable (mirrors scripts/iiwa7_chain.json). Includes the measured Drake
    body parity and the RE-MEASURED active dims, so the artifact carries its own evidence."""
    hull_rat, err = build()
    box = [["-7/10", "7/10"], ["-1/4", "1/4"], ["-1/4", "1/4"],
           ["-3", "3"], ["-3", "3"], ["-3", "3"], ["-3", "3"]]
    panel_b = ["1/2", "3/20", "9/10", "-1/20", "1/20", "-7/20"]   # provisional, S10-quater
    _, views, glob, passive = measure_active(
        emit_scene(hull_rat, panel_b, box, ["-3/5"] + ["0"] * 6, ["3/5"] + ["0"] * 6))
    out = {"note": "iiwa7 link 3 faithful convex silhouette (level 1) — Drake visual hull, "
                   "support-sampled to K vertices, rationalized (limit_denominator 1e6), "
                   "expressed in the frozen-chain body frame after q3 (chain index 7). "
                   "verify.py form (rational vertices); body parity vs Drake ~2e-6.",
           "body_link": BODY_LINK, "drake_link": DRAKE_LINK,
           "hull_vertices": [[str(c) for c in v] for v in hull_rat],
           "k_vertices": len(hull_rat),
           "drake_body_parity": f"{err:.3e}",
           "active_dims_measured": list(glob), "passive_dims": list(passive)}
    with open(BODY_OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nfrozen body -> {BODY_OUT}  ({len(hull_rat)} vertices, active {glob})")
    return out


def check_body_parity(n_cfg=200):
    """Load the FROZEN body + Drake and return the max body-point FK error (test entry).
    Skips gracefully (caller) if Drake / the cached visual mesh is unavailable."""
    body = json.load(open(BODY_OUT))
    hull_rat = [[F(x) for x in v] for v in body["hull_vertices"]]
    plant, sg, ctx = _plant()
    fk, chain = _chain_fk()
    var = chain["variable_indices"]
    hull_link = _support_silhouette(_link_hull_vertices(plant, sg), K_DIRS)
    Xd0 = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(DRAKE_LINK)).GetAsMatrix4()
    C = np.linalg.inv(_Xchain0(fk)) @ Xd0
    # match each frozen vertex back to its Drake link-frame source (same support set/order)
    link_for = (np.linalg.inv(C[:3, :3]) @ (np.array(
        [[float(x) for x in v] for v in hull_rat]).T - C[:3, 3:4])).T
    rng = np.random.default_rng(13)
    err = 0.0
    for _ in range(n_cfg):
        qi = rng.uniform(-2.0, 2.0, 7)
        plant.SetPositions(ctx, qi)
        Xd = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(DRAKE_LINK)).GetAsMatrix4()
        qf = np.zeros(len(chain["joints"]))
        for p, q in zip(var, qi):
            qf[p] = q
        s = fk.s_value(qf)
        for vrat, vlink in zip(hull_rat, link_for):
            w_chain = fk.body(BODY_JOINT).eval_world_point([float(x) for x in vrat], s)
            err = max(err, float(np.linalg.norm(w_chain - ((Xd[:3, :3] @ vlink) + Xd[:3, 3]))))
    return err


BODY_LINK = 7              # chain index of q3 (verified: chain['variable_indices'][2])


def emit_scene(hull_rat, panel_b, box, start_s, goal_s, delta="1/10"):
    """Assemble the scene mapping on the frozen chain (robot=19 joints + 12 locked)."""
    chain = json.load(open(CHAIN))
    robot = {"kind": "spatial_revolute",
             "q_star": ["0"] * len(chain["joints"]),
             "joints": [{"offset": j["offset"], "axis": j["axis"]} for j in chain["joints"]],
             "locked": {str(k): v for k, v in chain["locked"].items()}}
    panel = {"hrep": {"A": [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"],
                            ["-1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]],
                      "b": [str(x) for x in panel_b]}}
    return {"robot": robot,
            "body": {"link": BODY_LINK,
                     "hull_vertices": [[str(c) for c in v] for v in hull_rat]},
            "obstacles": {"SHELF_PANEL": panel},
            "phi": {"degree_per_var": 2, "coeffs": {"1,0,0,0,0,0,0": "1"}},
            "delta": delta, "box": box, "start_s": start_s, "goal_s": goal_s,
            "pairs": ["SHELF_PANEL"], "budget": {"max_depth": 24, "axis": "margin"}}


SCENE_OUT = os.path.join(HERE, "..", "scenes", "S6_iiwa_real_shelf.yaml")

# Franc trap (S10-quater, A43): the proximal link 3 is a compact blob with NO base-yaw lever,
# so we separate on q2 (shoulder PITCH — big real z-lever) and trap with an OVERHEAD SHELF.
# slab {|s1|<=delta} = q2~0 = arm STRAIGHT UP = body high (top z~0.77); start/goal = q2=∓62deg =
# arm tilted, body low (top z~0.60) -> clears the shelf. Ceiling z0 in the franc window
# (0.597, 0.772): margins ~+90mm both sides (vs 6mm for base-yaw). Validated 0-free by the
# convex oracle.
_SHELF_XY = "1/2"          # finite overhead shelf half-extent in x,y (realistic, A20)
_SHELF_Z0 = "17/25"        # 0.68: ceiling underside, mid franc window
_SHELF_ZTOP = "1"
_DELTA = "1/5"


def write_scene_yaml():
    """Freeze the franc flagship scene on the frozen chain + frozen faithful body."""
    import yaml
    hull_rat = [[F(x) for x in v] for v in json.load(open(BODY_OUT))["hull_vertices"]]
    box = [["-7/10", "7/10"], ["-7/10", "7/10"], ["-7/10", "7/10"],
           ["-3", "3"], ["-3", "3"], ["-3", "3"], ["-3", "3"]]
    panel_b = [_SHELF_XY, _SHELF_XY, _SHELF_ZTOP, _SHELF_XY, _SHELF_XY,
               str(F(_SHELF_Z0) * -1)]
    data = emit_scene(hull_rat, panel_b, box,
                      ["0", "-3/5", "0", "0", "0", "0", "0"],
                      ["0", "3/5", "0", "0", "0", "0", "0"], delta=_DELTA)
    data["phi"] = {"degree_per_var": 2, "coeffs": {"0,1,0,0,0,0,0": "1"}}   # phi = s1 (q2)
    data["obstacles"]["SHELF_PANEL"] = data["obstacles"].pop("SHELF_PANEL")
    header = (
        "# S6 — FLAGSHIP d'EN-TÊTE : VRAI iiwa7 (chaîne + corps convexe fidèle GELÉS), portée 7-DOF\n"
        "# CERTIFIÉE (S10-quater, porte G4'). Cinématique fidèle à l'URDF iiwa7 ~2e-6 (S10-bis) ET\n"
        "# silhouette convexe fidèle 40 sommets, parité ~1.7e-6 (S10-ter). verify.py SACRÉ — zéro diff.\n"
        "#\n"
        "# RÉCIT. Un bras redondant 7-DOF (KUKA iiwa7) doit passer d'une pose basse (épaule pitchée d'un\n"
        "# côté) à une pose basse symétrique (pitchée de l'autre) ; une ÉTAGÈRE EN SURPLOMB barre le\n"
        "# passage par le haut. L'intuition dit « un bras à 7 axes, redondant, contournera ». Le certificat\n"
        "# prouve le contraire : pour changer le SIGNE du pitch d'épaule (q2) il faut passer par q2~0 (bras\n"
        "# DROIT, vertical), où le SEGMENT PROXIMAL (lien 3) percute l'étagère — et AUCUN des 4 joints\n"
        "# distaux ne l'en sort (ils sont en aval du lien 3, passifs). Redondance inutile = THÈSE du flagship.\n"
        "#\n"
        "# POURQUOI PITCH ET PAS LACET (A43, finding S10-ter). Le vrai lien 3 est un blob COMPACT (~0.13 m),\n"
        "# sans le levier 0.3 m du segment iiwa-LIKE : le lacet de base ne le bouge pas assez (séparation\n"
        "# marginale ~6 mm, refusée). Le pitch d'épaule q2 a un GRAND levier en z réel (top du corps 0.81\n"
        "# bras droit -> 0.55 bras incliné) ⟹ piège FRANC par étagère en surplomb (marge ~90 mm, mesurée).\n"
        "#\n"
        "# CORPS = COQUE CONVEXE FIDÈLE (niveau 1) du mesh de visu Drake du lien 3, 40 sommets rationalisés\n"
        "# (verify recompte en Fraction), frame-chaîne après q3. Dims actives RE-MESURÉES (pair_views) =\n"
        "# (0,1,2) ; distaux (3,4,5,6) passifs AUTOMATIQUEMENT. Budget (d+1)^3 = 4^3 = 64 lignes/LP.\n"
        "# Obstacle = étagère H-rep EXACTE (étanche). VÉRITÉ-TERRAIN dense (oracle CORPS-CONVEXE, A43) :\n"
        "# voir scripts/flagship_iiwa_real_groundtruth.py. Limites box ±70deg actifs / ±143deg passifs (A25).\n")
    with open(SCENE_OUT, "w") as f:
        f.write(header)
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=None, width=120)
    print(f"frozen flagship scene -> {SCENE_OUT}")
    return SCENE_OUT


def measure_active(scene_dict):
    """Re-measure the per-pair active dims via engine.pair_views (A30; NOT presumed)."""
    import yaml
    from cnp import scenes, engine
    sc, _ = scenes.parse_scene(yaml.safe_load(yaml.safe_dump(scene_dict)))
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    glob = engine._global_active(views, prob)
    passive = engine.passive_dims(prob)
    return sc, views, glob, passive


if __name__ == "__main__":
    freeze_body()             # -> scripts/iiwa7_body_link3.json (needs Drake)
    write_scene_yaml()        # -> scenes/S6_iiwa_real_shelf.yaml (from the frozen body)
