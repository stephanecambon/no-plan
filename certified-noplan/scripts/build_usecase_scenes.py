"""S11 Tâche 1-2 — scènes des DEUX cas d'usage non-flagship, portées sur le VRAI iiwa7.

Repart des specs S9b (`scenes/usecase_binpicking.yaml`, `scenes/usecase_capot_surete.yaml`,
robot générique à corps-SEGMENT) et les RE-CONÇOIT sur la chaîne et la coque GELÉES du vrai
iiwa7 (`scripts/iiwa7_chain.json`, `scripts/iiwa7_body_link3.json`), méthode S10-quater.

CE QUE LA MESURE A TRANCHÉ (`scripts/measure_iiwa7_lever.py`, [A43], journal S11). Sur le vrai
link 3 — un blob compact de ~0,13 m —, le levier par joint actif a été mesuré AVANT de choisir
le séparateur, pour les 3 axes actifs × 6 directions × 2 motifs d'obstacle (demi-espace et
plaque-à-traverser) :

  * **s1 = q2, tangage d'épaule, obstacle en surplomb (+z) : +174,8 mm — le SEUL franc** ;
  * s0 = lacet de base : marge NÉGATIVE dans les 6 directions (−73 à −299 mm) — le finding
    S10-ter des ~6 mm, généralisé : le blob compact tourne sur lui-même sans se déplacer ;
  * s2 = q3, roulis du bras : négatif partout (le corps tourne autour de son propre axe) ;
  * motif PLAQUE (« traverser une paroi de bac ») : négatif partout — le corps reste ANCRÉ à
    l'épaule, il ne peut jamais être entièrement d'un côté d'une paroi verticale.

C'est un RÉSULTAT, pas un choix de confort : sur ce robot et ce lien, le piège proximal franc
est unique (tangage + surplomb). Les trois cas du portefeuille partagent donc la MÊME mécanique
cinématique — ce que `docs/usecases/PORTFOLIO.md` énonce déjà comme une force (« une seule
machinerie, trois marchés ») — et se différencient par la géométrie de l'obstacle, les limites,
la dalle, les poses, le récit et le claim. On le dit, on ne le cache pas.

Chaque scène est ensuite dimensionnée par MESURE : la fenêtre franche (A1 = min du haut du corps
sur la dalle ; B = max du haut du corps aux poses) est calculée, l'obstacle est posé en son
MILIEU (marges égales des deux côtés), et la scène est refusée si la fenêtre est < 80 mm.

Run :  python scripts/build_usecase_scenes.py            # écrit les deux scènes
"""
from __future__ import annotations

import json
import os
from fractions import Fraction as F

import numpy as np
import yaml

from cnp import scenes as _scenes

HERE = os.path.dirname(os.path.abspath(__file__))
CHAIN = os.path.join(HERE, "iiwa7_chain.json")
BODY = os.path.join(HERE, "iiwa7_body_link3.json")
BODY_LINK = 7                      # index-chaîne de q3 (cf. build_iiwa7_scene.BODY_LINK)
MIN_WINDOW_M = 0.080               # fenêtre franche minimale (⟹ ≥40 mm de chaque côté)


def _base_robot() -> dict:
    chain = json.load(open(CHAIN))
    return {"kind": "spatial_revolute",
            "q_star": ["0"] * len(chain["joints"]),
            "joints": [{"offset": j["offset"], "axis": j["axis"]} for j in chain["joints"]],
            "locked": {str(k): v for k, v in chain["locked"].items()}}


def _hull() -> list:
    return json.load(open(BODY))["hull_vertices"]


def _box_hrep(xlo, xhi, ylo, yhi, zlo, zhi) -> dict:
    """Boîte axis-aligned en H-rep EXACTE (étanche par construction) : A y <= b."""
    return {"hrep": {"A": [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"],
                           ["-1", "0", "0"], ["0", "-1", "0"], ["0", "0", "-1"]],
                     "b": [str(F(xhi)), str(F(yhi)), str(F(zhi)),
                           str(-F(xlo)), str(-F(ylo)), str(-F(zlo))]}}


def _scene_dict(obstacle_name, obstacle, box, start_s, goal_s, delta) -> dict:
    n = len(box)
    return {"robot": _base_robot(),
            "body": {"link": BODY_LINK, "hull_vertices": _hull()},
            "obstacles": {obstacle_name: obstacle},
            "phi": {"degree_per_var": 2,
                    "coeffs": {",".join("1" if i == 1 else "0" for i in range(n)): "1"}},
            "delta": str(F(delta)),
            "box": [[str(F(lo)), str(F(hi))] for lo, hi in box],
            "start_s": [str(F(v)) for v in start_s],
            "goal_s": [str(F(v)) for v in goal_s],
            "pairs": [obstacle_name],
            "budget": {"max_depth": 24, "axis": "margin"}}


