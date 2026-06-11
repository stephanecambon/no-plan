# SPEC.md — Démonstrateur d'infaisabilité certifiée en motion planning 3D

Version 1.3 — 11 juin 2026 (amendée post-S6 ; v1.0/v1.1/v1.2 dans git).
Projet : « certified-noplan ». Contexte : campagnes E1-E4 (CAMPAGNE-E1-E4-RESULTATS.md).
Amendements v1.1 (actés en S0/S1/S2, règle 12 de CLAUDE.md) : paramétrisation autour
d'une configuration de référence q* ; dénominateur commun PAR LINK ; exposant p=1 ;
témoin à K sommets ; joints verrouillés ; deps. Amendements v1.2 (actés en S4) :
schéma de certificat §4 FINALISÉ ; condition (i) vérifiée en espace-s sur des images
rationnelles de start/goal ; q* absorbé dans s pour les joints débloqués (le
vérificateur exact planaire n'admet que q*=0) ; certificat auto-suffisant en S4 (la
scène YAML croisée arrive en S6). Amendements (actés en S5) : phifit prend un
**oracle de collision générique** en argument (le checker Drake est branché aux
scènes Drake, S9+) — chemin planaire = oracle regref, chemin 3-DOF spatial = chaîne
3R sympy, tout sans réseau (cohérent avec S2) ; la scène 3-DOF spatiale est certifiée
**moteur-PROOF + échantillonnage dense** (le vérificateur exact reste planaire
jusqu'à S9, kind `spatial_revolute` du schéma §4 = S9+) — portée honnête, pas un
affaiblissement. Amendements (actés en S6) : §6 — le parser YAML accepte les
obstacles en **boîtes axis-aligned (lo/hi par axe)** ou **H-rep brute (A,b)**,
toutes rationnelles ; les prismes convexes en **V-rep (sommets → enveloppe →
H-rep)** sont différés (l'enveloppe convexe exacte est un chantier à part) ; le
builtin **`spatial_revolute`** (chaîne 3R générique par joints offset/axe) est
supporté **côté moteur** ⟹ verdict **ENGINE-PROOF** (le vérificateur exact reste
planaire jusqu'à S9, A17) ; verdicts produit à trois statuts PROOF /
ENGINE-PROOF / UNDECIDED. Marqués « [amendé S<X>] ».

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

**Condition (i) en espace-s [amendé S4].** start/goal entrent dans le certificat
comme **images rationnelles exactes** s_start, s_goal (et non comme q : tan(θ/2) des
angles de démo est irrationnel, invérifiable en exact). Le vérificateur teste
φ(s_start) < −δ et φ(s_goal) > +δ en arithmétique exacte ; il certifie donc la
déconnexion entre deux **configurations réelles** q = q* + 2·arctan(s) d'images
rationnelles. C'est une restriction de portée honnête (règle 6), pas un affaiblissement.

**Absorption de q* [amendé S4].** Pour les joints **débloqués**, q* est absorbé dans
s_i = tan((q_i − q*_i)/2) : les numérateurs FK en fonction de s ne dépendent PAS de q*.
Ré-injecter un q* ≠ 0 exigerait la pré-rotation constante Rot(q*_i), donc cos/sin(q*_i)
rationnels (irrationnels en général). Le vérificateur exact planaire (S4) n'admet donc
que **q* = 0** et **refuse** un q* ≠ 0 plutôt que de le « croire » (règle 5) ; les
scènes Drake à q* ≠ 0 (S9+) porteront les cos/sin verrouillés en rationnels.

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
│   ├── phifit.py              # échantillonnage (oracle de collision générique en
│   │                          # arg ; Drake branché S9+ [amendé S5]), fit SVM/
│   │                          # moindres carrés, approx polynomiale, δ auto, retry
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

[schéma FINALISÉ S4] Tous les nombres sont des **chaînes rationnelles exactes**
("num/den"). Le certificat est **auto-suffisant** en S4 (il embarque la scène exacte
que verify recalcule ; le croisement avec un YAML externe arrive en S6).
```json
{
  "spec_version": "1.2",
  "theorem": "disconnection",
  "robot": {"kind": "planar_revolute",          // S4 ; "spatial_revolute" en S9+
            "link_lengths": ["1", "1"], "q_star": ["0", "0"],
            "locked_joints": {"idx": {"cos": "...", "sin": "..."}},  // {} en S4
            "n": 2},                              // nb de joints débloqués (= #vars s)
  "kinematics": {"substitution": "half_angle_homemade_v1",
                 "denominator": "per_link_prod_1_plus_s2"},
  "assumptions": ["no_wraparound_rel_qstar", "static_obstacles", "polytope_geometry"],
  "body": {"link": 1, "hull_vertices": [["0","0","0"], ["1","0","0"]]},  // frame-corps
  "obstacles": {"UP": {"A": [["1","0","0"], ...], "b": ["13/10", ...]}, ...},  // H-rep
  "phi": {"degree_per_var": 2, "n": 2, "coeffs": {"1,0": "1"}},  // tenseur sparse
  "delta": "1/20",
  "box": [["-1","1"], ["-1","1"]],               // boîte P en espace-s (rationnelle)
  "start_s": ["-9/10","0"], "goal_s": ["9/10","0"],  // images rationnelles (cond. i)
  "checks": {"phi_start": "-9/10", "phi_goal": "9/10"},
  "lam_degree": "affine",
  "pairs": ["UP", "DOWN", "MID"],                // obstacles relayés
  "leaves": [
    {"cell": [["lo","hi"],...], "status": "outside"},
    {"cell": [...], "status": "collision", "obstacle": "MID",
     "lambda": [{"0,0":"1/2", ...}, ...],        // K tenseurs ; Σλ_k ≡ 1 (exact)
     "mu": ["...", ...], "margin": "..."}         // μ par face ; marge LP (info)
  ],
  "stats": {"n_leaves": 46, "n_collision": 38, "n_outside": 8}
}
```
Tous les nombres du certificat sont des **rationnels exacts** (coupes dyadiques ;
coefficients arrondis vers l'intérieur avant export). **Arrondi des multiplicateurs
[S4]** : λ est mélangé vers le barycentre du corps (les zéros structurels de Bernstein
remontent à α/K > 0 et survivent à l'arrondi ; le barycentre somme à 1, donc Σλ_k ≡ 1
reste exact, le dernier sommet étant DÉRIVÉ par soustraction), puis arrondi à
`max_den` ; μ arrondi inférieurement ≥ 0. Re-vérification flottante à marge stricte,
escalade (α, max_den) si besoin (SPEC §5 « re-résolution »). Le vérificateur exact
(§5) est l'arbitre final ; le test round-trip generate→verify est la garantie.

## 5. Vérificateur indépendant (clé de crédibilité)

`cnp verify cert.json scene.yaml` — script volontairement minimal (< 500 lignes,
numpy interdit dans le chemin de preuve, `fractions.Fraction` uniquement) qui :
1. revalide les hypothèses (δ>0, boîte bien formée, dim obstacle ; refuse q*≠0 en S4,
   cf. §2 ; en S6+, obstacles du fichier scène = H-rep du certificat) ;
2. vérifie φ(s_start) < −δ et φ(s_goal) > +δ (STRICT, arithmétique exacte ; §2 cond. i) ;
3. vérifie que les feuilles **pavent exactement** P (cover disjoint reconstruit par
   récursion sur les bissections au milieu — l'arbre n'est pas stocké, il est
   re-dérivé) et que toute feuille est décidée (outside/collision) ;
4. pour chaque feuille « outside » : coefficients de Bernstein de φ−δ ou −φ−δ tous ≥ 0 ;
5. pour chaque feuille « collision » : reconstruit g à partir de la FK rationnelle
   SYMBOLIQUE (recalculée indépendamment, pas reprise du certificat), injecte λ, μ
   fournis, vérifie Σλ ≡ 1, Bernstein(λ_k) ≥ 0, et Bernstein(g − μT) ≥ 0, le tout en exact.
Le générateur et le vérificateur ne partagent QUE polylin (transformée de Bernstein),
ré-implémentée en exact dans verify.py (duplication assumée, c'est le but).

## 6. Scènes (du jouet au real-world)

Format YAML [amendé S6] : robot (`planar_revolute` builtin, ou `spatial_revolute`
= chaîne 3R générique par joints offset/axe ; URDF Drake en S9+), joints
verrouillés, obstacles en **boîtes axis-aligned (lo/hi par axe)** ou **H-rep brute
(A,b)** — toutes rationnelles ; les prismes convexes en V-rep (sommets → enveloppe
→ H-rep) sont différés. start/goal en **images s rationnelles** (cond. i, §2),
boîte P en espace-s, hint φ rationnel (obligatoire en S6 : le fit automatique
phifit/S5 bake son φ rationnel dans la scène), budget (depth max, temps,
**heuristique d'axe** oracle/margin — ne touche jamais la soundness, règle 9).
L'enveloppe convexe du corps mobile est **extraite de la géométrie du link** (le
link planaire = segment `[0,0,0]→[len,0,0]`) si `hull_vertices` n'est pas donné.
`cnp certify` rend PROOF (vérifié exact) / ENGINE-PROOF (moteur OK, vérif. exacte
indisponible — spatial avant S9) / UNDECIDED ; `cnp verify cert scene.yaml`
croise la scène externe ; `cnp show scene.yaml` ouvre une vue Meshcat minimale.

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
