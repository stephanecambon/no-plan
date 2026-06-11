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
    path = os.path.join(OUT, "scene_S2b_spatial_cspace.png")
    viz.save_cspace_figure(
        scene, oracle, path, axes=(0, 1), n=140, fixed={2: 0.0},
        title="S2b spatial 3R (C-space s0,s1 ; s2 passif) : mur de collision a "
              "s0=0 -> goal libre mais INATTEIGNABLE depuis start")
    print("written", os.path.normpath(path))


if __name__ == "__main__":
    peigne_figures()
    spatial_figure()
