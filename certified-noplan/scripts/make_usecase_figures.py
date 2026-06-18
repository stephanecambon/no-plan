"""S9b — one C-space figure per use-case scene (the "VOIR le cas" deliverable, A20/A25).

Each figure is a 2-D cut over (base yaw s0, shoulder pitch s1): collision in grey, the slab
{|phi|<=delta} in gold, start (★) / goal (✚) marked, and a DASHED escape-attempt path that
detours over the top yet still plunges into the slab wall (A20: shows why one would believe a
path exists). Footer = explicit joint limits in degrees (A25). These are PLAUSIBILITY views,
not certificates: the disconnection is PROVEN later by `cnp certify` + `cnp verify` (S10/S11).

Run: ``python scripts/make_usecase_figures.py`` -> benchmarks/figures/S9b_usecases/*.png
"""
from __future__ import annotations

import os

from cnp import scenes, viz

OUT = os.path.join("benchmarks", "figures", "S9b_usecases")

CASES = [
    ("usecase_binpicking",     "bin-picking logistique (6-DOF) — colis au fond du bac inatteignable"),
    ("usecase_etagere_pharma", "étagère pharma (7-DOF, FLAGSHIP) — casier haut inatteignable"),
    ("usecase_capot_surete",   "capot de sûreté (7-DOF) — zone opérateur inatteignable"),
]

# escape attempt (A20): start -> detour high over the top -> goal; it crosses the slab band
# at every shoulder pitch, so it plunges into the collision wall whatever the detour.
ESCAPE = [(-0.6, 0.0), (-0.45, 0.6), (-0.2, 0.68), (0.0, 0.68), (0.2, 0.68), (0.45, 0.6), (0.6, 0.0)]


def main():
    os.makedirs(OUT, exist_ok=True)
    for stem, title in CASES:
        sc, _ = scenes.load(os.path.join("scenes", f"{stem}.yaml"))
        oracle = scenes.collision_oracle(sc, n_samples=60)
        path = os.path.join(OUT, f"{stem}_cspace.png")
        viz.save_cspace_figure(
            sc, oracle, path, axes=(0, 1), n=150,
            title=title + "\n[plausibilité — preuve : cnp verify, S10/S11]",
            axis_labels=("lacet base  s0  (q0 = 2·arctan s0)", "tangage épaule  s1"),
            paths=[("tentative d'évasion (détour par le haut)", ESCAPE)],
            footer=viz.limits_caption(sc),
        )
        print("wrote", path)


if __name__ == "__main__":
    main()