def franc_window(scene_dict, n_grid=9, n_slab=7) -> tuple:
    """(A1, B) = (min du haut-du-corps sur la DALLE, max du haut-du-corps aux POSES).

    Le corps est en collision partout dans la dalle dès que le dessous de l'obstacle est
    <= A1 ; il est libre aux deux poses dès qu'il est > B. La fenêtre franche est A1 − B."""
    sc, _ = _scenes.parse_scene(yaml.safe_load(yaml.safe_dump(scene_dict)))
    fk = _scenes._body_fk(sc)
    hull = [[float(c) for c in v] for v in sc.hull_vertices]
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)

    def topz(s):
        s = np.asarray(s, float)
        return max(fk.eval_world_point(v, s)[2] for v in hull)

    A1 = min(topz([a, s1, c] + [0.0] * (len(lo) - 3))
             for a in np.linspace(lo[0], hi[0], n_grid)
             for c in np.linspace(lo[2], hi[2], n_grid)
             for s1 in np.linspace(-delta, delta, n_slab))
    B = max(topz([float(x) for x in sc.start_s]), topz([float(x) for x in sc.goal_s]))
    return A1, B


# --------------------------------------------------------------------------- #
# Les deux cas
# --------------------------------------------------------------------------- #

# Bin-picking : rack à deux niveaux d'un poste de prélèvement. Le colis cible est au FOND
# d'un bac du niveau BAS ; un bac du niveau HAUT est rangé juste au-dessus de l'épaule du
# robot. Pour passer de la baie gauche (home) à la baie droite (le bac cible), le bras doit
# se REDRESSER — et le bac du haut l'en empêche. « Il faut d'abord retirer la caisse. »
# Empreinte = un bac euro 600×400 (±0,30 × ±0,20 m), hauteur 220 mm.
BINPICKING = dict(
    name="CRATE_ABOVE",
    footprint=(-F(3, 10), F(3, 10), -F(1, 5), F(1, 5)), height=F(11, 50),
    box=[(-F(3, 5), F(3, 5))] * 3 + [(-3, 3)] * 4,
    start_s=[0, -F(1, 2), 0, 0, 0, 0, 0], goal_s=[0, F(1, 2), 0, 0, 0, 0, 0],
    delta=F(3, 20),
    out="scenes/usecase_binpicking_iiwa7.yaml")

# Capot de sûreté : capot horizontal (canopy) au-dessus de la cellule, zone opérateur de
# l'autre côté. Le bras ne peut pas se redresser au-dessus du plan du capot. Panneau MINCE
# (50 mm) et LARGE (±0,60 m) — géométrie franchement distincte du bac et de l'étagère.
CAPOT = dict(
    name="GUARD_PANEL",
    footprint=(-F(3, 5), F(3, 5), -F(3, 5), F(3, 5)), height=F(1, 20),
    box=[(-F(13, 20), F(13, 20))] * 3 + [(-3, 3)] * 4,
    start_s=[0, -F(23, 40), 0, 0, 0, 0, 0], goal_s=[0, F(23, 40), 0, 0, 0, 0, 0],
    delta=F(9, 50),
    out="scenes/usecase_capot_surete_iiwa7.yaml")


def build_case(case, header: str) -> str:
    xlo, xhi, ylo, yhi = case["footprint"]
    # 1er passage : obstacle bidon très haut (hors d'atteinte) juste pour mesurer la fenêtre
    probe = _scene_dict(case["name"], _box_hrep(xlo, xhi, ylo, yhi, 10, 11),
                        case["box"], case["start_s"], case["goal_s"], case["delta"])
    A1, B = franc_window(probe)
    window = A1 - B
    print(f"--- {case['name']} : fenêtre franche mesurée ---")
    print(f"    A1 (min haut-du-corps sur la dalle)   = {A1:.4f} m")
    print(f"    B  (max haut-du-corps aux poses)      = {B:.4f} m")
    print(f"    fenêtre = {window*1000:+.1f} mm   (exigé >= {MIN_WINDOW_M*1000:.0f} mm)")
    if window < MIN_WINDOW_M:
        raise SystemExit(f"REFUS : fenêtre {window*1000:.1f} mm < {MIN_WINDOW_M*1000:.0f} mm "
                         "— marge non franche (lignée S10-ter, on ne grave pas un piège "
                         "que la marge ne soutient pas)")
    z0 = F(round((A1 + B) / 2 * 200), 200)       # milieu, rationalisé au 1/2 cm
    print(f"    dessous de l'obstacle z0 = {z0} = {float(z0):.3f} m  ⟹ marges "
          f"+{(A1-float(z0))*1000:.1f} mm (pénétration dalle) / "
          f"+{(float(z0)-B)*1000:.1f} mm (dégagement poses)")

    data = _scene_dict(case["name"],
                       _box_hrep(xlo, xhi, ylo, yhi, z0, z0 + case["height"]),
                       case["box"], case["start_s"], case["goal_s"], case["delta"])
    dest = os.path.join(HERE, "..", case["out"])
    with open(dest, "w") as f:
        f.write(header.format(z0=float(z0), A1=A1, B=B,
                              pen=(A1 - float(z0)) * 1000, cle=(float(z0) - B) * 1000))
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=None, width=120)
    print(f"    -> {case['out']}\n")
    return dest


