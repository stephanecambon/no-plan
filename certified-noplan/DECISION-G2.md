# DECISION-G2.md — Go/no-go technique G2′ (5-6 DOF)

Session S9d (Claude Code) · 12 juin 2026 · commit de référence `eb134e7` (arbre propre).
Sortie formelle du pilotage D22 : la supervision la revoit, **Stéphane la SIGNE avant toute
ouverture de S10**. Ce document est une RECOMMANDATION ; la décision de re-scope, si rouge,
se prend avec Stéphane (pas dans Claude Code).

---

## 1. Verdict G2′ (chiffré) — **GO (vert)**

Critère de sortie G2′ (SPEC §8) : *S4 (5-6 DOF) certifiée PROOF, vérifiée en arithmétique
exacte, en < 1 h sur la machine cible, < 10⁴ feuilles, compteur A32 à zéro.*

| Exigence G2′                         | Mesuré (scène S4 iiwa-like bac profond)             | Verdict |
|--------------------------------------|------------------------------------------------------|---------|
| Verdict                              | **PROOF** (moteur + `verify.py` exact indépendant)   | ✅      |
| Vérification exacte indépendante     | **OK** (`cnp verify` re-dérive la FK, joints verrouillés cos/sin) | ✅ |
| Temps total (machine cible = laptop CPU) | **5-DOF ≈ 1,0 s · 6-DOF ≈ 3,9 s** (certif + verify) — marge ×1000 sous 1 h | ✅ |
| Nombre de feuilles                   | **8** (5-DOF *et* 6-DOF) — marge ×1250 sous 10⁴      | ✅      |
| `n_reresolve_failed` (A32)           | **0** (dissonance décision↔certificat nulle)         | ✅      |

Machine cible : MacBook (Apple Silicon arm64), Python 3.12, **CPU pur, sans GPU**.
Les cinq exigences sont tenues avec une marge de 3 ordres de grandeur. **G2′ est VERT.**

---

## 2. Ce qui est certifié — et la lecture honnête

**Scène S4** (`scenes/S4_iiwa_bin.yaml`) : bras iiwa-like 7 joints (chaîne S-R-S, longueurs
de liens ~ iiwa, axes lacet/tangage alternés), **2 joints poignet VERROUILLÉS à 0** (cos=1,
sin=0) ⟹ 5 DOF actifs ; bac profond à mur frontal scellé. La **déconnexion est PROXIMALE** :
le segment certifié (link 2) a son extrémité proximale piégée dans le mur sur toute la bande
de lacet de base et tout tangage du box ; **aucun jeu des joints distaux ne l'en sort** (ils
ne déplacent que des points au-delà du link 2).

**Vérité-terrain dense AVANT certification** (règle 9, leçon micro-canal) : start/goal libres ;
**0 point libre dans la dalle sur 40 000 échantillons seedés** ; libre des deux côtés (deux
composantes) ; contrôle négatif (mur descellé) ⟹ **UNDECIDED, jamais de faux certificat**.

**Lecture honnête (le point central, non un angle mort).** La scène n'a que **3 dimensions
actives** {lacet, tangage épaule, coude} alors qu'elle a 5-6 DOF : les joints distaux sont
*prouvés passifs* pour la paire de collision. Ce n'est **pas** un cas favorable trié sur le
volet — c'est une **propriété intrinsèque des déconnexions certifiables** : prouver une
déconnexion exige de piéger un corps que le bras ne peut pas déplacer, donc un corps
**proximal**, donc peu de joints actifs. Un piégeage distal serait défait par la redondance
(leçon S5/S6/S7) et ne serait pas une déconnexion. **Conséquence stratégique** : sur
exactement la classe de problèmes qui sont certifiables, le coût suit les **dims actives**,
pas le **DOF total** — la montée en DOF est quasi gratuite (table §3).

---

## 3. Calibration du modèle de coût (A31 / D20 / D31)

Même famille de scènes (le bac S4 avec un nombre croissant de joints verrouillés : les 3
joints actifs {0,1,2} restent fixes, seul le nombre de joints PASSIFS croît). `axis=margin`,
réductions A29/A30 actives. Coût/feuille = lignes Bernstein de la paire WALL (faces + λ≥0).

### 3a. feuilles(n) et coût/feuille — globaux

