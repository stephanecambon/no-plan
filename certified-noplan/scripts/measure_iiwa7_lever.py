"""S11 — MESURE DU LEVIER PAR JOINT ACTIF sur le VRAI iiwa7 (méthode S10-quater, [A43]).

**À lancer AVANT de choisir le séparateur d'une nouvelle scène.** Le finding A43 (S10-ter) dit
qu'un corps à silhouette réelle est COMPACT : le levier du corps-segment a disparu, et le lacet
de base ne sépare plus (marge ~6 mm, refusée). Ce script ne devine pas — il MESURE, pour chaque
axe actif candidat et chaque direction de séparation, la marge FRANCHE atteignable.

MÉTRIQUE (celle qui décide). Pour un séparateur ``phi = s_i`` (dalle ``|s_i| <= delta``), une
direction unitaire ``u`` et un obstacle demi-espace ``{x·u >= c}`` :

    A(u) = min          sur la DALLE      de  max_v u·x_v(s)     (portée garantie dans la dalle)
    B(u) = max sur {start, goal}          de  max_v u·x_v(s)     (portée aux poses libres)

Le corps est en collision partout dans la dalle dès que ``c <= A(u)`` et libre aux poses dès que
``c > B(u)``. La **marge franche** est ``A(u) - B(u)`` : il existe un plan séparateur ssi elle est
positive, et on la veut **>= ~40 mm** (S10-ter a refusé 6 mm ; le flagship S6 tient ~90 mm).

Les axes PASSIFS n'entrent pas dans la mesure : le corps proximal n'en dépend pas (c'est la thèse
« robuste à la redondance ») — vérifié par ``engine.pair_views``, pas présumé.

Usage :
    python scripts/measure_iiwa7_lever.py [scene.yaml]        # défaut : le flagship S6 (témoin)
"""
from __future__ import annotations

import itertools
import sys

import numpy as np

from cnp import engine, scenes, viz

# Directions candidates : les 6 axes du monde + le milieu des quadrants (un obstacle réel est
# un mur/plafond/paroi aligné, un coin est une intersection de deux demi-espaces).
_AXIS_DIRS = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0),
              "+z": (0, 0, 1), "-z": (0, 0, -1)}


def _world(fk, hull, s) -> np.ndarray:
    """Les K sommets du corps en coordonnées monde à la config ``s`` (K×3)."""
    s = np.asarray(s, float)
    return np.array([fk.eval_world_point(v, s) for v in hull])


def _support(W: np.ndarray, u: np.ndarray) -> float:
    """max_v u·x_v — la fonction d'appui du corps dans la direction ``u`` (W déjà évalué)."""
    return float((W @ u).max())