_HDR_COMMON = """#
# MÉCANIQUE (mesurée, pas choisie — scripts/measure_iiwa7_lever.py, [A43]) : sur le VRAI link 3
# du iiwa7 (blob compact ~0,13 m), le SEUL piège proximal franc est « tangage d'épaule q2 +
# obstacle en SURPLOMB » (+174,8 mm). Le lacet de base est NÉGATIF dans les 6 directions (le
# blob tourne sur lui-même sans se déplacer) ; le roulis q3 aussi ; et le motif « traverser une
# paroi verticale » est négatif partout (le corps reste ancré à l'épaule, il ne peut jamais être
# entièrement d'un côté). Les trois cas du portefeuille partagent donc cette mécanique — c'est la
# thèse « une seule machinerie, trois marchés » (PORTFOLIO.md), pas une redite dissimulée.
#
# CORPS = coque convexe FIDÈLE du lien 3 (40 sommets rationalisés, parité Drake ~1,7e-6, S10-ter),
# sur la chaîne GELÉE fidèle à l'URDF iiwa7 à ~2e-6 (S10-bis). Dims actives (0,1,2) ; les 4 joints
# distaux sont PASSIFS automatiquement (en aval du corps) = la thèse « robuste à la redondance ».
# Obstacle H-rep EXACTE (étanche par construction). Barrière phi = s1 (q2, tangage d'épaule).
#
# FENÊTRE FRANCHE MESURÉE : dalle min haut-du-corps A1 = {A1:.4f} m ; poses max haut-du-corps
# B = {B:.4f} m ; dessous de l'obstacle posé au MILIEU, z0 = {z0:.3f} m
# ⟹ +{pen:.1f} mm de pénétration dans la dalle / +{cle:.1f} mm de dégagement aux poses.
# (Lignée S10-ter : on refuse le marginal — les ~6 mm du lacet de base ont été rejetés.)
"""

HDR_BINPICKING = """# S11 — CAS D'USAGE « BIN-PICKING LOGISTIQUE » sur le VRAI iiwa7 : élagage PROUVÉ d'une branche TAMP.
#
# RÉCIT. Poste de prélèvement à rack deux niveaux. Le colis cible est au FOND d'un bac du niveau
# BAS, dans la baie de droite ; le bras est au repos au-dessus de la baie de gauche. Un bac plein
# est rangé au niveau HAUT, juste au-dessus de l'épaule du robot. Le planificateur TAMP ouvre la
# branche « saisir le colis dans le bac du bas SANS dépiler ». Le colis est VISIBLE et PROCHE
# (apparence faisable, A20). Pour passer de la baie gauche à la baie droite, le BRAS doit se
# REDRESSER (q2 change de signe, donc passe par q2~0, bras vertical) — et c'est là que le SEGMENT
# PROXIMAL (lien 3) percute le bac du niveau haut. AUCUN des 4 joints distaux ne l'en sort.
# VALEUR : le planificateur ÉLAGUE la branche AVEC UNE PREUVE (« ce colis est inatteignable sans
# retirer d'abord la caisse du dessus »), au lieu d'échantillonner jusqu'au timeout.
""" + _HDR_COMMON

HDR_CAPOT = """# S11 — CAS D'USAGE « CAPOT DE SÛRETÉ · FENÊTRE OPÉRATEUR » sur le VRAI iiwa7 : certificat EXACT
# RECOMPTABLE pour un dossier de sûreté.
#
# RÉCIT. Cellule robotisée coiffée d'un CAPOT horizontal ; la zone opérateur est de l'autre côté du
# capot. Question d'analyse de risque (ISO 10218 / 13849) : « le bras peut-il, depuis sa zone home,
# atteindre la zone opérateur ? » La zone est VISIBLE et PROCHE, le capot a l'air contournable
# (apparence faisable, A20) — l'intuition dit « il passera ». Le certificat prouve que NON : pour
# basculer d'un côté à l'autre, le bras doit se REDRESSER, et le SEGMENT PROXIMAL (lien 3) percute
# alors le plan du capot ; les 4 joints distaux n'y changent rien. VALEUR : ce n'est pas « croyez
# notre collision-checker flottant » — c'est une pièce ALGÉBRIQUE que l'organisme notifié RECOMPTE
# en arithmétique exacte (`cnp verify`, <500 l., stdlib seule, sans importer le générateur).
#
# CE QUE LE CERTIFICAT NE PROUVE PAS (contexte réglementaire — voir docs/usecases/capot_surete.md) :
# ni la sûreté SYSTÈME (ce n'est PAS une certification ISO, c'est une PIÈCE géométrique versable),
# ni quoi que ce soit hors des limites articulaires affichées, hors de la géométrie modélisée, ni
# rien de dynamique (vitesses, arrêts, capteurs). UNDECIDED ≠ inatteignable.
""" + _HDR_COMMON


def main() -> int:
    print("=== S11 — scènes cas d'usage sur le VRAI iiwa7 (chaîne + corps GELÉS) ===\n")
    build_case(BINPICKING, HDR_BINPICKING)
    build_case(CAPOT, HDR_CAPOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