| n (DOF actifs+passifs) | actifs | passifs | feuilles | coût/feuille RÉDUIT (A30) | coût/feuille PLEIN (sans réduction) | facteur | certif s | verify s | A32 |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 0 | **8** | 766  | 766    | ×1,0   | 0,34 | ~0,04 | 0 |
| 4 | 3 | 1 | **8** | 766  | 3 782  | ×4,9   | 0,36 | ~0,05 | 0 |
| 5 | 3 | 2 | **8** | 766  | 18 814 | ×24,6  | 0,84 | 0,16  | 0 |
| 6 | 3 | 3 | **8** | 766  | 93 878 | ×122,6 | 3,26 | 0,68  | 0 |

**Lecture** : feuilles(n) = **8, constant** (les dims passives n'ajoutent aucune feuille —
le moteur ne branche jamais dessus, A18). Coût/feuille réduit = **766 lignes, constant** (les
3 dims actives fixent (d+1)³). Le coût PLEIN (ce que coûterait l'absence de réduction) explose
en (d+1)ⁿ : le **facteur de réduction A30 atteint ×122 à 6-DOF** et croît ≈×5 par dim passive.
Le temps de certification croît modestement (la re-résolution pleine-dim du certificat à
l'export, soundness S8, est le seul terme qui voit le n complet) : **3,3 s à 6-DOF**, loin de 1 h.

### 3b. Réduction PAR-PAIRE proximale vs distale (A30) — première validation réelle

La scène S4 livrée n'a **qu'UN corps certifié** (link 2) ⟹ sur elle, la réduction par-paire ≡
la réduction globale (dit honnêtement). Le levier par-paire se mesure sur une **variante
deux-corps** de la même chaîne (n=7, sans lock), paire proximale sur link 2 et paire distale
sur link 4 :

| Paire | corps | dims actives | lignes LP par-paire (A30) | lignes LP si global {0,1,2,3,4} |
|---|---|---|---|---|
| PROX (link 2) | proximal | {0,1,2}       | **766**    | 18 814 |
| DIST (link 4) | distal   | {0,1,2,3,4}   | 18 814     | 18 814 |

**Lecture** : la paire proximale ne paie que ses 3 dims actives (**766 lignes**) là où la
réduction globale (union des actifs de toutes les paires = {0,1,2,3,4}) lui imposerait 18 814 —
**×24,6 par-paire** sur la paire proximale. C'est la première mesure réelle (hors synthétique
S9a) du levier A30 : *chaque paire paie SES dims actives, pas l'union*.

### 3c. Ancrage S3 (4-DOF, Li-Dantam, benchmark canonique régénéré)

Benchmark canonique régénéré sur arbre **propre** (commit `eb134e7`, `git_dirty=false`),
`benchmarks/results/20260612T233416Z/` : **S3 (4-DOF) = moteur 0,043 s + verify exact 0,041 s**.
(S1 46 feuilles 0,48 s ; S2-peigne 54 feuilles 1,36 s ; S4 iiwa 8 feuilles 0,15 s.)

---

## 4. Comparaison à Li-Dantam — positionnement, PAS une course

Chiffres **vérifiés à la source** (rule 9/A28) dans **Li & Dantam, « Scaling Motion Planning
Infeasibility Proofs », arXiv:2406.04795, 2024** (PDF lu cette session ; le journal antérieur
est **IJRR 2023**, SAGE 10.1177/02783649231154674 — *le « RA-L 2023 » du prompt est un lapsus
pour IJRR 2023, à corriger*) :

| | **Li-Dantam 2024 (arXiv:2406.04795)** | **certified-noplan (nous, S9d)** |
|---|---|---|
| DOF | 5-DoF & 6-DoF (Packbot, Universal robot, Schunk ; 4 scènes) | 5-6 DOF (bac iiwa-like, piège proximal) |
| Temps | **« les deux scènes 6-DoF prennent moins d'1 minute en moyenne »** (triangulation : secondes→dizaines de s ; collision : dizaines de s) | **5-DOF ≈ 1 s · 6-DOF ≈ 3,9 s** |
| Matériel | **NVIDIA GeForce RTX 4070 (12 Go) + Intel i9-13900K** | **laptop Apple Silicon, CPU pur, sans GPU** |
| Nature du certificat | manifold triangulé (Coxeter) sur GPU, **validé par collision-checker FLOTTANT** | **certificat algébrique Bernstein-LP, exactement re-vérifiable** par un programme indépendant en arithmétique rationnelle (verify.py, <500 l. stdlib) |
| Re-vérification a posteriori | aucune (confiance dans le pipeline flottant) | **oui, exacte** (la clé de crédibilité) |

**Caveats honnêtes (lignée « pas de ×400 »)** :
- **Pas de course apples-to-apples.** Scènes différentes (leurs Packbot/UR/Schunk vs notre
  bac proximal), objets prouvés différents (ils trianglent le manifold séparateur ; nous
  certifions une dalle-barrière), matériel différent (GPU vs CPU). On **NE revendique PAS**
  un facteur de vitesse (« 60 s / 3,9 s ≈ ×15 » serait malhonnête : notre scène exploite la
  passivité, la leur est possiblement plus dense en dims actives).
- **Ce qu'on revendique, prudemment** : on atteint **la même frontière DOF (5-6) que la
  méthode GPU de Li-Dantam, sur un laptop CPU sans GPU**, avec un certificat **d'une autre
  nature** — algébrique et **exactement re-vérifiable** (différenciation A26/D27, pas le DOF).
- Leur méthode scale par **parallélisme massif** (coût intrinsèque élevé absorbé par le GPU) ;
  la nôtre scale par **structure** (réduction aux dims actives). Les deux sont légitimes ; ce
  sont des leviers orthogonaux sur des problèmes différents.

---

## 5. Recommandation — **GO**

**GO vers S9b (portefeuille de cas d'usage) puis S10 (flagship 7-DOF).** Justification :

1. **G2′ vert avec 3 ordres de grandeur de marge** : 5-6 DOF certifiés PROOF, vérifiés exact,
   en secondes sur CPU, 8 feuilles, A32=0.
2. **Le levier qui porte la montée en DOF est mesuré et réel** : ×122 (global) et ×24,6
   (par-paire proximal) — la machinerie A18/A29/A30 transforme un coût (d+1)ⁿ en (d+1)^actif.
3. **L'insight de scope est solide** : les déconnexions certifiables sont proximales ⟹ peu de
   dims actives ⟹ le DOF total n'est pas le driver de coût. **S10 doit choisir un flagship
   7-DOF à piégeage PROXIMAL** (case haute d'étagère inatteignable, capot de sûreté) pour
   rester dans ce régime — c'est une consigne de conception, pas une limite.

**Caveats portés au dossier (pas des bloquants)** :
- La scène S4 est un **bac technique iiwa-LIKE documenté** (table A21 dans le YAML :
  FIDÈLE = chaîne/axes/limites usine ⊂(−π,π) ; CHOISI = offsets rationnels arrondis, frames
  inter-joints simplifiés, mur, locks). Le `spatial_revolute` ne porte pas les rotations
  constantes inter-joints de l'URDF iiwa exact — une reproduction URDF-fidèle exigerait soit
  une formulation POE, soit une extension de `verify.py` (sacré) : **à décider en S10/S11 si
  un reviewer l'exige** ; hors-scope d'un go/no-go technique.
- Box des joints actifs limité à ±70° (limite douce de cellule ⊂ limites usine ±120/±170°) :
  le théorème prouve la déconnexion **dans ce box**, affiché en degrés (A25). Honnête.
- Pas de scène à **dims actives élevées** (le risque d'explosion §9.1) — par construction
  (cf. insight). Si un cas d'usage S9b exige une déconnexion à ≥4 dims actives, **re-mesurer**
  (le facteur (d+1)^actif jouerait alors contre nous) ; ce serait le vrai point de pivot.

**SI la supervision juge ROUGE** : mitigations SPEC §9.1 (heuristique d'axe, sparsité, degré
témoin adaptatif) ; point de pivot journalisé ; re-scope décidé **avec Stéphane**.

---

## 6. Signatures

- [ ] **Supervision (claude.ai)** — revue : _______________________  date : __________
- [ ] **Stéphane Cambon** — SIGNATURE (requise avant toute ouverture de S10) : _______________________  date : __________

Reproductibilité : `python scripts/calibrate_g2.py` (table §3) ;
`benchmarks/results/20260612T233416Z/` (timings canoniques, `calibration.json`) ;
`cnp certify scenes/S4_iiwa_bin.yaml` → PROOF ; `cnp verify <cert> scenes/S4_iiwa_bin.yaml` → OK.
