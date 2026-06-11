# SPEC.md — Démonstrateur d'infaisabilité certifiée en motion planning 3D

Version 1.1 — 10 juin 2026 (amendée post-S2, revue de supervision ; v1.0 dans git).
Projet : « certified-noplan ». Contexte : campagnes E1-E4 (CAMPAGNE-E1-E4-RESULTATS.md).
Amendements v1.1 (actés en S0/S1/S2, règle 12 de CLAUDE.md) : paramétrisation autour
d'une configuration de référence q* ; dénominateur commun PAR LINK ; exposant p=1 ;
témoin à K sommets ; joints verrouillés ; deps. Marqués « [amendé S<X>] ».

---

## 1. Objet

Un outil en ligne de commande qui, pour un robot sériel (chaîne révolute, limites
articulaires dans (−π, π)), une scène d'obstacles statiques et deux configurations
start/goal, produit l'un des deux verdicts :

- **PROOF** : un certificat mathématique, sérialisé et **vérifiable par un programme
  indépendant en arithmétique exacte**, établissant qu'aucune trajectoire continue
  sans collision ne relie start à goal dans les limites articulaires.
- **UNDECIDED** : pas de certificat trouvé au budget donné (ce n'est PAS une preuve
  de faisabilité), avec diagnostic (cellules en échec, visualisation).

Le démonstrateur n'est PAS un planificateur temps réel. C'est un outil de
design-time / dossier de sûreté / élagage TAMP.

## 2. Fondement mathématique (rappel binding)

**Théorème de déconnexion (forme implémentée).** [amendé S1] Soit q* une
configuration de référence (joints débloqués) et s_i = tan((q_i − q*_i)/2) la
paramétrisation rationnelle ; P = Π[s_i^lo, s_i^hi] la boîte des limites
(images de limites articulaires telles que |q_i − q*_i| < π sur tout le domaine —
hypothèse wrap-around, relative à q*). Les joints verrouillés sont substitués par
leurs cos/sin numériques, sans variable s ni facteur (1+s²) ; n = nombre de
joints débloqués, ré-indexés 0..n−1. Soit φ : R^n → R polynomiale,
δ > 0. Si :
(i) φ(s_start) ≤ −δ et φ(s_goal) ≥ +δ ;
(ii) la dalle S = {s ∈ P : |φ(s)| ≤ δ} est entièrement en collision
     (∀s ∈ S, ∃ paire (corps robot, obstacle) en intersection) ;
alors start et goal sont dans des composantes connexes distinctes de C_free.
Preuve de (ii) par partition : arbre binaire de découpes axiales de P ; chaque
feuille est soit (a) certifiée disjointe de S (bornes de Bernstein sur φ),
soit (b) certifiée en collision contre UNE paire via certificat-témoin slab-aware.

**Certificat-témoin (feuille, paire (link L, obstacle O), cellule Q).**
[amendé S1/S2] Témoin x(s) = Σ_k λ_k(s)·v_k^L(s) sur les K sommets de
l'enveloppe convexe du link L, λ_k polynomiaux (base à degré total borné,
const/affine/quadratic, défaut affine), Σλ_k ≡ 1 (identité de coefficients),
λ_k ≥ 0 sur Q (Bernstein). v_k^L(s) = positions monde des sommets : NUMÉRATEURS
rationnels de la FK sur le **dénominateur commun PAR LINK**
D_L(s) = ∏_{i ∈ chaîne débloquée de L} (1 + s_i²) > 0. La substitution
demi-angle est « maison » (approche C, S1) : depuis le polynôme multilinéaire en
(cos_delta_i, sin_delta_i), cos→(1−s_i²), sin→2s_i, joint hors-chaîne→(1+s_i²) —
c'est cette substitution, et pas celle de Drake, que verify.py ré-implémente
indépendamment (S4). Pour chaque face (aᵀy ≤ b) de O (H-représentation) :
g(s) = b·D_L(s) − aᵀX(s) ≥ 0 où X = Σ_k λ_k·N_k = numérateur de x (p = 1 suffit).
Forme slab-aware : Bernstein(g − μ·(δ² − φ²)) ≥ t sur Q, μ ≥ 0.
ATTENTION SIGNE : g − μT (g + μT est UNSOUND, bug documenté E3).
Tout est linéaire en (coeffs de λ, μ, t) ⟹ **LP**. Aucun SDP, aucun Mosek
dans le chemin critique.

