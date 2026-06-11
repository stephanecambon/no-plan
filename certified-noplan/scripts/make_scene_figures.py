"""make_scene_figures — top-down 2-D scene figures for design inspection (S6, V3).

Generates ``benchmarks/figures/scene_S2_peigne.png``: the planar 3-DOF comb with the
free start/goal poses AND two in-slab poses (s0=0) showing the middle link caught in
the comb — the story the certificate proves. A planar scene reads far better top-down
than in 3-D Meshcat; ``cnp show <scene> --png`` produces the plain start/goal view.

Run: ``python scripts/make_scene_figures.py`` (or ``make figures``).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cnp import scenes, viz                     # noqa: E402

HERE = os.path.dirname(__file__)
SCENES = os.path.join(HERE, "..", "scenes")
OUT = os.path.join(HERE, "..", "benchmarks", "figures")


def peigne_figures():
    scene, _ = scenes.load(os.path.join(SCENES, "S2_peigne.yaml"))
    os.makedirs(OUT, exist_ok=True)

    # (a) Workspace view: WHY any crossing is blocked (the middle link enters the comb).
    poses = [
        ("start (libre, bras vers le bas)", scene.start_s, "#1f77b4"),
        ("dalle s0=0, s1=0  -> link median pris dans MID", [0.0, 0.0, 0.0], "#d62728"),
        ("dalle s0=0, s1=+0.7 -> pris dans UP (relais)", [0.0, 0.7, 0.0], "#ff7f0e"),
        ("goal (libre, bras vers le haut)", scene.goal_s, "#2ca02c"),
    ]
    p1 = os.path.join(OUT, "scene_S2_peigne.png")
    viz.save_planar_figure(
        scene, p1, poses=poses,
        title="S2 peigne 3-DOF (workspace) : start/goal libres ; toute traversee "
              "(s0=0) prend le link median dans le peigne")
    print("written", os.path.normpath(p1))

    # (b) C-space view: THAT goal is free but UNREACHABLE — a solid collision wall at
    # s0~=0 spanning the box separates start (left) from goal (right). s2 is passive,
    # so the (s0,s1) slice at s2=0 represents every s2.
    oracle = scenes.planar_collision_oracle(scene, n_samples=25)
    p2 = os.path.join(OUT, "scene_S2_peigne_cspace.png")
    viz.save_cspace_figure(
        scene, oracle, p2, axes=(0, 1), n=140, fixed={2: 0.0},
        title="S2 peigne (C-space s0,s1 ; s2 passif) : mur de collision a s0=0 "
              "-> goal libre mais INATTEIGNABLE depuis start")
    print("written", os.path.normpath(p2))


def spatial_figure():
    """Spatial 3R scene (S2b): the same 'goal free but unreachable' story with a
    GENUINE 3-D robot (orbit it with `cnp show scenes/S2b_spatial3.yaml`). The C-space
    (s0,s1) slice shows the collision wall at s0~=0 separating start from goal."""
    scene, _ = scenes.load(os.path.join(SCENES, "S2b_spatial3.yaml"))
    os.makedirs(OUT, exist_ok=True)
    oracle = scenes.collision_oracle(scene, n_samples=30)
    p1 = os.path.join(OUT, "scene_S2b_spatial_cspace.png")
    # The robot is a REVOLUTE chain (hinges), not a ball joint: s0 = base yaw (turns
    # left/right, in-plane), s1 = pitch ("lifts the arm"). The wall covers ALL s1, so
    # neither the direct crossing nor a "lift then cross" detour escapes the collision.
    paths = [("passage direct (lacet seul)", [(-0.6, 0), (0.6, 0)]),
             ("tentative: relever (tangage) puis traverser",
              [(-0.6, 0), (-0.6, 0.65), (0.6, 0.65), (0.6, 0)])]
    viz.save_cspace_figure(
        scene, oracle, p1, axes=(0, 1), n=160, fixed={2: 0.0}, paths=paths,
        axis_labels=("s0 = lacet base (tourne G/D)", "s1 = tangage (releve le bras)"),
        title="S2b 3R (joints rotoides, PAS rotule) : le mur couvre tout le tangage "
              "s1\n-> ni le passage direct ni la tentative de relever ne sortent du libre")
    print("written", os.path.normpath(p1))

    # Sweep filmstrip: the direct start->goal motion sweeps the arm through the wall.
    p2 = os.path.join(OUT, "scene_S2b_spatial_sweep.png")
    viz.save_sweep_figure(
        scene, oracle, p2, n=11, project=(0, 1),
        title="S2b : balayage start->goal (la base tourne) — les poses du milieu "
              "(rouge) plantent dans le mur : le mouvement direct est bloque")
    print("written", os.path.normpath(p2))


def shoulder_elbow_figures():
    """S3 — 4-DOF shoulder-elbow arm (Li-Dantam anchor, V4). Two figures:
      (a) a top-down filmstrip of the FULL arm (upper arm + forearm) sweeping base yaw
          start->goal, the middle poses (red) ramming the shelf panel — 'reachable in
          appearance, proven unreachable' (A20);
      (b) the C-space (yaw s0, pitch s1) slice with the collision WALL spanning every
          pitch and the gold slab inside it — goal free but UNREACHABLE.
    The arm is drawn in full so it reads as the shoulder-elbow robot of Li-Dantam RSS
    2021 Fig. 7b; collision colour is the UPPER-ARM body (the link the certificate traps)."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    scene, _ = scenes.load(os.path.join(SCENES, "S3_shoulder_elbow.yaml"))
    os.makedirs(OUT, exist_ok=True)
    oracle = scenes.collision_oracle(scene, n_samples=30)
    fk, _names, _bn, _tip = viz._fk_and_names(scene)
    L_UP, L_FORE = 0.40, 0.30

    def full_arm(s):
        """base -> elbow -> hand (upper arm length L_UP, forearm L_FORE)."""
        elbow = fk.body("j2").eval_world_point([L_UP, 0, 0], s)
        hand = fk.body("j3").eval_world_point([L_FORE, 0, 0], s)
        return np.array([[0, 0, 0], elbow, hand])

    # (a) full-arm sweep, top-down (world x,y)
    st = np.array([float(v) for v in scene.start_s])
    go = np.array([float(v) for v in scene.goal_s])
    fig, ax = plt.subplots(figsize=(7.5, 7))
    (xlo, xhi), (ylo, yhi), _ = viz._box_bounds(*scene.obstacles["PANEL"])
    ax.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo, facecolor="0.55",
                           edgecolor="0.3", alpha=0.85, zorder=1))
    ax.text((xlo + xhi) / 2, yhi + 0.02, "panneau / etagere", ha="center",
            fontsize=8, weight="bold")
    n = 9
    n_coll = 0
    for k in range(n):
        s = st + (go - st) * (k / (n - 1))
        colliding = oracle(s)
        n_coll += colliding
        colour = "#d62728" if colliding else "#2ca02c"
        pts = full_arm(s)
        ax.plot(pts[:, 0], pts[:, 1], "-", color=colour, lw=2.4, alpha=0.85, zorder=3)
        ax.plot(pts[:, 0], pts[:, 1], "o", color=colour, ms=4, zorder=4)
    ax.plot(0, 0, "ks", ms=10, zorder=7)
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.5)
    ax.set_xlabel("x monde (m)")
    ax.set_ylabel("y monde (m)")
    ax.set_title(f"S3 epaule-coude 4-DOF : balayage du lacet base ({n_coll}/{n} poses "
                 "en collision)\nstart/goal libres, le panneau bloque le bras median")
    p1 = os.path.join(OUT, "scene_S3_shoulder_elbow_sweep.png")
    fig.tight_layout()
    fig.savefig(p1, dpi=130)
    plt.close(fig)
    print("written", os.path.normpath(p1))

    # (a') SIDE view (world x-z) + pitch-plane fan: answers "why not go OVER the panel?".
    # At yaw 0 (in the slab) the upper arm is swept over its whole pitch range; every pose
    # (red) rams the panel. The panel TOP (z=0.6) is higher than the arm's entire reach
    # (the radius-0.4 dashed envelope), so no configuration ever gets above it — the block
    # is the WALL HEIGHT, not the pitch joint limit (even at max pitch the arm crosses the
    # panel low). This is the natural-objection answer the V4 review (A23) requires.
    fig, ax = plt.subplots(figsize=(7.5, 7))
    (pxlo, pxhi), _, (pzlo, pzhi) = viz._box_bounds(*scene.obstacles["PANEL"])
    ax.add_patch(Rectangle((pxlo, pzlo), pxhi - pxlo, pzhi - pzlo, facecolor="0.55",
                           edgecolor="0.3", alpha=0.85, zorder=2))
    ax.text((pxlo + pxhi) / 2, pzhi + 0.03, f"panneau (sommet z={pzhi:g})",
            ha="center", fontsize=9, weight="bold")
    reach = L_UP
    th = np.linspace(-np.pi / 2, np.pi / 2, 100)
    ax.plot(reach * np.cos(th), reach * np.sin(th), "--", color="0.4", lw=1.2,
            zorder=1, label=f"portee max du bras sup. (r={reach:g})")
    ax.axhline(reach, ls=":", color="#7f0000", lw=1.0, zorder=1)
    s1lo, s1hi = float(scene.box[1][0]), float(scene.box[1][1])
    n_coll = 0
    for s1 in np.linspace(s1lo, s1hi, 9):
        s = np.array([0.0, s1, 0.0, 0.0])             # yaw 0 (in slab), vary pitch
        colliding = oracle(s)
        n_coll += colliding
        colour = "#d62728" if colliding else "#2ca02c"
        # draw ONLY the UPPER ARM (base->elbow) — the certified body and the link the
        # height argument is about; its tip never leaves the radius-0.4 envelope.
        elbow = fk.body("j2").eval_world_point([L_UP, 0, 0], s)
        pts = np.array([[0, 0, 0], elbow])
        ax.plot(pts[:, 0], pts[:, 2], "-", color=colour, lw=2.6, alpha=0.9, zorder=3)
        ax.plot(pts[1, 0], pts[1, 2], "o", color=colour, ms=4, zorder=4)
    ax.plot(0, 0, "ks", ms=10, zorder=7)
    ax.set_aspect("equal")
    ax.set_ylim(pzlo - 0.08, pzhi + 0.18)
    ax.grid(True, ls=":", alpha=0.5)
    ax.set_xlabel("x monde (m) — profondeur")
    ax.set_ylabel("z monde (m) — hauteur")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.95)
    ax.set_title("S3 vue de COTE (plan du tangage, lacet=0) — bras superieur sur tout "
                 f"son tangage : {n_coll}/9 poses en collision\n"
                 "sommet panneau 0.6 > portee du bras 0.4  =>  passer PAR-DESSUS est "
                 "IMPOSSIBLE (raison = HAUTEUR DU MUR,\npas la limite articulaire : meme "
                 "au tangage max le bras plante bas dans le panneau)", fontsize=10)
    p3 = os.path.join(OUT, "scene_S3_shoulder_elbow_side.png")
    fig.tight_layout()
    fig.savefig(p3, dpi=130)
    plt.close(fig)
    print("written", os.path.normpath(p3))

    # (b) C-space wall (yaw s0, pitch s1); s2 roll + s3 elbow are passive for the body.
    p2 = os.path.join(OUT, "scene_S3_shoulder_elbow_cspace.png")
    viz.save_cspace_figure(
        scene, oracle, p2, axes=(0, 1), n=140, fixed={2: 0.0, 3: 0.0},
        axis_labels=("s0 = lacet base (tourne G/D)", "s1 = tangage epaule (releve)"),
        title="S3 epaule-coude (C-space lacet s0 / tangage s1 ; roll+coude passifs) :\n"
              "mur de collision couvrant tout le tangage -> goal libre mais INATTEIGNABLE")
    print("written", os.path.normpath(p2))


if __name__ == "__main__":
    peigne_figures()
    spatial_figure()
    shoulder_elbow_figures()