def measure(sc, sep_dim: int, delta: float, start_s, goal_s, active, n_grid=7, n_slab=5):
    """A(u), B(u) et la marge franche pour chaque direction candidate, séparateur ``s_sep_dim``."""
    fk = scenes._body_fk(sc)
    hull = [[float(c) for c in v] for v in sc.hull_vertices]
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    others = [i for i in active if i != sep_dim]

    # grille de la dalle : séparateur balayé dans [-delta, delta], autres ACTIFS sur la boîte
    slab = []
    for combo in itertools.product(*[np.linspace(lo[i], hi[i], n_grid) for i in others]):
        for sv in np.linspace(-delta, delta, n_slab):
            s = np.zeros(len(sc.box))
            s[sep_dim] = sv
            for i, v in zip(others, combo):
                s[i] = v
            slab.append(s)

    # une seule passe de FK par config (K×3), réutilisée pour toutes les directions
    Wslab = [_world(fk, hull, s) for s in slab]
    Wsg = [_world(fk, hull, start_s), _world(fk, hull, goal_s)]

    out = {}
    for name, u in _AXIS_DIRS.items():
        u = np.array(u, float)
        # (a) obstacle DEMI-ESPACE {x·u >= c} — le motif « plafond / étagère en surplomb »
        A = min(_support(W, u) for W in Wslab)
        B = max(_support(W, u) for W in Wsg)
        # (b) obstacle PLAQUE {c1 <= x·u <= c2} — le motif « paroi à traverser » : il faut
        #     que la plaque coupe le corps dans TOUTE la dalle et le rate aux DEUX poses.
        #     c1 <= A1 = min_dalle max(u·x) ; c2 >= A2 = max_dalle min(u·x) ;
        #     start/goal libres ⟺ c1 > max(u·x)|pose  OU  c2 < min(u·x)|pose.
        A1 = min(_support(W, u) for W in Wslab)              # = A
        A2 = max(-_support(W, -u) for W in Wslab)            # max_dalle min(u·x)
        near = min(-_support(W, -u) for W in Wsg)            # min sur poses de min(u·x)
        plate_near = A1 - max(_support(W, u) for W in Wsg)   # marge côté c1 (pose EN DEÇÀ)
        plate_far = min(-_support(W, -u) for W in Wsg) - A2  # marge côté c2 (pose AU DELÀ)
        out[name] = {"A_slab_min_support": A, "B_startgoal_max_support": B,
                     "franc_margin_m": A - B,
                     "plate_A1": A1, "plate_A2": A2, "plate_pose_min": near,
                     "plate_margin_m": min(plate_near, plate_far)}
    return out, len(slab)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "scenes/S6_iiwa_real_shelf.yaml"
    sc, _ = scenes.load(path)
    prob = scenes.build_problem(sc)
    views = engine.pair_views(prob)
    active = engine._global_active(views, prob)
    n = len(sc.box)
    passive = tuple(i for i in range(n) if i not in active)
    delta = float(sc.delta)

    print(f"=== LEVIER PAR JOINT ACTIF (A43) — {path} ===")
    print(f"corps : link {sc.body_link}, {len(sc.hull_vertices)} sommets   "
          f"actifs = {active}   passifs (redondance) = {passive}")
    print("étiquettes physiques (axe EFFECTIF locked·axe, finding S10-quater) :")
    for nm, lo_, hi_ in viz.joint_limits_deg(sc):
        print(f"   {nm:16s} [{lo_:7.1f}°, {hi_:7.1f}°]")
    print(f"delta = {delta}   (dalle |s_sep| <= delta)")
    print("\nMarge FRANCHE = A(dalle, min portée) − B(start/goal, max portée). "
          "Seuil exigé ≈ +40 mm.\n")

    start_s = [float(x) for x in sc.start_s]
    goal_s = [float(x) for x in sc.goal_s]
    best = []
    for sep in active:
        # start/goal de la scène si le séparateur est celui de la scène ; sinon poses
        # symétriques ±3/5 sur l'axe testé (le motif de conception du portefeuille).
        if any(e[sep] for e in sc.phi):
            s0, s1 = start_s, goal_s
        else:
            s0 = [0.0] * n; s1 = [0.0] * n
            s0[sep], s1[sep] = -0.6, 0.6
        res, npts = measure(sc, sep, delta, s0, s1, active)
        print(f"--- séparateur s{sep} (q{sep+1}) --- dalle échantillonnée sur {npts} configs")
        for nm, r in sorted(res.items(), key=lambda kv: -kv[1]["franc_margin_m"]):
            def _flag(m):
                return "  <== FRANC" if m >= 0.040 else ("  (marginal)" if m > 0 else "")
            print(f"    u={nm}  demi-espace : A={r['A_slab_min_support']:+.4f} "
                  f"B={r['B_startgoal_max_support']:+.4f} "
                  f"marge={r['franc_margin_m']*1000:+8.1f} mm{_flag(r['franc_margin_m'])}")
            print(f"          plaque      : A1={r['plate_A1']:+.4f} A2={r['plate_A2']:+.4f} "
                  f"marge={r['plate_margin_m']*1000:+8.1f} mm{_flag(r['plate_margin_m'])}")
            best.append((r["franc_margin_m"], sep, nm, "demi-espace"))
            best.append((r["plate_margin_m"], sep, nm, "plaque"))
        print()

    best.sort(key=lambda t: -t[0])
    m, sep, nm, kind = best[0]
    print(f"MEILLEUR : séparateur s{sep} (q{sep+1}), obstacle {kind} de normale {nm}, "
          f"marge {m*1000:+.1f} mm  ({'FRANC' if m >= 0.040 else 'INSUFFISANT (<40 mm)'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