**Hypothèses du théorème (à afficher dans chaque certificat) :**
- limites articulaires strictement incluses dans (−π, π) par joint (pas de wrap-around) ;
- obstacles statiques, corps robot = enveloppes convexes (polytopes) ;
- géométrie de scène = données exactes (rationnels) du fichier scène.

## 3. Architecture

```
certified-noplan/
├── CLAUDE.md                  # règles + plan de sessions (binding)
├── SPEC.md                    # ce fichier
├── JOURNAL.md                 # tenu à jour à chaque session
├── pyproject.toml             # python 3.12 ; base: numpy, scipy, cvxpy, sympy
│                              # (repli FK), highspy, scikit-learn, pyyaml,
│                              # matplotlib, meshcat ; extra [drake] requis dès S1
│                              # (make setup installe .[drake,dev]) [amendé S0/S1]
├── src/cnp/                   # NOTE [S0] : l'oracle de régression du bac à sable
│   │                          # vit dans tests/regref.py, jamais importé par src/cnp
│   ├── polylin.py             # tenseurs polynomiaux, Bernstein (porté du sandbox)
│   ├── ratfk.py               # wrapper Drake RationalForwardKinematics →
│   │                          # tenseurs numérateurs par sommet de link
│   ├── witness.py             # construction LP du certificat-témoin slab-aware
│   ├── engine.py              # branch-and-bound n-dim, heuristiques d'axe,
│   │                          # parallélisme, checkpoint/resume
│   ├── phifit.py              # échantillonnage (collision checker Drake),
│   │                          # fit SVM/moindres carrés, approx polynomiale, δ auto
│   ├── certificate.py         # format JSON, sérialisation, statistiques
│   ├── verify.py              # VÉRIFICATEUR INDÉPENDANT (voir §5)
│   ├── scenes.py              # parser YAML scène → modèle Drake + H-rep obstacles
│   └── viz.py                 # Meshcat 3D + figures C-space/partition
├── scenes/                    # *.yaml (voir §6)
├── benchmarks/                # harness + résultats datés (jamais écrasés)
└── tests/                     # pytest ; inclut contrôles négatifs obligatoires
```

Back-end LP : HiGHS (highspy) en direct pour les feuilles (perf) ; cvxpy/Clarabel
accepté pour le prototypage. Parallélisme : multiprocessing sur les feuilles.

## 4. Format de certificat (JSON)

[amendé S1, schéma finalisé en S4]
```json
{
  "spec_version": "1.1",
  "theorem": "disconnection",
  "robot": {"urdf": "...", "joint_limits_rad": [...],
            "q_star": ["...rationnels..."],
            "locked_joints": {"idx": {"cos": "...", "sin": "..."}}},
  "kinematics": {"substitution": "half_angle_homemade_v1",
                 "denominator": "per_link_prod_1_plus_s2"},
  "assumptions": ["no_wraparound_rel_qstar", "static_obstacles", "polytope_geometry"],
  "phi": {"degree_per_var": 2, "coeffs": {...}},   // tenseur sparse {expo: rationnel}
  "delta": "7/200",                                 // rationnels en chaînes
  "start_q": [...], "goal_q": [...],
  "checks": {"phi_start": "...", "phi_goal": "..."},
  "tree": {...},          // arbre binaire de découpes (axe, point de coupe rationnel)
  "leaves": [
    {"cell": [["lo","hi"],...], "status": "outside"},
    {"cell": [...], "status": "collision", "pair": ["link_6", "shelf_top"],
     "lambda_degree": "affine", "lambda_coeffs": {...}, "mu": ["...", ...],
     "margin": "..."}
  ],
  "stats": {"n_leaves": 0, "time_s": 0, "lp_rows_max": 0}
}
```
Tous les nombres du certificat sont des **rationnels exacts** (coupes dyadiques,
coefficients arrondis vers l'intérieur de la zone faisable avant export — la marge
absorbe l'arrondi ; si la marge ne l'absorbe pas, la feuille est re-résolue).

## 5. Vérificateur indépendant (clé de crédibilité)

`cnp verify cert.json scene.yaml` — script volontairement minimal (< 500 lignes,
numpy interdit dans le chemin de preuve, `fractions.Fraction` uniquement) qui :
1. revalide les hypothèses (limites ⊂ (−π,π), obstacles du fichier scène = H-rep du certificat) ;
2. vérifie φ(s_start) ≤ −δ, φ(s_goal) ≥ +δ (arithmétique exacte) ;
3. vérifie que l'arbre partitionne exactement P (couverture par construction :
   chaque nœud = union disjointe de ses deux enfants) et que toute feuille est décidée ;
4. pour chaque feuille « outside » : coefficients de Bernstein de φ−δ ou −φ−δ tous ≥ 0 ;
5. pour chaque feuille « collision » : reconstruit g à partir de la FK rationnelle
   SYMBOLIQUE (recalculée indépendamment, pas reprise du certificat), injecte λ, μ
   fournis, vérifie Σλ ≡ 1, Bernstein(λ_k) ≥ 0, et Bernstein(g − μT) ≥ 0, le tout en exact.
Le générateur et le vérificateur ne partagent QUE polylin (transformée de Bernstein),
ré-implémentée en exact dans verify.py (duplication assumée, c'est le but).

## 6. Scènes (du jouet au real-world)

Format YAML : robot (URDF Drake ou planaire builtin), joints verrouillés,
obstacles (boîtes, prismes convexes ; sommets rationnels), start/goal,
hint φ optionnel, budget (depth max, temps).

- **S1 — planaire 2-DOF « relais »** (portage E3/E4) : 3 obstacles à relais de
  paires. Rôle : régression, tests rapides.
- **S2 — planaire 3-DOF « peigne »** : bras 3 segments, passage entre dents d'un
  peigne d'obstacles ; déconnexion par dent retirée/ajoutée. Rôle : premier n>2
  multi-paires.
- **S3 — 4-DOF « bookshelf » (ancrage Li-Dantam)** : reproduction d'une scène de
  type étagère utilisée par Li & Dantam (bras 4-DOF, objet hors d'atteinte derrière
  une planche). Rôle : comparaison directe à l'état de l'art rigoureux, à DOF égal.
- **S4 — 5/6-DOF « bac profond » (bin picking)** : iiwa à joints verrouillés,
  prouver qu'un objet au fond d'un bac n'est PAS atteignable sans retirer la caisse
  de devant. Application : élagage prouvé en task-and-motion planning.
- **S5 — 7-DOF iiwa « étagère » (flagship, ancrage C-IRIS)** : KUKA iiwa14 complet
  (limites usine, toutes ⊂ (−π,π) ✓), étagère type scène C-IRIS + panneau
  obstruant ; prouver que la case haute est inatteignable depuis home. Application :
  validation de conception de cellule (« avec ce capot, l'outil ne peut pas
  atteindre la fenêtre opérateur ») — argument dossier de sûreté ISO 10218/15066.
- **S6 (stretch) — « glovebox »** : cellule confinée, prouver que l'outil ne peut
  pas toucher une zone de conduite. Même machinerie que S5, narration
  nucléaire/téléopération.
- **Stretch hors v1** : self-collision et bimanuel (témoin = égalité de deux
  combinaisons convexes, reste un LP — voir note dans witness.py), corps capsules
  (quadratique ⟹ feuilles SOS ponctuelles), wrap-around.

## 7. Benchmarks et métriques

- **B1** : scènes Li-Dantam (récupérer leur code/scènes si publics — vérifier en
  S7 ; sinon ré-implémentation depuis les papiers arXiv 2406.04795 / 2501.11434,
  documentée comme telle). Métrique : temps-jusqu'à-preuve à 3-4 DOF (eux vs nous),
  puis 5+ DOF (nous seuls — c'est LE résultat-titre).
- **B2** : scène étagère C-IRIS (géométries du repo Drake). Pas de comparaison de
  temps (objet différent : eux certifient le libre) — comparaison de POSITIONNEMENT.
- **B3** : 2-3 scènes MotionBenchMaker adaptées (bookshelf, table) en variantes
  infaisables.
- Métriques systématiques par run : temps total, #feuilles, profondeur max,
  lignes LP max, degré témoin utilisé, temps de vérification exacte, verdict.
  Courbes : temps et #feuilles vs DOF. Tout run écrit benchmarks/results/<date>/.

## 8. Portes go/no-go (révisées)

- **G0'** ✅ (S0) : parité bac à sable → machine locale (43 tests, t* à 1e-6).
  S1 ✅ (FK rationnelle, parité < 1e-9) et S2 ✅ (témoin 3D, parité E3 < 1e-7,
  isolation back-end HiGHS prouvée) acquis — voir JOURNAL.md.
- **G1'** : témoin 3D validé vs vérité-terrain échantillonnée sur S2 (3-DOF) ;
  zéro faux certificat sur la suite adversariale (§9).
- **G2'** : S4 (5-6 DOF) certifié en < 1 h sur la machine cible, < 10⁴ feuilles.
  SI ÉCHEC : actionner les mitigations §9 avant d'élargir le périmètre.
- **G3'** : S3 reproduit et chiffré face à Li-Dantam à 4-DOF.
- **G4'** : S5 (7-DOF) certifié + vérification exacte indépendante OK. C'est le
  résultat-titre du papier.

## 9. Risques techniques et mitigations

1. **Explosion du nombre de feuilles à n≥5** (LE risque restant). Mitigations dans
   l'ordre : heuristique d'axe guidée par les marges LP des échecs ; dimensions
   passives traitées par intervalles (Bernstein restreint aux k dims actives,
   lignes (d+1)^k au lieu de (d+1)^n) ; exploitation de la sparsité des tenseurs
   FK ; degré du témoin adaptatif par feuille (constant → affine → quadratique) ;
   parallélisme.
2. **Taille des LP feuilles à 7-DOF** : 4^7 = 16 384 lignes Bernstein par
   inégalité, ~6-12 faces par obstacle ⟹ LP de 10⁵ lignes. HiGHS tient, mais
   profiler tôt (S8) ; sparsité et dims actives en première ligne.
3. **Degré de φ approximant la SVM** : si deg ≤2/var ne suffit pas, monter à 3
   (tenseurs 5^n — coût) ou φ par morceaux (une dalle par tronçon, théorème
   composé). À trancher sur données en S5'.
4. **Friction API Drake** : RÉSOLU en S1 (wheel 1.46.0 arm64 OK ; substitution
   demi-angle maison car les dénominateurs réduits de Drake sont inutilisables
   comme dénominateur commun ; repli sympy opérationnel, interface identique).
   Reste : dépendance réseau au premier téléchargement des modèles
   (pré-télécharger avant S9-S10, règle 13) ; mosek présent en transitif dans le
   wheel Drake — jamais importé, test-garde en S3 (règle 3).
5. **Soundness** : suite adversariale obligatoire (scènes à prémisse fausse :
   obstacles rétrécis, micro-canaux insérés exprès — leçon E3) ; le CI échoue si
   un seul certificat passe sur prémisse fausse ; arithmétique exacte au shipping.
6. **Antériorité** : revue de littérature sérieuse (pas 2 recherches web) en
   parallèle des sessions S0-S2 — tâche humaine assistée, pas Claude Code.

## 10. Hors périmètre v1

Temps réel ; obstacles mobiles ; joints prismatiques (extension facile, plus tard) ;
preuves de FAISABILITÉ ; complétude (le théorème asymptotique est un travail
papier, pas démonstrateur) ; GUI au-delà de Meshcat.
