# JOURNAL.md — certified-noplan

Convention : une entrée par session Claude Code. Format : Fait / Décisions /
Pièges rencontrés / Prochaine étape. Ne jamais réécrire l'historique.

---

## 2026-06-10 — Session amont (claude.ai, pré-S0)

**Fait** : campagne expérimentale E1-E4 dans le bac à sable claude.ai (voir
docs/CAMPAGNE-E1-E4-RESULTATS.md). Témoin affine validé (n=3..6), back-end
Bernstein-LP validé (t* identique au SOS, scaling jusqu'à n=10 synthétique),
déconnexion multi-paires certifiée end-to-end en 2-DOF (46 feuilles, 3 paires en
relais), pipeline φ-appris certifié. Contrôles de soundness OK. SPEC.md et
CLAUDE.md rédigés.

**Décisions** : Bernstein-LP comme back-end unique du chemin critique (pas de
SDP/Mosek) ; vérificateur indépendant en arithmétique exacte obligatoire ;
obstacles statiques en v1 ; plan en 13 sessions S0-S13, portes G0'-G4'.

**Pièges (à ne pas repayer)** : signe de Putinar (g − μT, jamais g + μT) ;
coupes dyadiques vs frontières de dalle non dyadiques (⟹ certificat slab-aware
obligatoire) ; la grille d'échantillonnage ne fait pas foi (micro-canal raté par
41 points, attrapé par le certificateur) ; profondeur = coût, pas faisabilité.

**Prochaine étape** : S0 — environnement, squelette, portage régression
(critères de sortie dans CLAUDE.md).

---

## 2026-06-10 — S0 (Claude Code) — **G0' vert**

**Fait** :
- venv Python 3.12 Homebrew (`.venv`) + `pyproject.toml` (deps SPEC §3) ;
  `make setup` idempotent (deuxième appel = no-op), `make test`, `make clean`.
- Arborescence `src/cnp/` complète (SPEC §3) : `polylin.py` porté du bac à sable
  (numérique inchangé) ; `ratfk/witness/engine/phifit/certificate/verify/scenes/viz`
  en stubs datés par session.
- Suite régression pytest : **43 tests, `make test` vert en 63 s**.
  - `test_polylin.py` : les self-tests du `__main__` de polylin convertis.
  - `test_exp12_ladder.py` : E1/E2 rejoués depuis `sandbox_reference/exp12_results.json`
    (16 lignes bern-LP reproduites à **1e-6** — souvent <1e-9 ; 14 lignes SOS-SDP à
    1e-5 ; accord LP=SOS vérifié). t* identiques : const −0.090, affine/multilin
    +0.220, contrôle négatif −0.190.
  - `test_exp34_multipair.py` : E3 **certified=True, 46 feuilles** (38 collision —
    UP 12 / DOWN 12 / MID 14 ; 8 outside ; 0 fail) ; contrôle négatif (obstacles
    rétrécis 30 %) **refusé** (soundness) ; E4 (φ appris) **78 feuilles, 76 collision**.
  - `test_putinar_sign.py` : **fige le signe g − μT**. Instance trouvée (pair UP
    rétréci, cell s1∈[−0.125,0], s2∈[0.875,1]) où la prémisse est réellement fausse
    (configs libres présentes) : le bon signe refuse (t*=−0.039), `g + μT` certifie
    **faussement** (t*=+0.029). Flipper le défaut casse le test.
  - Scènes planaires E3/E4 = fixtures réutilisables (`conftest.py`).

**Décisions** :
- Le code de régression du bac à sable vit sous `tests/regref.py`, **pas** dans
  `src/cnp` (witness/engine sont S2/S3) ; seul noyau partagé : `cnp.polylin`.
- SOS-SDP conservé pour le cross-check E2 mais isolé dans `regref` (jamais importé
  par le cœur — règle 3) ; tol SOS 1e-5 (point intérieur), tol LP 1e-6.
- `certify_cell_pair(..., putinar_sign=-1)` : le paramètre n'existe **que** pour le
  test de signe ; le défaut est le signe sound (soustraction).
- **Drake non installé en S0** : déplacé dans l'extra `[drake]` du pyproject ; non
  nécessaire pour la régression planaire, wheel macOS arm64 traitée en S1.

**Pièges rencontrés** :
- Le dépôt git est la racine `no-plan/` ; le projet est dans `certified-noplan/`.
  Tout le squelette est sous ce sous-dossier.
- `exp12_ladder.py` écrit `exp12_results.json` dans le cwd : le rejouer pour vérifier
  pouvait écraser un fichier ; la référence `sandbox_reference/` n'a jamais été
  touchée et le test rejoue en mémoire sans rien écrire.
- 5 avertissements Clarabel « Solution may be inaccurate » (cas multilinéaires /
  négatifs) : bénins, t* reproduit dans la tolérance. **Non supprimés** par choix
  d'honnêteté — les masquer cacherait une dégradation future. À surveiller en S8.

**Prochaine étape** : S1 — FK rationnelle 3D (`ratfk.py`) ; installer l'extra
`[drake]` (`pip install -e ".[drake,dev]"`) ou activer le repli sympy si friction.

---

## 2026-06-10 — S1 (Claude Code) — FK rationnelle 3D vert

**Fait** :
- G0' re-vérifié vert avant démarrage (43 tests, 64 s).
- Drake 1.46.0 installé (wheel macOS arm64, `pip install drake`), `pydrake`
  + `RationalForwardKinematics` importables sans friction.
- `src/cnp/ratfk.py` implémenté : pour chaque body, pose monde en fonctions
  **rationnelles de s = tan((q−q*)/2)**, numérateurs (rotation 3×3 + position 3)
  sur **dénominateur commun canonique D(s) = ∏(1+s_i²) > 0**, degré ≤2/var.
  - Container back-end-agnostique `BodyRatFK` (n, s_chain, D, pos_num, rot_num ;
    `point_numerator(p_B)` = position monde d'un point body-frame = combinaison
    linéaire des numérateurs sur D ; `vertex_numerators`, `eval_world_point`).
  - Back-end Drake `DrakeRatFK(plant, locked, q_star)` ; back-end repli sympy
    `SympyRatFK(joints, locked, q_star)` (chaîne révolute générique), **même
    interface**.
- `tests/test_ratfk.py` (8 tests) — critères de sortie S1 atteints :
  - **FK numérique vs tenseurs, 1000 configs iiwa aléatoires** (dans les limites
    usine ⊂ (−π,π)), 7 links × 3 points body-frame : **erreur max < 1e-9**
    (typiquement ~3e-15).
  - **joints verrouillés** : `locked={1,4}`, n=5, FK reproduite < 1e-9.
  - **degré ≤2/var** par tenseur ; chaîne croissante (link_k dépend de s_0..s_{k-1},
    EE de tous les 7).
  - **repli sympy** validé vs FK numérique homogène indépendante (1000 configs,
    chaîne spatiale 3-DOF aléatoire) + variante verrouillée + degré ≤2.
  - **parité Drake↔sympy** sur cinématique identique (plant Drake construit par
    programme, sans réseau) : tenseurs égaux à 1e-9.
- `make test` complet : **51 passed** (43 régression + 8 ratfk), 77 s, mêmes
  5 warnings Clarabel bénins.

**Décisions** :
- **Substitution rationnelle faite maison (Approche C), pas le dénominateur de
  Drake.** `ConvertMultilinearPolynomialToRationalFunction` rend des dénominateurs
  réduits **distincts par entrée** (4 différents sur une pose) → inutilisable comme
  dénominateur commun. On part du polynôme **multilinéaire** (indéterminées
  `cos_delta[i]`/`sin_delta[i]`) et on dégage soi-même le demi-angle sur le
  dénominateur commun canonique : cos→(1−s²), sin→2s, joint absent→(1+s²). C'est
  exactement la substitution que `verify.py` recalculera indépendamment en S4 → FK
  auditable, pas « de confiance » (règle 4).
- **Dénominateur commun par link** (∏ sur les joints débloqués de la chaîne du
  body) — SPEC §2 « dénominateur commun » s'entend par link. Le témoin (S2) utilise
  le D du link concerné.
- **Joints verrouillés** : substitués par leurs cos/sin numériques, **sans variable
  s ni facteur (1+s²)** ; les débloqués sont ré-indexés 0..n−1.
- **Sommets d'enveloppe convexe en paramètre** (`point_numerator`/`vertex_numerators`)
  plutôt qu'extraits de la géométrie ici : l'extraction depuis la scène est S6 et le
  témoin (S2) fournira les sommets. Le livrable S1 = les tenseurs FK rationnels.
- `sympy` ajouté aux deps de base (repli) ; **Makefile installe `.[drake,dev]`**
  dès maintenant (Drake nécessaire au cœur à partir de S1) ; `importorskip` garde
  la suite gracieuse si le wheel Drake échoue un jour.
- Réutilisation du seul noyau partagé `cnp.polylin` pour l'algèbre tensorielle
  (mono/tmul/teval/zeros).

**Pièges rencontrés** :
- **Matrice homogène et dénominateur** (bug sympy, attrapé par les tests) : le
  coin (3,3) de la transfo homogène de rotation doit valoir `den`, pas 1, sinon la
  colonne translation est silencieusement divisée par (1+s²). Construire `den·I`
  puis écraser le bloc rotation.
- **Ordre de composition** : X_parent_child = X_pj · Rot(axe,θ) (offset puis
  rotation), pas l'inverse.
- **Mosek tiré en transitif par le wheel Drake** (8 Mo) : jamais importé, règle 3
  respectée (aucun `import mosek` dans le cœur). À surveiller qu'aucun chemin Drake
  ne le réveille.
- **Dépendance réseau** : le modèle iiwa est téléchargé une fois par Drake
  (`package://drake_models`, cache local) ; les tests iiwa **skippent proprement**
  hors-ligne (fixture try/except), le repli sympy et la parité tournent sans réseau.
- Hypothèse de portée assumée : chaîne révolute série, base soudée ⟹ index de
  position = index de joint/delta (asserté via limites ⊂ (−π,π) et n=positions).

**Prochaine étape** : S2 — témoin 3D (`witness.py`) : LP témoin slab-aware générique
n-dim (corps convexe mobile vs polytope statique H-rep), degré de λ paramétrable,
back-end cvxpy d'abord. Entrée : `BodyRatFK.vertex_numerators` + D par link.

---

## 2026-06-10 — S2 (Claude Code) — Témoin 3D vert

**Fait** :
- S1 re-vérifié vert avant démarrage (51 tests, 77 s).
- `src/cnp/witness.py` implémenté : LP témoin slab-aware **générique n-dim**, corps
  convexe mobile (sommets = numérateurs FK sur dénominateur commun, via `ratfk`) vs
  polytope statique en **H-rep** (`Polytope`, fabrique `box`).
  - Témoin x(s) = Σ_k λ_k(s)·v_k(s), Σλ_k≡1, λ_k≥0 (Bernstein) ; face j de O :
    g_j = b_j·D − a_jᵀX ≥ 0 ; slab `T = δ²−φ²` ; contrainte **Bernstein(g_j − μ_j·T) ≥ t**,
    μ_j ≥ 0 ; maximise t. Tout linéaire en (coeffs λ, μ, t) → **LP** (aucun SDP/Mosek).
  - **Degré de λ paramétrable** : `const`/`affine`/`quadratic` (base à degré total
    borné ; défaut affine).
  - **Interface back-end isolée** : `build_witness_lp` rend un `WitnessLP`
    solveur-agnostique (numpy pur) ; `LPBackend`/`CvxpyBackend` (CLARABEL) le
    consomment. S8 branchera highspy sur le **même** `WitnessLP`.
  - `eval_witness_point` : reconstruit x(s) batch (numpy vectorisé) depuis la solution,
    pour le contrôle vérité-terrain échantillonnée.
- `tests/test_witness.py` (14 tests) — critères de sortie S2 atteints :
  - **Exit #1** — **S1-planaire embarquée en 3D reproduit le certificat E3** : b&b
    (même flot que l'oracle `regref.certify_slab`, seul le certifieur change) →
    **46 feuilles, 38 collision (UP 12 / DOWN 12 / MID 14), 8 outside, 0 fail**,
    identique à E3. Parité t* par cellule **< 1e-7** vs oracle 2D (cas `unbounded`
    inclus). Les 2 faces z extrudées sont esclaves (z=0), la marge vient des faces x/y.
  - **Exit #2** — **3-DOF spatial minimal** (chaîne révolute générique 3R, back-end
    **sympy**, sans réseau) : lien dans une boîte obstacle → **certifié (t=0.079)** ;
    sur **1e5 échantillons** de la cellule, le point témoin est **toujours dans
    l'obstacle (0 violation)** ⟹ aucun point libre.
  - **Gel du signe de Putinar** (rule 2) sur le nouveau témoin : sur prémisse
    réellement fausse (UP rétréci, cellule s1∈[−0.125,0]×s2∈[0.875,1], 4 configs
    libres), `g − μT` refuse (t=−0.039), `g + μT` certifie **faussement** (t=+0.029).
  - **Contrôles négatifs (soundness)** : E3 obstacles rétrécis 30 % → b&b **refuse**
    (feuilles FAIL) ; 3-DOF obstacle rétréci ×0.5 → témoin **refuse** (t=−0.015) ET
    188 configs libres trouvées (prémisse fausse confirmée).
  - **Isolation back-end** prouvée : un second solveur indépendant (`scipy.linprog`,
    HiGHS) sur le **même** `WitnessLP` donne le même t* (< 1e-6).
  - λ quadratique certifie aussi ; `Polytope.box` et bases de degré testées.
- `make test` complet : **65 passed** (43 régression + 8 ratfk + 14 témoin), 100 s,
  mêmes 5 warnings Clarabel bénins.

**Décisions** :
- **K sommets explicites avec Σλ_k≡1, λ_k≥0** (au lieu du `0≤λ≤1` scalaire de l'oracle
  E3) : la version K=2 redonne exactement le segment x=p1+λ(p2−p1) → parité E3 exacte ;
  généralise au corps convexe quelconque (enveloppe à K sommets).
- **D^p = D (p=1)** : sommets sur dénominateur commun unique D du link ; g_j = b_j·D − a_jᵀX
  avec X = Σλ_k N_k numérateur sur D. Pas besoin de l'exposant p>1 du SPEC ici.
- **Σλ=1 en coefficients bruts** (identité polynomiale), λ≥0 et faces en **Bernstein**
  sur la cellule — même base que l'oracle, t* reproduit à 1e-7.
- **`_putinar_sign` test-only** (défaut −1 sound), à l'identique de l'oracle `regref` :
  le signe est figé par `test_witness_sign_is_frozen` ; production ne le touche jamais.
- **Embarquement 3D de S1** = sommets planaires à z=0 + boîtes extrudées z∈[−1,1] :
  les faces z restent esclaves (marge ≫ t*), donc certificat **identique** à E3.
- **Back-end b&b reste dans le test**, pas dans `engine.py` : le moteur n-dim est S3 ;
  le scaffold b&b du test reprend volontairement le flot de l'oracle pour isoler le
  témoin comme seule variable.
- **3-DOF spatial via sympy** (pas Drake) : pas de dépendance réseau dans la suite,
  vérité-terrain reproductible et seedée.

**Pièges rencontrés** :
- **Matrice homogène / `PolyLin.__add__`** : addition de PolyLin de degrés différents
  OK (slicing dans `zeros(n,d)`), mais bien **padder D et φ²** au degré de travail
  `DPAD = max(d_λ+d_N, 2·d_φ)` (=4 ici, comme E3) avant Bernstein — sinon recouvrement
  de tenseurs incohérent.
- **Faces esclaves** : les 2 faces z (z=0, D>0 ⟹ b·D≥1≫t*) ne lient jamais ; c'est ce
  qui garantit la parité E3 quand on embarque le planaire en 3D. Vérifié numériquement.
- **Contrôle négatif 3-DOF** : un rétrécissement ×0.5 de la boîte (autour du centre)
  ouvre 188 configs **entièrement** libres (segment hors boîte) sur grille 9³ — assez
  pour le contrôle ; testé f∈[0.3,0.6], tous donnent prémisse fausse + refus.

**Prochaine étape** : S3 — moteur branch-and-bound n-dim (`engine.py`) : généraliser
le moteur E3 à n dims, heuristique d'axe (frontière de dalle puis pire marge LP),
checkpoint/resume disque, parallélisme multiprocessing sur les feuilles, budget +
verdict UNDECIDED propre. Entrée : `cnp.witness.certify_cell_pair`. Le scaffold b&b
de `test_witness.py` documente le flot de référence (axe + test outside) à généraliser.

---

## 2026-06-10 — Revue de supervision S0-S2 (claude.ai) — **plan révisé v1.1**

**Verdict** : les trois sessions sont validées. Qualité au-dessus de l'attendu sur
quatre points : (1) test_putinar_sign démontre le faux certificat du mauvais signe
sur une instance à prémisse *réellement* fausse — c'est un test de soundness en
acte, pas un test de non-régression ; (2) la parité E3 est à valeurs égales
(t* < 1e-7 par cellule), pas seulement à verdict égal ; (3) l'isolation back-end
de S2 (WitnessLP + cross-check scipy/HiGHS < 1e-6) dérisque par anticipation la
partie conception de S8 ; (4) le choix S1 de la substitution demi-angle « maison »
(approche C) plutôt que le dénominateur Drake est exactement le bon arbitrage pour
l'auditabilité de verify.py — les dénominateurs réduits distincts de Drake auraient
rendu la vérification indépendante pénible.

**Points relevés (annotations, actions injectées dans le plan v1.1)** :
- [A1 → S4] **q_star** : l'implémentation est s = tan((q − q*)/2), la SPEC dit
  tan(θ/2). Divergence légitime (et plus générale) mais elle touche l'énoncé du
  théorème (wrap-around : |q_i − q*_i| < π), le schéma de certificat et verify.py.
  SPEC §2/§4 à amender en S4 ; q_star et les valeurs exactes des joints verrouillés
  entrent dans le certificat. Nouvelle règle 12 (anti-dérive de spec) pour que ce
  cas reste l'exception traitée, pas le précédent silencieux.
- [A2 → S3] **Garde Mosek automatisée** : le wheel Drake l'embarque en transitif ;
  « aucun import dans le cœur » doit être un test (sys.modules après import cnp +
  un solve), pas une vigilance humaine.
- [A3 → S3] **Temps de suite** : 63 → 77 → 100 s en trois sessions. `make test-fast`
  (< 30 s) pour le quotidien, `make test` complet requis aux sorties de session.
- [A4 → règle 13] **Skips réseau** : légitimes au quotidien, interdits sur les tests
  requis aux sorties de session (décompte exact passed/skipped/warnings au journal).
  Pré-télécharger les modèles Drake avant S9-S10.
- [A5 → S8] Les 5 warnings Clarabel « non supprimés par honnêteté » : bon réflexe ;
  l'élucidation (résoudre ou expliquer structurellement) devient une tâche S8.
- [A6, sans action] L'embarquement 3D de l'exit #1 (faces z esclaves) est un test de
  parité, pas un test de 3D-ité — c'est l'exit #2 (3-DOF spatial, 1e5 échantillons,
  0 violation du témoin) qui porte la validation spatiale. Couverture jugée
  suffisante pour S2.
- [A7, demande produit] **Validation visuelle humaine** : à la demande de Stéphane,
  protocole formalisé (règle 11, points [V1]-[V7] dans le plan) — la session
  s'arrête, donne la commande exacte, la checklist de ce qu'il faut regarder et le
  critère binaire, puis attend « VALIDÉ S<X>-V<k> ». Portée explicite : intention
  et conception seulement ; jamais la soundness (l'œil rate les micro-canaux,
  leçon E3). `cnp show` avancé de S11 à S6 pour servir ces validations.

**Prochaine étape** : S3 — moteur b&b n-dim, selon CLAUDE.md v1.1 (tâches 1-6,
validation V1 incluse).

---

## 2026-06-11 — S3 (Claude Code) — Moteur b&b n-dim (**code vert, V1 en attente**)

**Fait** :
- S2 re-vérifié vert avant démarrage (65 passed, 100 s).
- `src/cnp/engine.py` : branch-and-bound **n-dim** générique. `Problem` (box, phi,
  delta, `Pair`s, lam_degree, tol, max_depth), `Budget`, `EngineResult`
  (verdict PROOF/UNDECIDED, leaves, failed exportées, stats). Test outside par
  Bernstein de φ (`cell_outside_slab`, ré-exprimé via `cnp.polylin`, identique à
  l'oracle). Verdict **UNDECIDED** propre (jamais « infaisable ») sur budget
  (temps/feuilles) ou profondeur épuisée, cellules ouvertes exportées.
- **Heuristiques d'axe** : dalle-d'abord (split qui pousse un enfant hors dalle),
  puis fallback `axis="oracle"` (axe le plus large = choix de l'oracle ⇒ partition
  E3/E4 identique) ou `axis="margin"` (pire marge LP).
- **Parallélisme = work-queue dynamique** (défaut `n_workers>1`) : les workers
  partagent une file ; quand une cellule se découpe, ses **deux enfants repartent
  dans la file**, donc même un sous-arbre lourd s'étale sur tous les cœurs. L'arbre
  exploré est l'arbre déterministe du serial ⇒ **certificat octet-identique au
  serial, zéro inflation** (`test_workqueue_matches_serial`).
- **Checkpoint/resume** : chemin *frontier* (pré-découpe uniforme déterministe en
  2^d sous-cellules, chaque sous-arbre écrit atomiquement `done/<i>.json` via
  tmp+`os.replace`+fsync). `meta.json` à empreinte SHA : reprise refusée si le
  problème diffère (soundness). `test_resume_after_kill_same_certificate` lance un
  fils, le **SIGKILL en cours de run**, reprend, et obtient le même certificat.
- **Backend HiGHS par défaut** (`witness.HighsBackend`, scipy.linprog) : reproduit
  E3=46/E4=78 **exactement** (t* = CLARABEL < 1e-6, aucun flip à tol=1e-6), plus
  rapide (pas de compile cvxpy), et **mosek-free** (voir piège). cvxpy reste dispo
  en `backend=` pour cross-check.
- **Garde Mosek** (`tests/test_mosek_guard.py`, 3 tests, en **sous-process frais**) :
  import du cœur sans mosek/cvxpy ; solve par défaut (HiGHS) sans mosek ; + 1 test
  qui **documente** que le backend cvxpy, lui, réveille mosek.
- **Figures** : `scripts/make_figures.py` + `make figures` → `benchmarks/figures/
  partition_{E3,E4}.png` (panneau vérité-terrain + partition certifiée colorée par
  paire). Adaptateur de scènes DRY `tests/eng_scenes.py` (l'oracle `regref` reste
  intact).
- **Makefile** : `make test-fast` (`-m "not slow"`, **33 passed en 4.95 s**),
  `make test-slow`, `make figures`. Marqueurs `slow` posés sur les rejouages lourds
  (exp12 SOS 28 s, exp34 34 s, ratfk iiwa ~14 s, contrôle négatif témoin 37 s).
- `make test` complet : **82 passed, 0 skipped, 25 warnings, 130 s**
  (65 régression + 14 engine + 3 garde Mosek).

**Décisions** :
- **Work-queue plutôt que frontier statique pour le parallélisme.** Une pré-découpe
  statique de la dalle (fine) ne donne qu'une poignée de cellules *lourdes* → un
  worker hérite d'un gros sous-arbre, speedup plafonné ~2×. Mesuré honnêtement :
  round-robin ~1.4-1.9×, découpe tangente-à-la-dalle 0.16× (re-isole la dalle dans
  chaque colonne → explosion à 154 feuilles), gradient-d'abord 1.1× (explosion à
  1042 feuilles). Le work-queue **3.56× (dup=20) / 3.68× (dup=30)** sur 8 workers,
  10 cœurs, sans inflation. Le chemin frontier est **conservé** mais réservé au
  checkpoint/resume (déterministe, reprenable).
- **`start_method="fork"` pour le work-queue.** Sûr ici car **le parent ne résout
  aucun LP** (les workers possèdent tout le calcul cvxpy/BLAS) ⇒ aucun thread de lib
  vivant au fork ; et fork évite le ré-import cvxpy par worker qui écrase « spawn »
  à ~1.4-1.7×. Surchargeable (`start_method="spawn"`).
- **HiGHS = défaut du moteur** (pas cvxpy). Triple gain : mosek-free (règle 3),
  rapide, workers fork instantanés. L'isolation back-end de S2 (WitnessLP
  solveur-agnostique) rend ça gratuit ; c'est aussi la direction S8 (highspy direct),
  avancée ici par nécessité règle 3. cvxpy/CLARABEL reste le solveur de l'oracle
  `regref` (la reproduction 46/78 est vérifiée contre lui).
- **`axis="oracle"` reste le défaut** (reproduction exacte = critère de sortie). La
  margin est l'enhancement S3, journalisée comme « écart » (voir ci-dessous).

**Pièges rencontrés** :
- **cvxpy réveille mosek à l'import.** `import cvxpy` énumère tous les solveurs
  installés, dont le mosek transitif du wheel Drake — alors qu'on ne résout qu'en
  CLARABEL. Donc la garantie règle 3 (« aucun Mosek dans le chemin critique »)
  **impose d'éviter cvxpy** sur le chemin critique : d'où HiGHS par défaut. Le cœur
  (`import cnp.engine/witness`) n'importe PAS cvxpy (lazy dans le backend) ⇒ import
  cœur mosek-free. Garde automatisée à 3 volets, en sous-process frais (la pollution
  inter-tests masquait la régression sinon).
- **Heuristique margin = piège de coût, pas de soundness.** Premières variantes
  désastreuses : worst-margin par point de contrôle Bernstein et minimax 1-pas →
  **E4 UNDECIDED (263 FAIL), boucle ~10 min**. La bonne formulation est le lookahead
  **relais** (max de la marge du meilleur enfant : carve une cellule certifiable,
  récurse le reste) → certifie E3 (54 feuilles) **et** E4 (56 feuilles, < oracle 78).
  Écart journalisé : margin ≠ oracle en nombre de feuilles, jamais en soundness
  (rule 9). `axis="oracle"` reproduit 46/78 à l'identique.
- **`multiprocessing` exige un guard `__main__`.** Mes scripts de mesure appelaient
  `solve(n_workers>1)` au niveau module sans guard → sous spawn chaque worker
  re-exécute le script → explosion récursive de process / deadlock (10 min muets).
  Bug de script, pas du moteur (cibles du pool au niveau module = picklables).
- **`fork()` multi-threaded** : 20 `DeprecationWarning` macOS « use of fork() may
  lead to deadlocks ». Non observé (suite complète verte, work-queue déterministe,
  resume OK) ; **non supprimé** par honnêteté (comme les 5 Clarabel). Mitigation
  dispo : `start_method="spawn"` (sûr, ~1.5×). À reconsidérer en S8 (highspy direct
  ⇒ workers mono-thread, fork sûr).
- **Mesures de speedup faussées par la charge** : machine de bureau partagée
  (windowserver, VM, 9 users) + mes process résiduels → une mesure serial à 982 s
  (contention). Toujours mesurer process unique, foreground. Test durci (meilleur
  de 2 runs parallèles) contre les à-coups du scheduler.

**Décompte exact (sortie de session)** : `make test` = **82 passed, 0 skipped,
25 warnings, 130 s** (20 fork-deprecation + 5 Clarabel, tous documentés).
`make test-fast` = 33 passed, 49 deselected, 4.95 s.

**Critères de sortie S3** : E3/E4 via le moteur = oracle (46/78, mode oracle) ✓ ;
resume kill-9 même certificat ✓ ; speedup 8 cœurs **3.56×** ✓ ; garde Mosek verte ✓ ;
décompte exact journalisé ✓ ; **V1 VALIDÉE par Stéphane (« VALIDÉ S3-V1 »)** ✓.
**S3 vert, tous critères acquis.**

- [A11 → S11] **Annotation produit (Stéphane, à la validation V1)** : sur le panneau
  partition (b), **rogner/hachurer les feuilles slab-aware hors-dalle** (une feuille
  certifiée n'est en collision que sur sa portion ∩ dalle, pas sur toute la cellule)
  et **tracer la frontière de dalle** {|φ|=δ}. À faire dans `viz.py`/`make_figures`
  en S11 (figures prêt-papier, [V7]). Ne change rien à la soundness — lisibilité.

**Prochaine étape** : S4 — certificat JSON + verify.py exact (amender SPEC §2/§4 :
q_star, D par link, p=1 ; substitution demi-angle maison ré-implémentée). NB pour S4 :
le moteur émet déjà `partition_records()` (cell/status/pair/margin) — base du champ
`leaves` du certificat. NB pour S8 : HiGHS est déjà le défaut du moteur (avance la
tâche back-end direct ; reste highspy sans scipy + warnings Clarabel à élucider).

## 2026-06-11 — Revue de supervision S3 (claude.ai) — **CLAUDE.md v1.2**

**Verdict** : S3 validée sur le fond ; V1 en attente côté Stéphane (figures
prêtes). Trois points au-dessus de l'attendu : (1) work-queue parallèle à
certificat octet-identique au serial, avec mesure honnête des alternatives
écartées (round-robin 1.4-1.9×, tangente 0.16× + explosion, gradient 1.1×) —
3.56×/8 workers sans inflation ; (2) découverte que `import cvxpy` réveille le
mosek transitif du wheel Drake ⟹ HiGHS par défaut, garde 3 volets en
sous-process frais (la pollution inter-tests masquait la régression) ;
(3) resume à empreinte SHA qui refuse la reprise si le problème diffère.

**Annotations (intégrées à CLAUDE.md v1.2)** :
- [A8 → règle 11] La validation visuelle ne bloque jamais le commit du code :
  commit immédiat « S<X> — V<k> pending », validation = micro-commit de
  clôture. Une V en attente bloque la session suivante, pas la sauvegarde.
- [A9 → S8] Re-scope : défaut HiGHS déjà acté (S3, scipy.linprog) ; S8 =
  highspy direct + warm starts, sparsité, dims passives, degré adaptatif,
  fork/spawn à ré-évaluer workers mono-thread, solder 20 warnings fork +
  5 Clarabel.
- [A10 → S9] Heuristique d'axe à trancher sur données : margin-relais bat
  l'oracle sur E4 (56 vs 78 feuilles), perd sur E3 (54 vs 46) — levier
  anti-explosion n°1 pour G2'. Micro-tâche ajoutée : mesurer feuilles(n) à
  n = 3,4,5,6 joints sur la même scène (exposant empirique du modèle de coût).

**V1 — instructions transmises à Stéphane** : `make figures`, ouvrir
`benchmarks/figures/partition_E3.png` et `partition_E4.png` ; vérifier
(1) bande dalle continue ★→✚ sans cellule FAIL noire, (2) relais des trois
couleurs de paires cohérent avec la vérité-terrain, (3) raffinement concentré
aux frontières de dalle et zones de relais. Répondre « VALIDÉ S3-V1 » à Code,
qui committe (rule 11 amendée) et ouvre S4.

**Prochaine étape** : V1, micro-commit, puis S4 — certificat JSON + verify.py
exact (le schéma §4 est pré-amendé dans SPEC v1.1, S4 le finalise).

---

## 2026-06-11 — S4 (Claude Code) — Certificat exact + vérificateur indépendant

**Fait** :
- S3 re-vérifié vert avant démarrage (82 passed, 0 skip, 130 s).
- `src/cnp/certificate.py` (GÉNÉRATEUR) : modèle `Scene` exact-rationnel (robot
  révolute, obstacles H-rep, φ, δ, boîte P, start/goal en espace-s), `scene_to_problem`
  (construit le `engine.Problem` flottant via `cnp.ratfk.SympyRatFK`), `make_certificate`
  (sérialise un JSON 100 % rationnels exacts), `certify`, `save/load`. Schéma SPEC §4
  finalisé.
- `src/cnp/verify.py` (VÉRIFICATEUR, **SACRÉ**) : **498 lignes**, `fractions.Fraction`
  uniquement, **zéro import** du générateur (audit AST en test). Ré-implémente
  *from scratch* : algèbre tensorielle creuse + transformée de Bernstein exacte ; FK
  demi-angle révolute indépendante (accumulation de transfos homogènes 4×4 en
  tenseurs Fraction) ; les 5 contrôles SPEC §2 — (0) hypothèses, (i) φ(s_start)<−δ ∧
  φ(s_goal)>+δ STRICT, (ii) pavage exact de P (cover disjoint re-dérivé par récursion
  sur les bissections au milieu — l'arbre n'est pas stocké), (iii) feuilles outside
  (Bernstein φ±δ ≥ 0), (iv) feuilles collision (Σλ_k ≡ 1 exact, Bernstein(λ_k) ≥ 0,
  μ_j ≥ 0, Bernstein(g_j − μ_j·T) ≥ 0). **Le vérificateur FORME lui-même g − μT** ⟹ un
  certificat ne peut pas y glisser le signe unsound g + μT (règle 2).
- `src/cnp/cli.py` + `__main__.py` + `[project.scripts] cnp = cnp.cli:main` :
  `cnp verify cert.json` (et `python -m cnp verify`) → PROOF (exit 0) / UNDECIDED
  (exit 1), verdict honnête (règles 5/6). `scene` en argument optionnel (S6).
- `tests/cert_scenes.py` : builders `Scene` E3/E4 (pendant S4 de `eng_scenes.py`).
- `tests/test_certificate.py` (7 tests) : round-trip E3 (**46 feuilles** 38c/8o,
  test-fast ~0.7 s) et E4 (**78 feuilles** 76c, @slow) reproduisant l'oracle, tous deux
  vérifiés exactement ; certificat 100 % rationnels (pas de float qui fuit) ; save/load ;
  refus d'un résultat UNDECIDED ; **audit verify** : < 500 lignes + imports stdlib only.
- `tests/test_verify.py` (28 tests) : **26 mutations adversariales** (μ<0, μ énorme, Σλ≠1,
  λ mis à l'échelle/négatif, coupe décalée, feuille manquante=trou, feuille dupliquée=
  recouvrement, q*≠0, δ×20, δ<0, start/goal du mauvais côté, signe φ, b/A d'obstacle,
  sommet de coque, longueur de link, body_link, collision↔outside relabellisées,
  obstacle permuté, theorem/substitution corrompus, boîte rétrécie, cellule hors-boîte)
  **toutes rejetées** ; le vérificateur ne lève jamais sur entrée corrompue (renvoie
  `(False, raison)`).
- `make test` complet : **117 passed, 0 skipped, 25 warnings, 135 s** (82 + 35 S4).
  `make test-fast` = **67 passed, 50 deselected, 7.77 s**. Garde Mosek verte (3/3).

**Décisions** :
- **FK générateur via `SympyRatFK`, FK vérificateur ré-implémentée en Fraction.**
  Vérifié : le bras planaire 2R exprimé en chaîne révolute z-axe reproduit EXACTEMENT
  (diff 0.0) les tenseurs `regref.fk_tensors()`, donc le moteur via le modèle `Scene`
  redonne 46/78. La duplication générateur↔vérificateur est le but (SPEC §5), pas un
  défaut : deux chemins de code indépendants qui doivent CONCORDER.
- **Pavage prouvé sans stocker l'arbre.** Le moteur n'émet qu'une liste plate de
  feuilles ; plutôt que modifier `engine.py` (⟹ re-run adversarial, règle 1), verify
  RECONSTRUIT le pavage par récursion sur les bissections au milieu (le moteur ne coupe
  qu'au milieu ⟹ exact). Prouve trou ET recouvrement (mutations dédiées le confirment).
- **Arrondi des multiplicateurs = mélange-au-barycentre + `limit_denominator`.** Le
  min des points de contrôle Bernstein de λ est un **zéro STRUCTUREL** (le témoin est
  sur un sommet du corps) ; l'arrondi indépendant des coeffs le rendait légèrement
  négatif. Fix : λ ← (1−α)λ + α·barycentre (le barycentre somme à 1 ⟹ Σλ≡1 préservé ;
  les zéros remontent à α/K>0), α ≪ marge de face (0.0063 sur E3) ⟹ faces restent > 0.
  Dernier sommet DÉRIVÉ par soustraction ⟹ Σλ≡1 exact par construction. max_den=1e6 :
  la poussière numérique (~1e-13) tombe sur 0, les marges (~1e-2) survivent.
- **Condition (i) en espace-s.** tan(θ/2) des angles de démo est irrationnel ⟹
  invérifiable en exact. On certifie entre deux configs RÉELLES d'images s_start,
  s_goal RATIONNELLES (q = q*+2·arctan(s)), test STRICT. Restriction de portée
  honnête (règle 6), SPEC §2 amendée.
- **Certificat auto-suffisant en S4** : il embarque la scène exacte (robot+obstacles)
  que verify recalcule ; le croisement avec un YAML externe est S6. Faire confiance à
  l'ÉNONCÉ du problème (géométrie, q*) ≠ faire confiance à la PREUVE (numérateurs, λ,
  μ, partition) — seule la preuve est recalculée/contrôlée.
- **`cnp verify` n'utilise pas cvxpy** (verify = stdlib pur) ; `make_certificate`
  re-résout via le backend HiGHS du moteur (mosek-free). La garde Mosek reste verte.

**Pièges rencontrés** :
- **q* est absorbé dans s pour les joints débloqués.** Changer q* dans le cert ne
  changeait RIEN au verdict (les numérateurs FK en s n'en dépendent pas). Ré-injecter
  q*≠0 exige Rot(q*_i) ⟹ cos/sin(q*_i) rationnels (irrationnels en général). Choix
  honnête : le vérificateur exact planaire n'admet que **q*=0** et REFUSE q*≠0 (règle 5 :
  ne jamais « vérifier » ce qu'on ne peut pas recalculer). C'est ce refus qui rend la
  mutation q* rejetable. q*≠0 viendra avec Drake (S9+, cos/sin verrouillés rationnels).
  NB : `SympyRatFK` ignore aussi le q* des joints débloqués — latent, sans effet à
  q*=0 (S4), à traiter pour le chemin sympy si q*≠0 un jour ; Drake le gère déjà.
- **`link_lengths[1]` n'entre PAS dans la FK de `body_link=1`** : seule
  `link_lengths[0]` (offset du joint 1) compte ; la longueur du link distal est portée
  par `hull_vertices`. Première mutation « link_length » (indice 1) passait à tort ;
  corrigée à l'indice 0.
- **Bernstein au MÊME degré que le générateur** (DPAD = max(d_λ+2, 2·d_φ) = 4 en
  affine) : un degré plus bas donnerait une borne plus lâche ⟹ FAUX rejet d'un cert
  valide (la soundness, elle, tiendrait). verify calcule au degré du générateur ⟹
  décision d'acceptation identique.
- **Audit d'imports par regex piégeux** : `^\s*from` matchait « from scratch » en
  prose. Remplacé par un parcours **AST** (Import/ImportFrom) — robuste.
- **verify.py a frôlé 500 lignes** (516 → 498) : suppression des helpers Bernstein
  min/max inutilisés et condensation des commentaires. La limite « < 500 » (règle 4)
  est testée (`test_verify_under_500_lines`).

**Décompte exact (sortie de session)** : `make test` = **117 passed, 0 skipped,
25 warnings, 135 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 67 passed, 50 deselected, 7.77 s.

**Critères de sortie S4** : round-trip generate→verify OK sur E3 et E4 ✓ ;
≥ 20 certificats corrompus rejetés (**26**) ✓ ; audit imports de verify (stdlib only,
< 500 lignes) ✓ ; SPEC §2/§4/§5 amendée (règle 12) ✓ ; décompte exact journalisé ✓.
Pas de point [V*] en S4 (la prochaine validation visuelle est V2 en S5). **S4 vert.**

**Prochaine étape** : S5 — pipeline φ (`phifit.py`) : échantillonnage C_free/C_obs
(collision checker Drake, seedé), fit SVM + approx polynomiale deg ≤2/var, sélection δ
auto, boucle de retry. **[V2]** : figure « C-space + lignes de niveau φ + dalle » pour
E4-planaire puis 3-DOF. NB S5 : `certificate.Scene` + `verify` attendent un φ rationnel
et des obstacles H-rep exacts ; phifit devra rationaliser son φ appris (cf. `e4_scene`
qui rationalise à 1e-6). NB S6 : brancher `cnp verify cert scene.yaml` (croisement scène
externe), et `cnp certify`.

## 2026-06-11 — Revue de supervision S4 (claude.ai) — **CLAUDE.md v1.3**

**Verdict** : S4 validée — la session la plus structurante du projet. Trois
points au-dessus de l'attendu : (1) le vérificateur **forme lui-même g − μT**
(le certificat ne transporte que λ et μ) ⟹ le signe unsound devient
structurellement impossible à glisser dans une preuve, plus seulement testé ;
(2) pavage prouvé par RECONSTRUCTION (récursion sur bissections au milieu)
plutôt qu'en modifiant engine.py — règle 1 respectée, trou ET recouvrement
prouvés ; (3) refus honnête de q*≠0 par le vérificateur planaire plutôt qu'une
fausse vérification (règle 5), et condition (i) restreinte aux s rationnels
(SPEC amendée). 26 mutations rejetées, audit AST, 498 lignes, 117 tests 0 skip.

**Annotations (intégrées à CLAUDE.md v1.3)** :
- [A12 → ouverture S5] `SympyRatFK` IGNORE silencieusement q* des joints
  débloqués (« sans effet à q*=0 » — vrai aujourd'hui, mine pour S9). Garde
  bruyante exigée : ValueError si q*≠0 sur le chemin sympy, + 1 test.
- [A13 → ouverture S5] L'arrondi mélange-au-barycentre est calibré en dur sur
  la marge d'E3 (α=0.0063 vs marge ~1e-2). À 7-DOF les marges visent ~1e-3 :
  α doit être adaptatif (fraction de la marge mesurée par feuille) + boucle de
  re-résolution si verify rejette après arrondi (promesse SPEC §4) + test à
  marge fine.
- [A14 → règle 9, contrat] La reconstruction du pavage par verify suppose que
  le moteur ne coupe QU'AU MILIEU. Désormais contrat explicite engine↔verify :
  changer l'un = amender l'autre + SPEC dans le même commit. Corollaire
  documenté : verify calcule Bernstein au même degré que le générateur (plus
  bas = faux rejets).
- [A11 → S11, issu de V1] Figures de publication : rogner/hachurer la partie
  hors-dalle des feuilles slab-aware et tracer la frontière de dalle sur le
  panneau partition (les grandes feuilles E4 débordant en zone libre sont
  sound — la couleur ne vaut que sur cellule∩dalle — mais piégeuses pour un
  lecteur).

**V1 (clôturée)** : figures partition_E3/E4 validées par Stéphane sur les trois
points de la checklist (continuité de dalle sans FAIL, relais des paires
conforme à la vérité-terrain, raffinement concentré aux frontières/relais).

**Prochaine étape** : S5 — tâches d'ouverture A12+A13 (< 30 min), puis pipeline
φ (échantillonnage seedé, fit SVM, approximation polynomiale RATIONALISÉE,
δ auto avec s_start/s_goal rationnels, boucle de retry). V2 en fin de session.

---

## 2026-06-11 — S5 (Claude Code) — Pipeline φ (**code vert, V2 en attente**)

**Fait** :
- S4 re-vérifié vert avant démarrage (117 passed, 0 skip, 135 s) ; au passage,
  réconciliation des docs de la revue S4 (CLAUDE.md v1.3 incohérent : le bloc
  A14/contrat était ajouté mais l'« État d'avancement » avait été reverté en
  pré-S4 ; header v1.2→v1.3 ; commit doc séparé avant S5).
- **Gardes d'ouverture** :
  - **A12** — `SympyRatFK` lève désormais `ValueError` si q*≠0 sur un joint
    **débloqué** (il ne pose pas la pré-rotation Rot(axe, q*) ⟹ q* serait ignoré
    en silence, FK fausse). Joints **verrouillés** : q* replié dans cos/sin
    numériques, q*≠0 toléré (testé). Drake gère q*≠0 nativement (inchangé).
  - **A13** — l'arrondi λ mélange-au-barycentre devient **adaptatif** : α =
    fraction de la marge de face MESURÉE par feuille (`(0.2,0.05,0.01,0.002)·marge`
    au lieu de constantes calibrées sur E3). `make_certificate` exécute le
    **vérificateur exact** et **escalade max_den** jusqu'à acceptation (promesse
    SPEC §4 « re-résolution »), sinon lève honnêtement. Test à marge fine
    (δ=3/40 ⟹ min marge ~1.9e-3) round-trip OK.
- **`src/cnp/phifit.py`** (pipeline φ) : échantillonnage seedé de la s-boîte +
  étiquetage par un **oracle de collision GÉNÉRIQUE passé en argument** (robot-
  agnostique : le checker Drake est branché aux scènes Drake en S9+) ; deux fits
  sur la base monomiale deg ≤2/var — **SVM linéaire** (`LinearSVC` sur les points
  LIBRES étiquetés par côté start/goal ⟹ la fonction de décision est une barrière
  dont le zéro traverse l'obstacle) et **moindres carrés** à cible signée (recette
  E4 généralisée n-dim) ; **δ auto** = fraction (`safety`) d'un bas quantile de
  |φ| sur les libres (marge du libre le plus proche), plafonnée par ½·borne de
  condition (i) — δ PETIT (dalle fine ⊆ collision) ; **rationalisation** exacte +
  ré-assertion de (i) en Fraction ; **boucle propose→certifie→raffine** : sur
  UNDECIDED, on pénalise (×8) les échantillons libres tombant dans les cellules en
  échec exportées par le moteur ET on amincit la dalle (safety/2), refit.
- **E4-planaire via le pipeline complet** : φ trouvé automatiquement (sans hint),
  certifié end-to-end et **vérifié en exact** (lstsq : 76 feuilles, δ≈0.264 ;
  svm : 76 feuilles, δ≈0.505 ; oracle hand-tuné = 78). Les deux passent
  `verify.verify`.
- **Scène 3-DOF spatiale** (chaîne 3R sympy axes z,y,y, la « scène de S2 ») :
  mur frontal **piégeant le point PROXIMAL du segment** (j2-origine, fonction de
  s0,s1 seulement) sur une bande de lacet de base ⟹ tout chemin franchissant s0=0
  est en collision pour TOUT tangage = **vraie déconnexion**. Le pipeline trouve
  φ≈s0 automatiquement → **moteur-PROOF** (lstsq 9 feuilles après 1 retry ;
  svm 8) ; **cond. (i) exacte** OK ; **0 point libre dans la dalle sur 300k
  échantillons** (contrôle vérité-terrain, style S2 exit #2). Le vérificateur
  exact reste planaire jusqu'à S9 (décision actée avec Stéphane : fidélité au
  calendrier ; le 3-DOF est étiqueté « moteur-PROOF + échantillonnage », PAS
  « certifié » au sens règle 5).
- **Contrôle négatif (soundness)** : mur rétréci ×0.4 ⟹ chemin libre autour ⟹ le
  pipeline ne renvoie **jamais PROOF** (UNDECIDED sur budget).
- **Figures V2** (`scripts/make_figures.py` étendu, `phi_scenes.py` DRY) :
  `benchmarks/figures/phi_E4.png` et `phi_3dof.png` — C-space échantillonné
  (gris=collision) + lignes de niveau de φ (bleu) + dalle {|φ|≤δ} (or) +
  start (★) / goal (✚).
- `make test` : **130 passed, 0 skipped, 25 warnings, 195 s** (117 + 2 A12 +
  2 A13 + 9 phifit). `make test-fast` = **76 passed, 54 deselected, 17.4 s**.

**Décisions** :
- **Oracle de collision en argument, pas Drake en dur** (amendé SPEC §3, règle 12).
  Garde phifit robot-agnostique et sans réseau (chemin planaire = regref, chemin
  3-DOF = sympy 3R), cohérent avec la décision S2. Drake = scènes S9+.
- **δ petit = bon** : la dalle fine ⊆ collision est plus facile à certifier (et
  moins de feuilles) ; le piège initial était δ=0.5·borne (≈0.6 sur E4) qui
  avalait du libre → UNDECIDED à >1000 feuilles. La sélection finale prend une
  fraction de la marge du libre le plus proche (quantile), pas 0.5·borne.
- **SVM sur les LIBRES étiquetés par côté** (pas free/collision) : un SVM
  free/collision donnerait la frontière de l'obstacle, pas une barrière le
  traversant. Étiqueter les libres start-côté/goal-côté met le séparateur DANS le
  gap de collision. Les deux fits livrés (svm + lstsq) ; lstsq reproduit la
  recette E4.
- **Disconnexion 3-DOF par piégeage proximal** : le point proximal du segment ne
  dépend pas de s2 ⟹ une bande pleine sur (s1,s2) est garantie, donc une vraie
  déconnexion topologique (vs un mur frontal que le bras contourne en tangage —
  testé, échoue : 64/225 libres à s0=0).
- **`make_certificate(verify_loop=True)` par défaut** : le générateur s'auto-
  vérifie à l'exact et escalade max_den (A13). Coût doublé par cert, accepté
  (c'est la garantie SPEC §4).

**Pièges rencontrés** :
- **δ=0.5·borne est le mauvais réflexe** (hérité de E4 où la borne était évaluée à
  ±0.577 ; ici start/goal à ±0.9 ⟹ borne ~1.1, δ~0.55 trop épais). Diagnostic par
  balayage de δ : 0.03–0.3 PROOF (14–76 feuilles), 0.5 UNDECIDED (549 feuilles).
- **Mur frontal contournable** : un bras 3R à joint distal libre se rétracte/tangue
  pour éviter un obstacle frontal (même haut). Il faut piéger une partie **proximale**
  (indépendante du joint distal) pour garantir une bande pleine. Plusieurs géométries
  écartées avant le piège proximal (collision frac 0.07→0.23→0.37).
- **Overflow Fraction × numpy.int64** dans un script de debug : `tuple(e)` issu de
  `np.argwhere` donne des exposants numpy ⟹ `Fraction ** np.int64` déclenche un
  overflow scalaire silencieux. Le pipeline convertit en `int` natif (`tuple(int(x)
  for x in e)`) — pas affecté ; piège de debug seulement.
- **Colormap inversée** dans la figure V2 (Greys : 0=blanc) : première version avait
  gris=libre alors que le titre disait gris=collision. Corrigé (collision→0.55).
- **test-fast trop lent** (52 s) : le contrôle négatif 3-DOF (moteur jusqu'à 400
  feuilles sur dalle libre) coûtait 41 s. Budget réduit à 80 feuilles + 1 retry
  (UNDECIDED atteint vite de toute façon) ⟹ test-fast 17.4 s.

**Décompte exact (sortie de session)** : `make test` = **130 passed, 0 skipped,
25 warnings, 195 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 76 passed, 54 deselected, 17.4 s.

**Critères de sortie S5** : E4-planaire reproduit via le pipeline complet
(generate→verify exact) ✓ ; 3-DOF spatial : φ auto + certifié moteur-PROOF +
0 point libre / 300k (étiqueté honnêtement, verify exact = S9) ✓ ; gardes A12/A13
✓ ; SPEC §3 amendée (règle 12) ✓ ; décompte journalisé ✓. **V2 VALIDÉE par
Stéphane (« VALIDÉ S5-V2 »)** sur les trois points (dalle or ⊆ collision sur les
deux figures et les deux coupes du 3-DOF ; start/goal de part et d'autre dans le
libre ; bande franche non dégénérée). Code commité « S5 — V2 pending » (b07519c),
clôture par micro-commit. **S5 vert, tous critères acquis.**

**Prochaine étape** : V2, micro-commit de clôture, puis S6 — scenes.py + parser
YAML + `cnp show` Meshcat + `cnp certify` bout-en-bout + suite adversariale
initiale (porte G1'). NB S6 : `phi_scenes.py` (oracle + build_problem) est la base
du branchement scène→pipeline ; le 3-DOF spatial attend `spatial_revolute` dans
certificate+verify (S9) pour une certification exacte.

## 2026-06-11 — Revue de supervision S5 (claude.ai) — **annotations A15-A17, nouveau circuit doc**

**Mea culpa (incident doc v1.3)** : l'incohérence réconciliée en ouverture de S5
venait du superviseur, pas de Code. Le patch v1.3 livré depuis claude.ai
s'appliquait en deux scripts ; le premier a avorté sans écrire (tout-ou-rien),
le second n'a écrit que le bloc règle 9 — fichier livré à moitié patché, sans
vérification finale avant remise. La réconciliation de Code depuis le journal
était la bonne réaction (trace faisant foi, commit doc séparé, signalement).
Deux résidus que Code ne pouvait pas deviner restent à appliquer (diffs D1-D2
ci-dessous).

**Verdict S5** : validée. Trois points au-dessus de l'attendu :
(1) A13 implémentée mieux que demandé — `make_certificate(verify_loop=True)`
par défaut : auto-vérification exacte + escalade max_den, promesse SPEC §4
tenue en standard ; (2) insight SVM : étiqueter les LIBRES par côté start/goal
(et non libre/collision) place le séparateur DANS le gap de collision — bonne
formulation du problème de barrière ; (3) déconnexion 3-DOF par piégeage
PROXIMAL, géométries écartées documentées chiffres à l'appui (mur frontal
contourné en tangage : 64/225 libres). Étiquetage honnête « moteur-PROOF, pas
certifié » (règle 5 appliquée spontanément). Trouvaille à retenir : δ PETIT est
le bon réflexe (dalle fine ⊆ collision ; balayage 0.03-0.3 PROOF vs 0.5
UNDECIDED 549 feuilles) — l'inverse de l'intuition « marge confortable ».
Nit de tenue de journal : le titre de l'entrée S5 dit « V2 en attente » alors
que la clôture dit « V2 VALIDÉE » — mettre le titre à jour au micro-commit de
clôture.

**Annotations** :
- [A15 — gouvernance CLAUDE.md] Code PEUT modifier CLAUDE.md pour :
  (a) réconcilier avec des décisions de supervision journalisées,
  (b) tenir l'« État d'avancement », (c) le changelog. Code ne modifie JAMAIS
  de sa propre initiative une règle, un critère de sortie ou une porte. Tout
  diff de CLAUDE.md est listé dans l'entrée de journal de la session.
  (→ devient la règle 14, diff D3.)
- [A16 — circuit de révision doc] Les revues de supervision ne livrent plus de
  fichiers CLAUDE.md entiers (risque de copie périmée, cause racine de
  l'incident) : elles livrent une entrée de journal + instructions de diff
  explicites, que Code applique au CLAUDE.md DU REPO en tâche d'ouverture de la
  session suivante. Le repo est l'unique source de vérité.
- [A17 — verdicts mécaniques] Trois statuts produit dès S6 (CLI, sorties,
  README) : PROOF (vérifié exact) ; ENGINE-PROOF (moteur OK, vérification
  exacte indisponible — ex. 3-DOF spatial avant S9, toujours affiché avec son
  avertissement) ; UNDECIDED. La règle 5 devient visible dans le produit.
  (→ diff D4.)

**Diffs à appliquer par Code en ouverture de S6 (CLAUDE.md du repo)** :
- D1 [résidu v1.3] Section S11, tâche figures : ajouter « **[A11, V1]** :
  rogner ou hachurer la partie hors-dalle des feuilles slab-aware et tracer la
  frontière de dalle sur le panneau partition (sans quoi un lecteur croit qu'on
  certifie de la collision en zone libre) ».
- D2 [cosmétique] En-tête du plan : « révisé v1.1 » → « tenu à jour (voir
  changelog) ».
- D3 [A15] Nouvelle règle 14 « Gouvernance de CLAUDE.md » : texte de
  l'annotation A15 ci-dessus.
- D4 [A17] Section S6, ajouter aux tâches CLI : « verdicts à trois statuts
  PROOF / ENGINE-PROOF / UNDECIDED (A17) ; ENGINE-PROOF toujours accompagné de
  son avertissement ; README et messages alignés (règles 5/6) ».
- D5 Header : version 1.4, ligne de changelog « v1.3→v1.4 (revue S5, A15-A17) :
  gouvernance CLAUDE.md (règle 14) ; circuit doc par diffs journalisés ;
  verdicts à trois statuts ; résidus v1.3 appliqués (A11→S11) ».

**Prochaine étape** : S6 — ouverture : appliquer D1-D5 (+ commit doc séparé),
puis scenes.py + YAML + `cnp show` + `cnp certify` + adversarial initial
(porte G1', validation V3).

---

## 2026-06-11 — S6 (Claude Code) — Scènes + CLI + adversarial (**V3 validée**)

**Fait** :
- **Ouverture** : diffs de revue S5 D1-D5 appliqués au CLAUDE.md du repo (circuit
  A16, repo = source de vérité), commit doc séparé (3904640) : règle 14
  (gouvernance CLAUDE.md, A15), verdicts à trois statuts dans la tâche S6 (A17),
  note figures slab-aware S11 (A11/D1), en-tête plan (D2), header v1.4 + changelog
  (D5). S5 re-vérifié vert avant démarrage (130 passed, 0 skip).
- **`src/cnp/scenes.py`** : parser YAML rationnel → `certificate.Scene` exact.
  Obstacles en **boîte axis-aligned (lo/hi par axe)** ou **H-rep brute (A,b)** ;
  enveloppe convexe du corps **extraite de la géométrie du link** (planaire =
  segment `[0,0,0]→[len,0,0]`) si `hull_vertices` absent ; budget (depth, leaves,
  temps, **heuristique d'axe**). `is_exactly_verifiable` (planaire q*=0),
  `scene_matches_cert` (cross-check scène↔cert, comparaison de rationnels en
  chaîne), `planar_collision_oracle` (oracle générique pour phifit/vérité-terrain),
  `build_problem` (dispatch planaire→certificate / spatial→ici).
- **`src/cnp/cli.py`** réécrit : `cnp certify <scene> [-o cert]` bout-en-bout
  (parse→build_problem→solve→make_certificate auto-vérifié→write) ; `cnp verify
  cert [scene]` (re-vérif exacte + cross-check scène externe optionnel) ; `cnp show
  <scene>` (Meshcat). **Verdicts à trois statuts (A17)** : PROOF (vérifié exact) /
  ENGINE-PROOF (moteur OK, vérif. exacte indisponible — TOUJOURS avec son
  avertissement) / UNDECIDED. Erreurs propres (exit 2).
- **`src/cnp/viz.py`** (minimal S6) : `show_scene` — bras planaire (squelette
  polyline + sphères aux joints) aux configs start ET goal dans un SEUL serveur
  Meshcat (bleu/vert) ; URL retournée. + `save_planar_figure` — **figure 2D vue de
  dessus** (dents en rectangles, poses du bras en polylignes épaisses), bien plus
  lisible que la 3D pour une scène planaire ; `cnp show --png` la produit, et
  `scripts/make_scene_figures.py` (dans `make figures`) génère deux figures :
  `scene_S2_peigne.png` (WORKSPACE — start/goal libres + 2 poses in-dalle, link
  médian pris dans MID puis UP, le relais) et `scene_S2_peigne_cspace.png`
  (**C-space (s0,s1), s2 passif** — `save_cspace_figure` : collision en gris, dalle
  en or, ★ start / ✚ goal ; un **mur de collision plein à s0≈0** sépare start
  (gauche) de goal (droite) ⟹ la figure « goal libre mais INATTEIGNABLE » que la
  V3 demandait). `show_scene` et l'oracle de collision (`collision_oracle`) gèrent
  aussi le **builtin spatial** : `cnp show scenes/S2b_spatial3.yaml` dessine le vrai
  robot 3R en 3D (poteau vertical + segment distal swingué gauche/goal-droite, mur
  en façade) et `scene_S2b_spatial_cspace.png` rejoue la même preuve visuelle en
  C-space spatial. **Mode `sweep`** (`cnp show --config sweep` + `save_sweep_figure`
  → `scene_S2b_spatial_sweep.png`) : éventail des poses interpolées start→goal,
  collisions en ROUGE — montre POURQUOI le mouvement direct est bloqué (le bras
  balaie le mur), complément du C-space qui montre que TOUT chemin l'est. (viz
  complet `cnp viz <cert>` = S11.)
- **Scènes** : `scenes/S1_relais.yaml` (E3, 46 feuilles, régression rapide),
  `scenes/S2_peigne.yaml` (**peigne 3-DOF planaire**), `scenes/S2b_spatial3.yaml`
  (3-DOF spatiale → ENGINE-PROOF).
- **G1' — S2-peigne 3-DOF certifié end-to-end** : `cnp certify scenes/S2_peigne.yaml`
  → PROOF, `cnp verify … scene` → OK (54 feuilles : 46 collision + 8 outside) +
  cross-check scène ; **0 point libre dans la dalle sur 300k échantillons**
  (vérité-terrain). Construction : E3 **relevé en 3-DOF par piégeage proximal**
  (le link MÉDIAN, fonction de s0,s1 seulement, est relayé par 3 dents ; joint
  distal s2 passif). Genuinement n=3, multi-paires, exactement vérifiable
  (planaire, q*=0).
- **`src/cnp/certificate.py`** : `Robot` reçoit un champ optionnel `joints`
  (builtin `spatial_revolute` côté moteur) ; sinon inchangé (verify ne lit jamais
  Robot). Schéma cert inchangé (spec_version 1.2).
- **Suite adversariale `tests/test_adversarial.py`** (zéro faux certificat, G1') :
  dents rétrécies ×0.7 (chemin libre) → moteur UNDECIDED, `make_certificate` lève ;
  **micro-canal** ×0.95 : grille grossière 11³ trouve **0 libre dans la dalle**
  (la grille est dupée) mais échantillonnage dense en trouve (prémisse réellement
  fausse) ET le moteur **REFUSE** (UNDECIDED) — le certificateur > la grille
  (règle 9) ; CLI refuse une prémisse fausse (exit 1, aucun cert écrit).
- **`tests/test_scenes.py`** (16 tests) : round-trip S1 reproduit l'oracle + vérifié ;
  peigne 3-DOF certifié+vérifié exact ; box≡hrep ; hull dérivé ; cross-check
  accepte/rejette (4 mutations) ; 5 scènes malformées lèvent proprement ; spatial
  → ENGINE-PROOF ; CLI certify→verify, ENGINE-PROOF spatial, rejet cross-check
  mauvaise scène ; helpers viz (positions joints + bornes boîte).
- `make test` complet : **149 passed, 0 skipped, 25 warnings, 184 s**
  (130 S5 + 16 scenes + 3 adversarial). `make test-fast` = **88 passed,
  61 deselected, 25.6 s**.

**Décisions** :
- **Peigne = E3 relevé par piégeage proximal** (pas une déconnexion distale).
  Une déconnexion 3-DOF pilotée par le joint DISTAL est défaite par la redondance
  (leçon S5 : « mur frontal contourné en tangage »). Le link médian (indépendant
  de s2) piégé sur une bande garantit une collision pour TOUT s2 → vraie
  déconnexion topologique dans la boîte 3D. Sound, peu coûteux, exactement
  vérifiable. Construction endorsée par la supervision S5.
- **`axis: margin` requis pour le peigne** : s2 est une dimension PASSIVE
  (collision/outside constants en s2) ; le défaut `oracle` (axe le plus large)
  gaspille la profondeur à découper s2 → 736 feuilles, 256 FAIL, UNDECIDED. Le
  lookahead-relais `margin` ne découpe pas la dimension passive → 54 feuilles,
  PROOF. L'heuristique ne touche jamais la soundness (règle 9) ; la mitigation
  « dims passives par intervalles » propre est S8 (SPEC §9.1). Le budget de scène
  porte donc `axis`.
- **Verdicts à trois statuts réels et testés (A17)** : ENGINE-PROOF n'est pas du
  code mort — le builtin `spatial_revolute` (chaîne 3R par joints offset/axe,
  géométrie de S5) est solvable par le moteur mais le vérificateur exact reste
  planaire jusqu'à S9 ⟹ `cnp certify scenes/S2b_spatial3.yaml` rend ENGINE-PROOF
  avec son avertissement. Rule 5 visible dans le produit.
- **φ baké, pas fité par cnp certify** : le hint φ rationnel est obligatoire dans
  la scène (le peigne = φ=s0 à la main, naturel pour un E3 relevé). Le fit
  automatique (phifit/S5) reste disponible hors-ligne pour produire le φ rationnel
  à baker ; testé sur le peigne (lstsq surajuste le bruit en s2 → φ=s0 à la main
  est le bon barrière). cnp certify reste déterministe.
- **Cross-check scène hors de verify.py** : `verify.py` reste SACRÉ (intouché,
  498 lignes, stdlib, zéro import générateur) ; le croisement scène↔cert (qui lit
  du YAML, côté générateur) vit dans `scenes.scene_matches_cert`, appelé par la
  CLI APRÈS la vérif exacte. Séparation des préoccupations : verify prouve la
  PREUVE (λ,μ,partition), le cross-check lie l'ÉNONCÉ au fichier scène.

**Pièges rencontrés** :
- **Dimension passive = explosion de feuilles** (risque #1 SPEC §9 rencontré en
  vrai) : φ=s0 sur la boîte 3D du peigne avec axe `oracle` → 256 FAIL (la
  profondeur part dans s2 inutile). Diagnostic immédiat (collision indépendante de
  s2) ; correctif `axis=margin` (54 feuilles). Pas un bug de soundness : le moteur
  refuse honnêtement quand la profondeur manque.
- **Suite adversariale d'abord à 433 s** : les solves moteur sur scènes à dalle
  LIBRE explorent profond (chaque cellule = 3 LP témoins) + échantillonnage dense
  60k. Resserré à **22.7 s** : budget feuilles borné (80 — il suffit d'UN FAIL
  pour ≠ PROOF), profondeur 12, échantillonnage dense 15k, micro-canal marqué
  `slow`. Le critère « zéro faux certificat » ne demande pas d'épuiser l'arbre,
  juste de prouver que le certificateur ne délivre pas de fausse preuve.
- **lstsq surajuste les dimensions passives** : sur le peigne 3D, le fit moindres
  carrés met du degré-2 partout (bruit en s2) → φ tordu → UNDECIDED (2 FAIL). Le
  barrière à la main φ=s0 est net et certifie. (À garder pour S9 : pénaliser/
  contraindre les coeffs des dims passives au fit.)
- **test-fast repassé sous 30 s** : les tests de scène refaisant un solve E3
  complet (cross-check, CLI certify→verify) marqués `slow` ; restent rapides le
  round-trip S1, le spatial (8 feuilles), un contrôle adversarial. 25.6 s.

**Décompte exact (sortie de session)** : `make test` = **149 passed, 0 skipped,
25 warnings, 184 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 88 passed, 61 deselected, 25.6 s.

**Critères de sortie S6** : parser YAML + scenes S1/peigne ✓ ; `cnp show` Meshcat ✓ ;
`cnp certify` bout-en-bout + verdicts 3 statuts (A17) ✓ ; suite adversariale
zéro faux certificat ✓ ; **G1' — S2-peigne certifié end-to-end (certify→verify OK) +
0 faux cert sur l'adversarial ✓** ; SPEC §6 amendée (règle 12) ✓ ; décompte
journalisé ✓. **V3 VALIDÉE par Stéphane** (« j'ai envie de te dire oui » après
itération sur les figures). **S6 vert, tous critères acquis.**

**Itération V3 (échange de validation — leçons viz)** : la validation a demandé
5 itérations de visualisation, chacune instructive : (1) Meshcat 3D pour une scène
PLANAIRE est illisible (on ne voit que boules + murs) → figure 2D top-down
(`save_planar_figure`) ; (2) deux poses figées ne disent pas « inatteignable » →
figure C-SPACE (`save_cspace_figure`) montrant le mur de collision séparant les
composantes libres ; (3) « je vois pas ce qui empêche de passer » → vue SWEEP
(`save_sweep_figure`, éventail des poses interpolées, collisions en rouge) ;
(4) « pourquoi le bras ne relève pas à la base ? c'est une rotule ? » → **non,
chaîne ROTOÏDE** (charnières 1 axe) : base = lacet (axe z, ne relève pas),
tangage = joint 1 (axe y) ; figure C-space annotée (axes lacet/tangage) + 2
trajectoires candidates (passage direct ET « relever puis traverser ») toutes deux
plongeant dans le mur. Leçon produit : expliciter le TYPE d'articulation et nommer
les axes du C-space par leur sens physique ; pour les scènes jouets la pédagogie de
la déconnexion est non triviale.

**Demande produit (Stéphane, pour les prochaines validations)** : voir une
situation **monde-réel** où le chemin a l'air faisable mais ne l'est pas (pas une
scène jouet). C'est exactement l'objet des scènes du plan : S7 (étagère 4-DOF,
objet derrière une planche), S9 (bin-picking, objet au fond d'un bac inatteignable
sans retirer la caisse), S10 (étagère 7-DOF, case haute inatteignable depuis home).
À garder en tête pour V4/V5/V6 : concevoir la scène ET sa figure pour raconter
« atteignable en apparence, prouvé inatteignable ».

**Prochaine étape** : S7 — ancrage Li-Dantam 4-DOF (porte G3'). NB S7/S9 : le
builtin `spatial_revolute` du parser est prêt côté moteur ; la certification EXACTE
des scènes spatiales (kind `spatial_revolute` dans verify.py) reste S9.

## 2026-06-11 — Revue de supervision S6 (claude.ai) — **G1' actée, annotations A18-A20**

**Verdict** : S6 validée, porte **G1' franchie** (peigne 3-DOF certifié
end-to-end certify→verify + cross-check scène + zéro faux certificat sur
l'adversarial). Le circuit A16 (diffs appliqués par Code en ouverture, commit
doc séparé) a fonctionné du premier coup.

**Signal majeur — le risque n°1 s'est matérialisé à n=3** : UNE dimension
passive (s2) suffit à faire échouer l'axe `oracle` (736 feuilles, 256 FAIL,
UNDECIDED) là où le lookahead-relais `margin` certifie en 54 feuilles. Données
précieuses obtenues deux sessions avant G2', à coût nul. Conséquences :
(a) le débat A10 est tranché par les faits — `margin` devient le défaut pour
toute scène nouvelle (l'oracle ne sert plus qu'à la parité de régression) ;
(b) la mitigation propre « dims passives par intervalles » monte en tâche n°1
de S8 ; (c) le modèle de coût (feuilles vs DOF) doit distinguer dims actives et
passives.

**Autres points au-dessus de l'attendu** : le micro-canal institutionnalisé en
test adversarial (la grille 11³ dupée, le moteur refuse — règle 9 prouvée à
chaque CI) ; verdicts à trois statuts réels et testés (ENGINE-PROOF n'est pas
du code mort) ; verify.py intouché, cross-check scène séparé côté générateur
(bonne frontière) ; `cnp certify` déterministe (φ baké, fit hors-ligne).

**Leçons V3 (5 itérations, capitalisées pour S11 et le papier)** : Meshcat 3D
illisible pour du planaire → vue 2D top-down ; deux poses figées ne montrent
pas l'inatteignable → C-space ; « je ne vois pas ce qui bloque » → vue SWEEP
(éventail interpolé, collisions rouges) ; confusion rotule/rotoïde → nommer le
TYPE d'articulation et les axes du C-space par leur sens physique
(lacet/tangage). Demande produit de Stéphane actée : les scènes S7/S9/S10
doivent raconter « atteignable en apparence, prouvé inatteignable ».

**Annotations** :
- [A18] Dimensions passives : priorité S8 relevée (tâche n°1) ; `margin` défaut
  scènes nouvelles ; modèle de coût à raffiner (actives vs passives).
- [A19] Le fit lstsq surajoute du degré-2 sur les dims passives (φ tordu →
  UNDECIDED) : en S9, fit STRUCTURÉ (pénaliser/zéroter les coefficients des
  dims détectées passives par sensibilité).
- [A20] « Apparence faisable » = critère de conception de scène : ajouté aux
  checklists V4/V5/V6 (point 0) et aux tâches de conception S7/S9/S10 ; la
  figure de chaque scène inclut la vue sweep qui montre POURQUOI ça a l'air
  passable.

**Vigilances S7 (premier contact avec une géométrie externe)** : scènes
Li-Dantam probablement Panda + maillages (voire doigts prismatiques) ⟹
s'attendre à une REPRODUCTION APPROCHÉE documentée (décomposition convexe,
joints prismatiques hors-périmètre v1 à verrouiller), pas un import direct ;
budget de session en conséquence. Comparaison de temps publiés : machines et
métriques différentes — le tableau dit ce qu'il peut comparer et ce qu'il ne
peut pas.

**Diffs à appliquer par Code en ouverture de S7 (CLAUDE.md du repo)** :
- D6 [A10 tranché/A18] Section S9, note A10 : remplacer « trancher SUR
  DONNÉES » par « TRANCHÉ (S6) : margin = défaut pour toute scène nouvelle ;
  oracle = parité de régression uniquement (données : peigne 3-DOF, 736 FAIL
  oracle vs 54 feuilles margin) ».
- D7 [A18] Section S8 : « dims passives par intervalles » passe en tâche n°1,
  avec référence aux données S6 ; ajouter à la sortie S8 : « le peigne certifie
  avec axis=oracle après mitigation (la profondeur n'est plus gaspillée) ».
- D8 [A19] Section S9, tâches : ajouter « fit STRUCTURÉ : pénaliser/zéroter les
  coeffs des dims passives détectées (leçon S6 : lstsq surajuste s2) ».
- D9 [A20] Checklists V4 (S7), V5 (S9), V6 (S10) : ajouter en point (0) :
  « la scène a l'air faisable — goal proche/visible dans l'espace de travail,
  la vue sweep montre pourquoi on croirait passer » ; et aux tâches de
  conception de scène correspondantes : produire la vue sweep.
- D10 [V3] Section S11 : la vue sweep et le nommage physique des axes
  (type d'articulation, lacet/tangage) deviennent des composants STANDARD de
  `cnp viz` et des figures.
- D11 Header : version 1.5, changelog « v1.4→v1.5 (revue S6, A18-A20) : G1'
  actée ; margin par défaut (A10 tranché) ; dims passives tâche n°1 S8 ; fit
  structuré S9 ; critère "apparence faisable" V4-V6 ; sweep + axes physiques
  standard S11 ».

**Prochaine étape** : S7 — ouverture : D6-D11 (+ commit doc séparé), puis
ancrage Li-Dantam 4-DOF (porte G3', validation V4 avec point « apparence
faisable »).

## 2026-06-11 — S7 (Claude Code) — Ancrage Li-Dantam 4-DOF (**V4 validée — clôture**)

**Fait** :
- **Ouverture** : diffs de revue S6 D6-D11 appliqués au CLAUDE.md du repo (circuit
  A16), commit doc séparé (10efe2c) : `margin` défaut scènes nouvelles + `oracle`
  parité régression (A10 tranché, D6) ; dims passives par intervalles = tâche n°1 S8
  (A18, D7) ; fit structuré S9 (A19, D8) ; point (0) « apparence faisable » +
  vue sweep en conception de scène, checklists V4/V5/V6 (A20, D9) ; sweep + axes
  physiques standard S11 (D10) ; header v1.5 + changelog (D11) ; État : S7 en cours.
  S6 re-vérifié vert avant démarrage (150 passed, 0 skip ; +1 vs les 149 journalisés
  en clôture S6 = `test_spatial_oracle_and_viz_geometry` ajouté pendant l'itération
  figures V3, après le décompte de clôture — tracé honnêtement).
- **Recherche de littérature (correction importante)** : les deux arXiv cités au plan
  (2406.04795, 2501.11434) ne sont **pas** la source 4-DOF. **2406.04795** (Li &
  Dantam, « Scaling MP Infeasibility Proofs ») est un suivi **5-6 DOF sur GPU**, zéro
  résultat 4-DOF ; **2501.11434** est un autre groupe (Thomas et al., Gênes,
  bitmap/segmentation). Le benchmark 4-DOF vit dans **Li & Dantam, RSS 2021 / IJRR
  2023, « Learning Proofs of Motion Planning Infeasibility »** : bras **épaule-coude
  4-DOF** (épaule sphérique 3-DOF + coude révolute, « reach inside a box »,
  **≈ 231 s CPU**) et **SCARA 4-DOF** (3 révolute coplanaires + 1 prismatique,
  ≈ 433 s). Leur certificat = **manifold séparateur appris** (SVM RBF + triangulation
  + collision numérique), pas un certificat algébrique. Aucun code/scène/URDF public.
- **Décision de portée S7 (Stéphane : « décide toi-même »)** : **Option A — scène
  spatiale épaule-coude 4-DOF fidèle → ENGINE-PROOF + échantillonnage dense**, la
  vérification EXACTE restant liée à S9 (`spatial_revolute` dans verify.py est une
  tâche S9). Raison : c'est le robot révolute-only 4-DOF fidèle de Li-Dantam
  (le SCARA a un prismatique hors-périmètre v1 ; le verrouiller donne un planaire
  3-DOF, plus 4-DOF) ; le verdict est honnête (précédent S5/S6 du 3-DOF spatial,
  règles 5/6) ; verify.py reste SACRÉ et le plan S9 intact. **La moitié « + vérifiée
  (exact) » de G3' est donc architecturalement reportée à S9** ; G3' est atteinte au
  sens SPEC §8 (« S3 reproduit et chiffré »). **Je n'amende pas le libellé de la porte
  G3' (règle 14)** — la réconciliation éventuelle (scinder G3' en engine/S7 +
  exact/S9 ?) revient à la revue de supervision.
- **`scenes/S3_shoulder_elbow.yaml`** : `spatial_revolute` 4 joints (épaule sphérique
  lacet z / tangage y / roll x concourants à la base + coude y). **Corps = bras
  supérieur (link 2)** : sur l'axe x de j2, donc un roll (axe x) autour de son propre
  axe ne le bouge pas, et le coude est distal ⟹ ses extrémités ne dépendent QUE de
  s0 (lacet) et s1 (tangage). **s2 (roll) et s3 (coude) sont PASSIFS** pour le corps.
  **Déconnexion par piégeage PROXIMAL** (leçon S5/S6 : un barrage piloté par le joint
  distal est défait par la redondance) : un panneau vertical mince devant l'épaule
  piège le bras supérieur sur une bande de lacet |s0|≤δ, pour TOUT tangage admissible
  et TOUS s2,s3. φ=s0, δ=1/10, start lacet gauche / goal lacet droite, tous deux
  libres. « Atteignable en apparence, prouvé inatteignable » (A20).
- **`cnp certify scenes/S3_shoulder_elbow.yaml` → ENGINE-PROOF** (8 feuilles, axe
  margin) avec son avertissement règle 5. Cross-checks soundness : **start/goal
  libres**, **0 point libre dans la dalle sur 300k échantillons seedés**, **libres
  des deux côtés** (deux composantes libres distinctes) ⟹ vraie déconnexion 4-DOF.
  Contrôle négatif : panneau rétréci en y ⟹ chemin libre ⟹ moteur **UNDECIDED**,
  aucun faux certificat.
- **Harness `benchmarks/run_benchmark.py`** (`make benchmark`) : chronométrage certify
  des scènes livrées + **balayage du coût en dimensions passives** (mini-version de la
  micro-tâche feuilles(n) de S9, avancée car c'est le risque n°1). Écrit dans
  `benchmarks/results/<UTC>/results.json` seedé + hash de commit (règle 7). Métriques
  SPEC §7 (verdict, feuilles, profondeur, #LP, degré témoin, temps moteur, temps de
  vérif exacte). **Données obtenues** :
  - S1 PROOF 46 feuilles (vérif exacte ~0.09 s) ; S2 PROOF 54 (~0.18 s) ;
    **S3 ENGINE-PROOF 8 feuilles**, moteur ~0.5 s, dense 0/300k.
  - **Balayage dims passives (margin vs oracle)** : n=2/3/4/5 joints (0/1/2/3 dims
    passives) → margin **plat à 8 feuilles**, oracle **8/12/20/36** (exponentiel en
    dims passives). Preuve chiffrée sur runs moteur réels du défaut margin (A10) et de
    la priorité n°1 S8 (A18) ; levier n°1 de G2', mesuré 2 sessions à l'avance.
- **Table comparative** `benchmarks/COMPARISON-Li-Dantam.md` (G3' « chiffré ») :
  nos chiffres vs Li-Dantam RSS2021 publiés, avec **caveats honnêtes** (méthode
  différente : manifold-SVM numérique vs Bernstein-LP algébrique ; matériel/métrique
  différents ; force de certificat différente — nous exact-vérifiable au planaire /
  moteur+dense au spatial, eux collision numérique ; notre barrière est bakée). Dit
  ce qu'elle PEUT comparer (même régime 4-DOF, certificat algébrique des ordres de
  grandeur moins cher quand une barrière basse existe, exact-vérifiable) et ce qu'elle
  NE PEUT PAS (pas une course de vitesse apples-to-apples — pas de claim « ×400 »).
- **Figures V4** (`scripts/make_scene_figures.py`, `make figures`) :
  `scene_S3_shoulder_elbow_sweep.png` (bras épaule-coude COMPLET, éventail du lacet,
  poses du milieu rouges plantées dans le panneau) + `scene_S3_shoulder_elbow_cspace.png`
  (C-space lacet s0 / tangage s1 : mur de collision couvrant tout le tangage, dalle or
  dedans, start/goal de part et d'autre = goal libre mais INATTEIGNABLE).
- **Tests `tests/test_s3_anchor.py`** (6) : 4-DOF spatial ENGINE-PROOF ; start/goal
  libres + dalle 0-libre (4k rapide, 300k @slow) ; CLI ENGINE-PROOF avec avertissement
  + note de portée S9 ; contrôle négatif panneau rétréci (@slow) ; balayage dims
  passives margin-plat/oracle-croît (@slow). `make benchmark` cible.
- `make test` : **156 passed, 0 skipped, 25 warnings, 252 s** (150 S6 + 6 S3).
  `make test-fast` = **92 passed, 64 deselected, 28.7 s** (sous 30 s).

**Décisions** :
- **Robot fidèle = épaule-coude (pas SCARA)** : le SCARA a un joint prismatique
  (hors-périmètre v1) ; le verrouiller le réduit à un planaire 3-DOF, perdant le
  4-DOF. L'épaule-coude est révolute-only et c'est la vraie scène 4-DOF de leur papier.
- **Reproduction APPROCHÉE documentée** (anticipé par la revue S6) : on reproduit leur
  ROBOT 4-DOF et un échec d'atteinte de même nature (cible bloquée par un panneau),
  la tâche étant adaptée pour qu'une barrière basse s'applique (piégeage proximal).
  Pas un import (aucun artefact public). La table le dit explicitement.
- **Corps = bras supérieur, déconnexion proximale** : un barrage distal est défait par
  la redondance (leçon S5 « mur frontal contourné en tangage », S6 peigne). Le bras
  supérieur indépendant de s2,s3 garantit une bande pleine ⟹ déconnexion topologique
  réelle dans la boîte 4-DOF. 2 dims actives + 2 passives, exactement la structure qui
  stresse le coût (et que margin encaisse à plat).
- **`axis=margin` (défaut A10)** : ne découpe pas les 2 dims passives → 8 feuilles vs
  20 (oracle). Validé par le balayage.
- **Harness avec balayage dims passives** : la donnée la plus utile de S7 pour G2' ;
  obtenue gratuitement en construisant l'ancrage. Quantifie A18.

**Pièges rencontrés** :
- **arXiv mal attribués dans le plan** : les deux IDs cités ne contiennent pas la scène
  4-DOF (l'un est 5-6 DOF GPU, l'autre un autre groupe). Source réelle = RSS2021/IJRR2023.
  Recherche web nécessaire avant de coder (sinon reproduction d'une scène inexistante).
- **Panneau trop large en y** (1er prototype) : start/goal PIÉGÉS (collision) au lieu de
  libres — la déconnexion doit séparer deux configs LIBRES. Resserré en y (w=0.06) :
  la bande de lacet est attrapée (y≤0.022 au panneau) mais les lacets extrêmes
  (start/goal, y≈0.13-0.24) passent libres. Diagnostic par le contrôle « start free ».
- **Reach au tangage extrême** : à |s1| max, le bras n'atteint qu'environ x=0.18 ;
  le panneau doit être à x<reach pour TOUT tangage admissible, sinon la dalle n'est
  pas toute-collision et le moteur REFUSE (UNDECIDED, pas faux). Tangage borné à ±2/5,
  panneau à x∈[3/20,1/5]. Le moteur (pas l'œil) arbitre : la dalle 0-libre/300k confirme.
- **test-fast à 66 s** (1ʳᵉ version) : les checks denses (oracle sympy-lambdifié, 20k×30
  évals) coûtent cher. Dense rapide ramené à 4k + n_samples=20, le 300k / le contrôle
  négatif / le balayage passés @slow → test-fast 28.7 s.
- **Tip == elbow dans la viz du corps** : le corps (bras sup.) s'arrête au coude ; la
  figure ne montrait qu'un segment. Ajout du dessin de l'avant-bras (via la FK de j3)
  dans la figure S3 pour qu'elle lise comme un vrai bras épaule-coude (fidélité V4).

**Décompte exact (sortie de session)** : `make test` = **156 passed, 0 skipped,
25 warnings, 252 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 92 passed, 64 deselected, 28.7 s. Benchmark canonique :
`benchmarks/results/20260611T194801Z/` (à régénérer post-commit pour aligner le hash —
les chiffres figurent aussi dans COMPARISON-Li-Dantam.md).

**Critères de sortie S7** : scène S3 4-DOF reproduite (épaule-coude fidèle) ✓ ;
harness benchmarks/ + résultats datés/commit-stampés (règle 7) ✓ ; **table comparative
honnête vs Li-Dantam** ✓ ; écarts commentés (méthode/matériel/certificat ; pas de
course de vitesse) ✓ ; SPEC : pas d'amendement requis (reproduction approchée prévue
au plan, ENGINE-PROOF aligné sur §1/§6) ; décompte journalisé ✓.
**RÉSERVE** : la moitié « + vérifiée (exact) » de G3' (libellé CLAUDE.md S7) est
reportée à S9 (verify spatial) — décision actée avec Stéphane (Option A), non un échec ;
**à arbitrer par la revue** (scinder G3' ?). **V4 EN ATTENTE** (demande ci-dessous).

=== DEMANDE DE VALIDATION VISUELLE (S7-V4) ===
Commande à lancer :
  make figures          # (re)génère les PNG ; ou directement :
  # python scripts/make_scene_figures.py
  open benchmarks/figures/scene_S3_shoulder_elbow_sweep.png
  open benchmarks/figures/scene_S3_shoulder_elbow_cspace.png
  # robot 3-D (orbitable) : python -m cnp show scenes/S3_shoulder_elbow.yaml
  #   (--config sweep pour l'éventail ; Ctrl-C pour arrêter le serveur Meshcat)
Ouvrir            : les deux PNG ci-dessus (figure sweep + figure C-space).
Référence papier  : Li & Dantam, RSS 2021 « Learning Proofs of Motion Planning
                    Infeasibility », Fig. 7b (bras épaule-coude 4-DOF). (Je ne peux
                    pas reproduire leur figure ; comparer la topologie/le robot.)
Vérifier          :
  0. [A20] La scène a l'air FAISABLE : le goal (lacet droite) est proche/visible,
     start et goal sont libres, la vue sweep montre POURQUOI on croirait passer
     (l'éventail des poses balaie le panneau).
  1. Même topologie qu'eux : un bras épaule-coude (épaule sphérique + coude) dont la
     cible est bloquée par un panneau/étagère devant — « atteignable en apparence ».
  2. Même robot / joints actifs : épaule sphérique (lacet/tangage/roll) + coude ;
     le mouvement bloqué est le balayage du LACET de base (s0), roll+coude passifs.
  3. Figure C-space : un MUR de collision (gris) couvre TOUT le tangage s1, la dalle
     or |φ|≤1/10 est entièrement dedans, start (★) et goal (✚) de part et d'autre
     ⟹ goal libre mais INATTEIGNABLE.
Critère de réussite : la paire de figures raconte « bras 4-DOF, cible bloquée par un
  panneau, atteignable en apparence mais prouvé inatteignable », fidèle au scénario
  4-DOF de Li-Dantam.
Réponse attendue  : « VALIDÉ S7-V4 » ou description de l'anomalie.

**Itération V4 (1er retour Stéphane : NON VALIDÉ, point 0 en échec)** — l'objection
était juste : la vue de dessus masque la HAUTEUR du panneau ⟹ « pourquoi pas
par-dessus ? ». Corrections :
- **Vue de CÔTÉ + éventail de tangage** (`scene_S3_shoulder_elbow_side.png`, plan x-z) :
  bras supérieur balayé sur tout son tangage à lacet=0, **9/9 poses en collision**,
  enveloppe de portée (rayon 0.4) tracée, sommet du panneau au-dessus. **Réponse
  explicite : le blocage par-dessus est la HAUTEUR DU MUR, pas la limite articulaire.**
  Géométrie : portée verticale max du bras supérieur = sa longueur 0.4 m (un point du
  segment ne dépasse jamais z=0.4) ; panneau remonté à **z∈[-3/5,3/5]** (sommet 0.6 >
  0.4) ⟹ aucune config ne place le bras au-dessus du panneau. Même au tangage max
  (43.6°) le bras croise la profondeur du panneau à z≤0.19 (bas dedans). La limite de
  tangage |s1|≤2/5 borne la boîte mais n'est PAS la raison du blocage par-dessus (au
  tangage limite, le bras plante encore dans le panneau). Re-vérifié : PROOF, start/goal
  libres, 0 libre/100k dans la dalle (le panneau plus haut n'ajoute que de la collision).
  Figure « bras supérieur seul » (le corps certifié) ⟹ argument de hauteur étanche.
- **[A21] Tableau de correspondance géométrique** papier↔YAML archivé
  (`benchmarks/GEOMETRY-S3-vs-LiDantam.md`) : Li-Dantam ne publient AUCUN chiffre
  (RSS2021 §V-B = structure cinématique + tâche en prose, Fig 7b graphique seul). Le
  tableau sépare FIDÈLE (topologie épaule sphérique+coude, 4-DOF, tâche d'atteinte
  infaisable) de CHOISI PAR NOUS (toutes les longueurs/dimensions/limites). Honnêteté
  de reproduction approchée (anticipée par la revue S6).
- **[A23] Décision de périmètre actée + checklist V4 amendée (diff CLAUDE.md, commit
  doc séparé)** : le critère A20 « apparence faisable » est réservé aux scènes-VITRINES
  V5/V6 (non négociable là-bas) ; une scène de BENCHMARK (V4) doit avant tout
  **répondre aux objections naturelles du spectateur** (vue de côté + sweeps lacet ET
  tangage + contrainte bloquante explicite). V5/V6 point (0) marqué « non négociable ».
  Changelog header annoté (revue V4, A21/A23).
- Tests re-verts après remontée du panneau (6/6). Nouvelle figure dans `make figures`.
  La paire de figures est désormais un trio : sweep (lacet, dessus) + côté (tangage,
  hauteur) + C-space (mur sur tout le tangage). V4 re-soumise à Stéphane.

**Itération V4 (2e retour Stéphane : VALIDÉ côté figures + exigence nouvelle A24)** —
V4 acquise sur les figures ; nouvelle exigence à journaliser et appliquer :
- **[A24] Artefact de validation PRINCIPAL pour toute scène spatiale = interactif ou
  animé.** Livré : **`cnp show <scene> --interactive OUT.html`** (`viz.export_interactive_html`)
  → **HTML auto-suffisant, zéro dépendance** : FK recalculée en JS depuis les axes/offsets
  de la scène, deux projections (DESSUS x-y pour le lacet, CÔTÉ x-z pour le tangage/
  hauteur), **4 curseurs articulaires** (noms physiques lacet/tangage/roll/coude),
  **détection de collision visuelle** du bras supérieur (devient ROUGE), **fantômes
  start/goal étiquetés** sur les deux vues, **boutons rejouant les tentatives
  d'évasion** (passage direct lacet / passer par-dessus tangage / contourner roll+coude)
  avec **verdict animé**. Vérifié : la logique JS (FK Rodrigues + collision) reproduit
  EXACTEMENT l'oracle Python (node : start/goal libres, dalle en collision, corps
  indépendant de roll/coude) ; verdicts d'évasion corrects (lacet : trajet traverse
  7/25 en collision = BLOQUÉ ; tangage : 0 libre/25 = BLOQUÉ ; contourner : 0 libre/25
  = BLOQUÉ). Rendu vérifié au navigateur (Claude Preview) : poses libres en sombre,
  collision en rouge dans les deux vues, panneau + enveloppe de portée corrects. Le
  GIF de repli (A24) est inutile (HTML livré). 10 Ko, ouvrable sans serveur.
  Piège attrapé : 1ʳᵉ version du verdict « passage direct » disait « libre trouvé
  (18/25) » alors que le MOUVEMENT est bloqué (7 poses du trajet en collision) —
  corrigé : un TRAJET est bloqué dès qu'UNE pose en route collisionne ; une tentative
  d'ÉVASION dans la bande interdite est bloquée si 0 pose libre. Limite assumée :
  projection x-z (côté) ambiguë pour un bras décalé en lacet (peut sembler croiser le
  panneau sans le toucher) — note ajoutée dans le widget et les figures ; la collision
  est calculée en 3D.
- **[A24-a] Fantômes start/goal étiquetés sur TOUTES les vues d'espace de travail**
  (pas seulement symboles C-space) : ajoutés au sweep (dessus, fantômes gras bleu/vert
  « start/goal (libre) ») et à la vue de côté (étiquetés lacet ±0.6, libres ; dashés car
  la projection x-z écrase le lacet). **[A24-b] Chaque vue déclare ce qu'elle montre**
  (bras complet vs bras supérieur seul) : sous-titres ajoutés (dessus = bras complet,
  sup. épais = corps ; côté = bras supérieur seul ; widget = idem par vue).
- **Standard V5/V6** : A24 ajouté aux checklists V5/V6 (artefact interactif/animé
  obligatoire pour scènes spatiales). Amendement CLAUDE.md (règle 11 + V4-V6), commit
  doc séparé (A16).
- Tests : 2 nouveaux (`test_interactive_html_*`) — HTML auto-suffisant + géométrie bakée
  correcte + refus d'une scène planaire. Note : Claude (claude.ai) a prototypé un widget
  côté supervision ; j'ai livré ma propre version auto-suffisante (zéro dépendance) — à
  aligner sur son prototype si Stéphane préfère (demander la spec).

**Itération V4 (3e retour Stéphane : exigence A25 — limites articulaires explicites)** —
- **Correction des chiffres** : les valeurs d'exemple de Stéphane (lacet ±62°, roll ±90°,
  coude 0-110°) ne correspondaient pas à ma boîte (±62° = la valeur de start/goal s0=±0.6,
  pas la limite). Limites RÉELLES (q=2·atan(s)) : lacet ±70°, tangage ±44°, roll/coude
  étaient ±70° (s=±0.7). Son indice « coude 0-110° » est juste sur le fond : un coude
  symétrique ±70° est physiquement faux. Comme **roll et coude sont PASSIFS** (impact nul
  sur la soundness), je les ai rendus RÉALISTES : **roll s2∈[-1,1]→±90°**, **coude
  s3∈[0,7/5]→0–109°** (pas d'hyperextension ; start/goal à s3=0). Re-vérifié : PROOF,
  start/goal libres, **0 libre/150k** dans la dalle, libre des deux côtés.
- **[A25] Limites explicites PARTOUT** : (a) **encadré « limites articulaires : lacet
  ±70° · tangage ±44° · roll ±90° · coude 0–109° »** sur chaque figure (sweep, côté,
  C-space) ; (b) **C-space : « LE CADRE DE CE GRAPHE = LES LIMITES ARTICULAIRES »** +
  limites dans les labels d'axes (lacet ±70°, tangage ±44°) ; (c) **widget : bandeau de
  limites + butées des curseurs = limites** (dit explicitement) + **degrés affichés par
  curseur** (« coude (y) [0…109°] ») ; (d) **verdict CLI rappelle ses hypothèses à chaque
  PROOF/ENGINE-PROOF** : limites articulaires en degrés + « pas de wrap-around » +
  obstacles statiques + polytopes + géométrie exacte (`cnp certify` ET `cnp verify`).
  Helpers `viz.joint_limits_deg` / `viz.limits_caption`. Tests étendus (+ assertions A25).
- Boîte du widget « contourner » corrigée pour rester dans les limites (s3 ne descend plus
  sous 0). Limite assumée déjà notée : projection x-z ambiguë (collision calculée en 3D).

**Décompte exact consolidé (après itérations V4 A24+A25)** : `make test` = **158 passed,
0 skipped, 25 warnings** (156 du commit V4-pending + 2 tests widget/limites A24/A25).
`make test-fast` = 92 passed, 64 deselected, ~29 s. Le titre de l'entrée garde
« V4 en attente » : V4 validée côté figures mais re-soumise après A24/A25, pas encore
de « VALIDÉ S7-V4 » — le titre passera à « V4 validée » au micro-commit de clôture.

**Clôture S7 — V4 VALIDÉE par Stéphane (« VALIDÉ S7-V4 »)** après 3 itérations
(figures → vue de côté/objection « par-dessus » + A21 → widget interactif A24 →
limites explicites A25). **S7 vert**, tous critères de sortie acquis AU SENS SPEC §8
(S3 reproduite + chiffrée + V4 validée), avec la **réserve G3' actée** : la moitié
« + vérifiée (exact) » est portée à S9 (verify `spatial_revolute`) — à arbitrer par la
revue de supervision (scinder G3' engine/S7 + exact/S9 ?). Annotations produites cette
session : A21 (table géométrie), A23 (benchmark vs vitrine), A24 (artefact interactif),
A25 (limites explicites) — toutes appliquées + journalisées + intégrées à CLAUDE.md
(règle 11 / checklists V4-V6, commits doc séparés, circuit A16).

**Prochaine étape** : revue de supervision S7 (arbitrage G3'), puis S8 — perf :
**tâche n°1 dims passives par intervalles** (A18, données S7 : oracle 8→36 feuilles
sur 0→3 dims passives), highspy direct, sparsité, warnings. NB : la vérification EXACTE
des scènes spatiales (kind `spatial_revolute` dans verify.py) reste S9 — c'est elle qui
complétera le « + vérifiée » de G3' sur S3.

## 2026-06-11 — Revue de supervision S7 (claude.ai) — **A26 repositionnement, G3' scindée**

**Le point majeur [A26] — correction stratégique, pas bibliographique.** Vérifié
par la supervision : arXiv 2406.04795 = Li & Dantam, « Scaling Motion Planning
Infeasibility Proofs » (GPU, triangulation de Coxeter en batch, deux ordres de
grandeur vs leur méthode antérieure), précédé d'un RA-L 2023 sur le même axe.
La ligne « les méthodes rigoureuses plafonnent à 4-DOF », présente dans le récit
SPEC §1 et le pitch du projet, est PÉRIMÉE (elle venait des notes de la
supervision ; attrapée par la vérification de littérature de S7 — mea culpa
supervision, bravo session). Conséquences :
- G2' (5-6 DOF) se relit « la frontière GPU de Li-Dantam atteinte sur laptop
  CPU, avec certificat d'une autre nature » ; G4' (7-DOF) reste vraisemblablement
  au-delà d'eux (à confirmer sur leurs chiffres exacts).
- Le différenciateur principal devient la NATURE du certificat : algébrique,
  revérifiable en arithmétique exacte par un vérificateur indépendant, LP pur
  CPU, murs réutilisables (requêtes en microsecondes) — vs triangulation
  numérique d'un manifold appris validée par collision-checker flottant.
  « L'auditeur peut recompter » vs « croyez le pipeline ».
- Lecture positive : leur investissement continu (RSS→IJRR→WAFR→RA-L→GPU)
  valide le créneau.

**Arbitrage de porte (réserve S7)** : G3' est SCINDÉE — **G3'a ACQUISE en S7**
(scène 4-DOF fidèle épaule-coude, chiffrée, ENGINE-PROOF avec contrôles :
start/goal libres, 0 libre/150k dalle, libre des deux côtés, contrôle négatif
refusé) ; **G3'b = vérification exacte spatiale**, livrée avec S9
(`spatial_revolute` dans verify.py). L'option A de la session était la bonne ;
le refus d'auto-amender la porte (règle 14) est conforme.

**Verdict S7** : validée. Au-dessus de l'attendu : (1) balayage dims passives
sur runs moteur réels (margin PLAT à 8 feuilles, oracle 8/12/20/36 sur 0→3 dims
passives) — la donnée qui calibre G2', obtenue 2 sessions en avance ; (2) table
comparative refusant le claim de vitesse apples-to-apples (pas de « ×400 ») —
l'honnêteté qui survit à un reviewer ; (3) itérations V4 transformées en
produit : `cnp show --interactive` (HTML auto-suffisant, FK JS vérifiée contre
l'oracle Python, bug de verdict trajet-vs-pose attrapé), fantômes start/goal
partout, limites articulaires explicites partout (A24/A25), y compris la
correction des chiffres d'exemple erronés de la supervision (±62° → ±70°).

**Diffs à appliquer par Code en ouverture de S8 (CLAUDE.md + SPEC du repo)** :
- D12 [A26] SPEC §1 (et toute mention « plafonnent à 4-DOF ») : amender le récit
  état-de-l'art — Li-Dantam scalent à 5-6 DOF sur GPU (RA-L 2023, arXiv
  2406.04795) ; notre différenciation = certificat algébrique exactement
  vérifiable + CPU/LP + murs réutilisables ; G4' = au-delà en DOF *et* en force
  de certificat. Marquer « amendé S8 [A26] ».
- D13 [A26] benchmarks/COMPARISON-Li-Dantam.md : ajouter une section « lignée
  scaling » (RA-L 2023 + 2406.04795) avec leurs DOF/temps/matériel EXACTS lus
  dans les papiers (tâche d'ouverture S8, ~30 min de lecture) ; reformuler la
  conclusion du tableau selon A26.
- D14 [portes] CLAUDE.md : G3' scindée en G3'a (S7 ✅) / G3'b (S9) dans l'État
  et la section S7 ; libellés G2'/G4' annotés du repositionnement A26.
- D15 [A27] Harness : enregistrer l'état git clean/dirty avec le hash de commit
  (un benchmark sur arbre sale doit le dire) ; régénérer le run canonique
  post-commit.
- D16 [A28, légère] Règle 9, ajout : « toute référence externe (papier, chiffre,
  benchmark) citée dans SPEC/CLAUDE.md est VÉRIFIÉE à la première utilisation
  par la session qui s'en sert (leçon S7 : deux arXiv mal attribués par la
  supervision) ».
- D17 Header : version 1.6, changelog « v1.5→v1.6 (revue S7, A26-A28) :
  repositionnement état-de-l'art ; G3' scindée a/b ; lignée scaling au tableau ;
  git-dirty au harness ; vérification des citations ».

**Action Stéphane (V4 finale)** : `make figures`, ouvrir le TRIO de figures
(sweep dessus / côté tangage-hauteur / C-space) + l'interactif
(`python -m cnp show scenes/S3_shoulder_elbow.yaml --interactive /tmp/s3.html`
puis ouvrir le fichier) ; vérifier le bandeau de limites (A25) sur chaque vue,
les fantômes start/goal étiquetés, et que les trois boutons d'évasion concluent
BLOQUÉ ; répondre « VALIDÉ S7-V4 » (ou anomalie) à Code, qui clôt par
micro-commit et ouvre S8.

**Prochaine étape** : V4 finale, clôture S7, puis S8 — ouverture D12-D17, puis
tâche n°1 dims passives par intervalles (données S7 : oracle 8→36), highspy
direct, sparsité, warnings.

## 2026-06-12 — Session S8 (perf) — dims passives par intervalles + highspy + warnings

Entrée : S7 vert re-confirmé (`make test` = 158 passed, 0 skipped, 25 warnings avant S8).

**Fait** :
- **Ouverture (diffs de supervision S7, D12-D17, circuit A16/règle 14)** — tous appliqués :
  - **D12** SPEC §7 B1 + header (v1.3→v1.4) : récit état-de-l'art corrigé (A26). Li-Dantam
    **scalent à 5-6 DOF sur GPU** ; le « rigoureux plafonne à 4-DOF » est PÉRIMÉ.
  - **D13** `benchmarks/COMPARISON-Li-Dantam.md` : section « Scaling lineage » + reformulation
    de la conclusion (différenciateur = NATURE du certificat, pas la borne DOF) + bloc perf
    honnête. **D16** vérification de citation : `arXiv:2406.04795` confirmé par WebFetch
    (Li & Dantam, « Scaling Motion Planning Infeasibility Proofs », 2024, GPU, scènes 5-DoF
    et 6-DoF, ~2 ordres de grandeur vs leur méthode antérieure).
  - **D14** CLAUDE.md : G3' **scindée a/b** dans l'État (G3'a ✅ S7 / G3'b S9) ; **SPEC §8**
    portes G2'/G3'/G4' annotées du repositionnement A26.
  - **D15/A27** harness : `_git_dirty()` → champ `git_dirty` dans results.json + tag
    `+DIRTY-TREE` au header (un benchmark sur arbre sale le dit).
  - **D16/A28** règle 9 : clause « toute référence externe est vérifiée à sa première
    utilisation ». **D17** CLAUDE.md header v1.5→v1.6 + changelog + entrée État S8.
- **TÂCHE N°1 [A18] — dimensions passives par intervalles (le cœur de S8)** :
  - `engine.passive_dims(problem)` / `engine.active_axes` : un axe est PASSIF si ni `phi`
    ni aucune géométrie de paire (numérateurs FK + dénominateur D) n'en dépend
    (détection tensorielle, conservatrice).
  - **(a) Partition** : `_choose_axis` / `_slab_boundary_axis` / `_margin_axis` / fallback
    oracle restreints aux axes ACTIFS ⟹ on ne branche jamais sur une dim passive (elle reste
    un intervalle plein). Tie-breaking préservé ⟹ E3/E4 (0 dim passive) **byte-identiques**
    (46 / 78). **Le peigne 3-DOF certifie maintenant avec `axis=oracle` : PROOF, 46 feuilles,
    + vérifié exact** (vs UNDECIDED/736 avant). C'est le critère de sortie S8 nommé.
  - **(b) Réduction de LP** : `build_witness_lp(..., active_dims=)` projette `phi`/`N_k`/`D`
    sur les axes actifs (constants sur les passifs) et construit le LP en `k` dims ⟹ blocs
    Bernstein `(d+1)^k` au lieu de `(d+1)^n` — la lettre de A18. Appliqué au chemin de
    DÉCISION du moteur seulement ; le **certificat est re-résolu en pleine dimension** et
    `verify.py` (sacré, intact) le re-vérifie en pleine dim ⟹ **une réduction erronée ne peut
    PAS produire un faux PROOF** (au pire ENGINE-PROOF, attrapé par les tests). Garde de
    soundness : `_project_tensor` REFUSE de projeter un axe dont le polynôme dépend.
  - Sweep cost-model (harness) : **oracle 8/12/20/36 → 8/8/8/8** (plat), margin reste plat.
- **highspy direct (`witness.HighspyBackend`)** : API C++ via une instance `Highs` réutilisée
  (lazy par process, re-créée après fork). Consomme le MÊME `WitnessLP` (isolation S2).
  **Défaut moteur** (`ENGINE_BACKEND`), Mosek-free. Parité `t*` vs cvxpy/scipy < 1e-6 (test).
- **Warnings traités (25 → 0)** :
  - **20 DeprecationWarning fork** : RÉSOLUES (pas masquées) — défaut du work-queue passé de
    `fork` à `forkserver` (fork depuis un serveur mono-thread, plus de warning). Possible
    SANS perte car le ré-import est léger maintenant que le backend est highspy (pas cvxpy) :
    forkserver ~9% sous fork, toujours ≥3× sur 8 cœurs (test speedup vert).
  - **5 warnings Clarabel « Solution may be inaccurate »** : DOCUMENTÉS bénins + filtrés
    (`pyproject` filterwarnings) — proviennent UNIQUEMENT du cross-check SOS-SDP de
    `tests/regref.py` (oracle test-only, hors src/cnp par règle 3) ; le test assert quand
    même l'accord SOS↔LP à tolérance, donc une solution intérieure « inaccurate » mais
    in-tolérance n'affaiblit rien. Le chemin produit (HiGHS/highspy) ne l'utilise jamais.
- **Soundness re-validée** (règle 1, changement witness+engine) : `make test` complet +
  suite adversariale `test_adversarial.py` verts, **0 changement de verdict**. Nouveaux tests :
  `test_passive_dims.py` (6 — détection, oracle certifie le peigne + vérif exacte, sweep plat),
  `test_witness.py` +3 (parité highspy, réduction active-dim == pleine dim sur t*, refus de
  projection non-sound). `test_s3_anchor` mis à jour (oracle désormais PLAT, pas croissant).

**Décisions** :
- **Réduction `(d+1)^k` au chemin de DÉCISION seulement, certificat en pleine dim** : minimise
  la surface sur le code soundness-critique (witness/cert/verify). Le vérificateur indépendant
  reste l'arbitre en pleine dim (règle 5) ⟹ la réduction est un pur levier de coût.
- **highspy = défaut moteur** : le plus rapide des trois, Mosek-free ; débloque aussi forkserver
  (le coût de ré-import qui écrasait spawn/forkserver disparaît sans cvxpy).
- **Peigne gardé sur `axis: margin`** (cert canonique stable à 54 feuilles, défaut A10) ; oracle
  documenté comme certifiant désormais (46) mais non basculé pour ne pas churner le cert.

**Pièges rencontrés / HONNÊTETÉ PERF (le point dur de S8)** :
- **« ≥10× vs cvxpy » N'EST PAS atteint par le back-end** : mesure honnête (chaud, par-LP)
  highspy ~1.3-3.7× vs cvxpy, et l'écart **rétrécit** avec la taille (le solve simplex domine).
  Le « 85 ms cvxpy » initial était du COLD-START (compilation), trompeur si amorti par-LP.
  Bout-en-bout S3 (process froid) : cvxpy 1.06 s / highspy-full 0.51 s / **highspy-réduit
  0.18 s** = **~6×**, pas 10×. **Refus de fabriquer un 10× cosmétique** (éthique S7, « pas de
  ×400 »). Le VRAI ≥10× est la réduction `(d+1)^k` : mesuré **7× (1 dim passive) → 28× → 133×
  → 733× (4 dims)** sur le bras-piège, `t_réduit == t_plein` exactement (aucune décision ne
  bascule). S3 ne décroche que 6× car **une seule** de ses dims passives est DÉTECTÉE (le roll
  s2 est géométriquement passif mais formellement présent dans le tenseur FK ⟹ détecteur
  conservateur le garde). **Le critère littéral « ≥10× sur S3 » reste rouge ; à arbitrer par la
  revue** (reformuler en « ≥10× dès ≥2 dims passives » ? améliorer la détection ?).
- **Shadowing `active`** dans `_wq_worker` : le param `active` y est DÉJÀ le compteur in-flight
  (Value) ; ma variable d'axes actifs l'aurait masqué (deadlock). Renommée `active_ax`.
- **Instance Highs partagée à travers fork** : créée lazy par-process (`os.getpid()`), jamais
  partagée — un objet solveur C++ copié par fork est un piège.

**Décompte exact (sortie de session)** : `make test` = **167 passed, 0 skipped, 0 warnings**,
~206 s (158 S7 + 9 nouveaux ; les 25 warnings S7 soldés : 20 fork via forkserver, 5 Clarabel
filtrés). `make test-fast` = **103 passed, 64 deselected, ~24 s**. Benchmark canonique : à
régénérer post-commit (arbre propre, hash aligné, git_dirty=false).

**Critères de sortie S8** :
- « le peigne 3-DOF certifie avec `axis=oracle` après mitigation » ✅ (46 feuilles + vérif exacte) ;
- « aucun changement de verdict sur la suite + adversarial » ✅ ;
- « warnings traités » ✅ (25 → 0) ;
- « mémoire bornée » ✅ (highspy + LP réduit) ;
- **« ≥10× plus rapide que cvxpy sur S3 » ⚠️ NON atteint au sens littéral** (mesure honnête ~6×
  bout-en-bout ; le ≥10× est livré par la réduction `(d+1)^k`, 7×→733×, mais S3 n'a qu'1 dim
  passive détectée). **Réserve actée, à arbitrer par la revue** (cf. honnêteté perf ci-dessus).

**Diffs CLAUDE.md de cette session** (règle 14) : header v1.6 + changelog ; règle 9 clause A28 ;
État — entrée S8 + G3' scindée a/b sur S7. **Diffs SPEC** : header v1.4 ; §7 B1 (A26) ; §8
portes annotées. Tous = application des décisions journalisées de la revue S7 (D12-D17) ou
tenue de l'État (règle 14 (a)/(b)/(c)) — aucune règle/critère changé de ma propre initiative.

**Prochaine étape** : revue de supervision S8 — **arbitrage du critère « ≥10× sur S3 »**
(reformuler ? améliorer la détection de passivité géométrique ?) ; puis S9 (scène S4 5-6 DOF,
G2') qui porte aussi **G3'b** (`spatial_revolute` dans verify.py — la moitié « vérifiée exacte »).

## 2026-06-12 — Décision de pilotage (Stéphane + supervision) — **S9 = go/no-go, S9b cas d'usage**

**Décision de Stéphane** : S9 sert essentiellement de go/no-go et de validation
du gain sur l'état de l'art ; la définition des cas d'usage devient une étape
explicite ; les trois scénarios proposés (bac logistique, étagère pharma, capot
de sûreté) sont retenus comme COMPLÉMENTAIRES (trois propositions de valeur du
même certificat : élagage prouvé TAMP / portée 7-DOF / auditabilité
dossier-de-sûreté).

**Restructuration actée** :
- **S9 (re-scopée) — go/no-go technique pur.** Ouverture D18-D21 + A29/A30 ;
  G3'b (`spatial_revolute` dans verify.py) ; scène 5-6 DOF choisie pour la
  COMPARABILITÉ (si les scènes des papiers scaling Li-Dantam sont descriptibles,
  en refléter une — reproduction approchée documentée, précédent S7 ; sinon bac
  technique) ; micro-tâche feuilles(n) + coût/feuille (calibration A31).
  Le critère A20 « apparence faisable » est RETIRÉ de V5 (déplacé en S9b/V6) ;
  V5 reste : intention de scène + artefact interactif (A24) + limites (A25).
  **Sortie formelle : `DECISION-G2.md`** — verdict G2' chiffré, calibration du
  modèle de coût, comparaison aux chiffres GPU exacts de Li-Dantam,
  recommandation GO / NO-GO / RE-SCOPE — revue par la supervision puis SIGNÉE
  par Stéphane avant toute ouverture de S10.
- **S9b (NOUVELLE, légère) — Portefeuille de cas d'usage.** Pour chacun des
  trois cas (bin-picking logistique ; étagère pharma ; capot de sûreté/fenêtre
  opérateur) : one-pager (claim, persona, valeur), spec de scène YAML
  (géométrie, robot, limites), storyboard des artefacts (figures + interactif,
  critères A20 non négociable / A24 / A25), et critères d'acceptation. Choix du
  cas FLAGSHIP pour S10. Validation **VU par Stéphane** (c'est sa matière
  commerciale Cambon AI autant que la nôtre).
- **S10** : implémente le flagship choisi en S9b (7-DOF, G4', V6 avec A20 non
  négociable). **S11** : pack démo étendu aux DEUX autres cas (certifiés à
  5-6 DOF via la machinerie S9) + viz complète (A11, sweep, axes physiques).

**Diffs à appliquer par Code en ouverture de S9 (CLAUDE.md du repo)** :
- D22 [re-scope S9] Réécrire la section S9 selon ci-dessus (go/no-go, scène
  comparabilité, A20 retiré de V5, sortie DECISION-G2.md signée avant S10) ;
  tâche : lire les descriptions de scènes 5/6-DOF de 2406.04795/RA-L 2023 et
  trancher reflet vs bac technique (documenté).
- D23 [nouvelle session] Insérer la section S9b « Portefeuille de cas d'usage »
  (contenu ci-dessus, validation VU, session légère) entre S9 et S10.
- D24 [S10/S11] S10 : « implémente le flagship choisi en S9b » ; S11 : ajouter
  « pack démo des deux autres cas d'usage certifiés 5-6 DOF ».
- D25 Header : version 1.8, changelog « v1.7→v1.8 (décision de pilotage) :
  S9 = go/no-go avec DECISION-G2.md signée ; S9b portefeuille de cas d'usage ;
  S10/S11 ajustés ».

**Prochaine étape** : S9 (gabarit habituel). Rappel des risques : session
chargée malgré le re-scope (A29/A30 + verify spatial + scène + calibration) —
Code est autorisé à proposer une coupe S9a (réductions + G3'b) / S9c (scène +
G2' + DECISION-G2.md) si le contexte sature, au critère partiel le plus proche
(règle 8).

## 2026-06-12 — Session S9a (Claude Code) — **G3'b : vérification exacte spatiale**

Coupe S9a prise (option explicitement autorisée par la décision de pilotage) : cette
session livre **G3'b** seul — la moitié « vérifiée exacte » de la scène spatiale — sans
toucher à la scène 5-6 DOF / G2' / DECISION-G2.md (= S9c, session suivante). Choix motivé :
(1) c'est le cœur soundness, auto-suffisant, sans dépendance Drake ; (2) il solde le
placeholder ENGINE-PROOF « exact verification arrives in S9 » posé depuis S6 ; (3) la
substance technique est non ambiguë (contrairement au volet doc, cf. réserve ci-dessous).

**Entrée** : S8 vert re-confirmé (`make test` = 167 passed, 0 skip, 0 warning ; le seul
échec observé, `test_parallel_speedup` à 2.92×, est un flake de timing — repasse à 3×+
isolé, machine chargée juste après une suite de 208 s).

**Fait — G3'b (verify.py spatial)** :
- **`verify.py` (module sacré) généralisé planaire→spatial sans dépasser 500 lignes**
  (499). La FK planaire et la FK `spatial_revolute` partagent désormais UNE boucle de
  chaîne sérielle (`_chain_joints` normalise → `[(offset, axe), ...]` ; `_body_fk` chaîne
  `Trans(offset_j)·Rot(axe_j, s_j)`). Le planaire est exprimé comme un cas particulier
  (axe +z, offset `(len_{j-1},0,0)`) ⟹ la généralisation ne RÉGRESSE pas le planaire
  (S1/S2/E3/E4 inchangés). **Garde de soundness ajoutée** : l'axe doit être UNITAIRE en
  exact (`Σ axe² = 1`), sinon le numérateur de Rodrigues `(1+s²)I + 2sK + 2s²K²` est faux —
  refus explicite. Restrictions inchangées et refusées proprement (règle 5) : q*≠0 et
  joints verrouillés (exigent une Rot(angle) irrationnelle — support iiwa verrouillé = suite).
- **`certificate.py`** : `_body_numerators` supporte le spatial (SympyRatFK + `_spatial_joints`
  factorisé ici, scenes délègue → DRY) ; le certificat **sérialise le champ `joints`**
  (offset/axe rationnels exacts) — sans lui un cert spatial n'est pas re-vérifiable
  indépendamment.
- **`scenes.py`** : `is_exactly_verifiable` accepte `spatial_revolute` à q*=0 sans joint
  verrouillé ; `scene_matches_cert` compare aussi les `joints` (le cross-check scène↔cert
  attrape un échange de géométrie).
- **`cli.py`** : message ENGINE-PROOF rendu honnête (plus de « arrives in S9 » périmé ;
  il ne couvre plus que joints verrouillés / q*≠0).
- **Effet** : `cnp certify scenes/S2b_spatial3.yaml` → **PROOF** (était ENGINE-PROOF),
  re-vérifié exact (8 feuilles). **BONUS** : l'**ancrage 4-DOF S3 (`S3_shoulder_elbow`,
  spatial lui aussi) passe aussi à PROOF exact** — G3'a (ENGINE-PROOF en S7) est de fait
  RENFORCÉE en preuve algébrique machine-vérifiable. (G3'a reste acquise ; ce gain n'était
  pas requis.)

**Soundness re-validée (règle 1 — changement de verify.py + chemin cert)** :
- `make test` complet : **170 passed, 0 skipped, 0 warnings** (167 S8 + 3 tests spatiaux
  adversariaux). Aucun changement de verdict sur le planaire (régression S1/S2/E3/E4 intacte).
- **Suite adversariale spatiale ajoutée** (`test_adversarial.py`, soundness suite) : sur les
  certs S2b ET probée à la main sur S3 — REJET de (axe non unitaire, axe faux qui casse la
  collision, gros décalage d'offset qui sort le bras de la bande, λ corrompu Σλ≠1, μ<0,
  feuille retirée → pavage cassé, collision mal-étiquetée « outside »). **Vérifié que l'axe
  de j0 est GÉNUINEMENT consommé** par la FK de verify (numérateurs différents z vs x ; 3
  axes sur 5 rejetés — pas un rubber-stamp).
- **Frontière de soundness à deux couches confirmée et testée** : une petite perturbation
  d'offset produit un cert qui reste INTERNE-valide (verify.verify l'accepte — il certifie
  le robot que le cert DÉCLARE), mais `scene_matches_cert` le rejette contre la scène
  auteur (« spatial joints differ »). verify = validité interne ; cross-check = ancrage à
  la scène. Le cert honnête passe les deux.

**Pièges / décisions** :
- **Module sacré à 502 lignes après le 1er jet** → comprimé à **499** (commentaires
  resserrés, pas de logique retirée). Le plafond `< 500` (règle 4) tient ; mais le support
  des joints VERROUILLÉS (iiwa S9c, format cos/sin §4) coûtera des lignes — il faudra
  soit factoriser, soit acter une révision de la limite AVEC la supervision (à signaler).
- **Accepter un cert à géométrie modifiée n'est PAS un bug** : c'est le contrat de verify
  (validité interne). Tracé explicitement par les tests pour ne pas le « corriger » par
  erreur un jour.

**Décompte exact (sortie S9a)** : `make test` = **170 passed, 0 skipped, 0 warnings**,
~205 s. `verify.py` = 499 lignes (< 500 ✓).

**Diffs SPEC** (règle 12) : header v1.4→**v1.5** ; §5 (FK spatiale supportée) ; §4 (champ
`joints` au schéma) ; §6 (ENGINE-PROOF re-cadré). **Diffs CLAUDE.md** : circuit doc S8→S9
appliqué en fin de session (voir ci-dessous).

**RÉSERVE DOC — LEVÉE en cours de session.** À mon ouverture, la « Revue de supervision S8 »
n'était pas dans le repo (D18-D21/A29-A31/v1.7/arbitrage ≥10× introuvables ; dernière entrée
= la décision de pilotage). J'ai refusé d'appliquer D22-D25 à l'aveugle (ils figeraient un
v1.7 fantôme + un re-scope autour d'annotations absentes) et de les inventer (A28). Stéphane
a ALORS versé la revue S8 au journal (entrée datée 2026-06-12, en fin de fichier). Réserve
levée : (a) critère « ≥10× sur S3 » REFORMULÉ et ✅ acquis (D18, « ≥10× dès 2 dims passives
mesuré 28×-733× ET S3 ≥5× bout-en-bout mesuré 6× ») ⟹ S8 pleinement verte ; (b) v1.7 = revue
S8 (D21), v1.8 = pilotage (D25) ⟹ plus de fantôme ; (c) A29 (passivité rationnelle), A30
(réduction par-paire = levier G2'), A31 (calibration) définis. **Circuit doc appliqué** :
CLAUDE.md header v1.6→**v1.8** (changelog v1.6→v1.7 D18-D21 + v1.7→v1.8 D22-D25) ; S8 sortie
+ État ✅ (D18) ; section S9 réécrite go/no-go intégrant A29/A30/A31 + G3'b (D19/D20/D22) ;
section S9b insérée (D23) ; S10/S11 ajustés (D24). Repo = unique source de vérité (A16).
(NB ordre du journal : la revue S8 a été ajoutée après cette entrée S9a ; non réordonnée
physiquement — les dates lèvent l'ambiguïté.)

**S9a est PARTIELLE.** La décision de pilotage définit S9a = « **réductions + G3'b** » ;
les « réductions » sont précisément **A29 + A30** (D19). Cette session a livré **G3'b** (+ le
bonus S3→PROOF). **Restent pour compléter S9a** : A29 (division exacte de N_k ET D par
(1+s_i²) ⟹ le roll de S3, géométriquement passif, est enfin détecté) et A30 (réduction
par-paire des LP de feuille — passivité = propriété de la PAIRE, tous les joints en aval du
link de la paire passifs POUR CE LP ; même architecture de soundness : décision seulement,
certificat re-résolu pleine dim, verify intact). Tests requis (règle 1) : t_réduit==t_plein
par paire, 0 changement de verdict, adversarial re-vert.

**Prochaine étape** : (1) **A29 + A30** (compléter S9a, les réductions — moteur/witness, chemin
de décision uniquement). (2) **S9c** : scène 5-6 DOF (iiwa, modèles Drake pré-téléchargés),
calibration feuilles(n) avec réduction par-paire (A31/D20), **G2'**, `DECISION-G2.md` signée.
Note iiwa : G3'b ne couvre pas encore les joints VERROUILLÉS dans verify (Rot(angle)
rationnelle, format cos/sin §4) — à livrer en S9c (iiwa verrouille 1-2 joints ; tenue sous
500 lignes à vérifier, sinon point à arbitrer).

## 2026-06-12 — Revue de supervision S8 (claude.ai) — **arbitrage ≥10×, A29-A31**

**Arbitrage de la réserve « ≥10× vs cvxpy sur S3 » : critère REFORMULÉ, réserve
LEVÉE, S8 verte.** Le critère d'origine était un mauvais proxy posé par la
supervision ; ce qu'il protégeait (« les LP de feuille assez bon marché pour
G2' ») est livré au-delà de l'attendu : réduction (d+1)^k mesurée 7×/28×/133×/
733× sur 1-4 dims passives, t_réduit == t_plein (aucune décision ne bascule),
balayage oracle aplati 8/12/20/36 → 8/8/8/8, peigne certifié en oracle (critère
nommé ✅). Nouveau critère acté : « coût de décision par feuille ≥10× dès
2 dims passives détectées (mesuré 28×-733×) ET S3 ≥5× bout-en-bout (mesuré
6×) ». Mention spéciale à la culture de mesure : cold-start cvxpy démasqué,
refus du 10× cosmétique (lignée du refus du « ×400 » en S7).

**Architecture de soundness saluée** : réduction sur le chemin de DÉCISION
uniquement, certificat re-résolu en pleine dimension, verify.py intact et
arbitre en pleine dim, projection qui REFUSE un axe dont le polynôme dépend —
une réduction buggée ne peut produire au pire qu'un ENGINE-PROOF, jamais un
faux PROOF. C'est la manière canonique d'optimiser un système certifié.
Warnings 25 → 0 par résolution (forkserver, rendu viable par highspy) ou
explication confinée (Clarabel = oracle SOS test-only), pas par masquage.

**Annotations** :
- [A29 — ouverture S9] Passivité RATIONNELLE : le roll de S3 est géométriquement
  passif mais N et D portent tous deux le facteur (1+s2²) (dénominateur commun
  par link) ⟹ détecteur tensoriel le garde. Correction : division exacte de
  N_k ET D par (1+s_i²) ; si tout divise, simplifier et marquer passif. Bonus
  attendu (non-porte) : S3 passe largement le 10× bout-en-bout.
- [A30 — S9, LE levier G2'] La passivité est une propriété de la PAIRE, pas du
  problème : pour une paire sur le link k, tous les joints en aval de k sont
  passifs POUR CE LP. Implémenter la réduction par-paire au niveau de chaque LP
  de feuille (le choix d'axe de partition reste sur l'union des actifs). Même
  architecture de soundness (décision seulement, certificat pleine dim). Sur la
  scène bac, les paires proximales verraient 5^6 → 5^2-5^3 lignes ; les 733×
  mesurés à 4 dims passives en sont l'aperçu.
- [A31] Modèle de coût : réviser les estimations de temps (tableau de
  supervision du 11/06) à S9 avec les données réduction + micro-tâche
  feuilles(n) maintenue ; distinguer dims actives/passives détectées
  (globales ET par-paire).

**Diffs à appliquer par Code en ouverture de S9 (CLAUDE.md du repo)** :
- D18 [arbitrage] Section S8 : critère « ≥10× sur S3 » remplacé par le critère
  reformulé ci-dessus, marqué ✅ avec renvoi à cette revue ; État : S8 ✅
  (réserve levée).
- D19 [A29+A30] Section S9, tâches d'ouverture : (a) passivité rationnelle
  (division exacte par (1+s_i²)) + test S3 ≥10× en bonus ; (b) réduction
  par-paire des LP de feuille (active dims = chaîne du link de la paire),
  tests : t_réduit == t_plein par paire, aucun changement de verdict,
  adversarial re-vert (règle 1).
- D20 [A31] Section S9, micro-tâche feuilles(n) : ajouter la mesure du coût
  par feuille avec réduction par-paire activée ; livrer la table de calibration
  du modèle de coût (feuilles × coût/feuille vs DOF actifs/passifs).
- D21 Header : version 1.7, changelog « v1.6→v1.7 (revue S8, A29-A31) :
  critère perf reformulé (arbitrage) ; passivité rationnelle + réduction
  par-paire en ouverture S9 ; calibration du modèle de coût ».

**Prochaine étape** : S9 — ouverture D18-D21 + A29/A30, puis scène S4 bac
(5-6 DOF iiwa), G3'b (`spatial_revolute` dans verify.py), porte G2', V5
(checklist avec point (0) « apparence faisable » non négociable + artefact
interactif A24 + limites A25). Stéphane : préférence de scénario-vitrine
(bin-picking logistique / étagère pharma / cellule capot) à exprimer AVANT la
conception de scène.

## 2026-06-12 — D26 (Stéphane) — **clôture de session = commit ET push**

**Décision** : règle 8 amendée — la clôture d'une session inclut désormais le **push**,
pas seulement le commit. Motif : la supervision lit le journal via GitHub ; sans push,
elle a systématiquement une session de retard (constaté à la clôture S9a, commitée
localement mais non poussée). Le push de clôture **lève**, pour ce cas précis, la règle
globale de Stéphane « jamais de `git push` sans demande explicite » : la clôture EST la
demande permanente, actée ici.

**Appliqué (règle 14, décision de supervision journalisée — pas d'initiative de Code)** :
CLAUDE.md règle 8 (« commit ET push [D26] ») + header v1.8→**v1.9** + changelog. Le commit
de clôture S9a (`4f5f678`) et ce commit D26 sont poussés vers `origin/main` en clôture.

**Portée** : push uniquement à la clôture de session (état vert, journal à jour). Pas de
force-push, pas d'amend (règles globales inchangées). La règle globale « jamais de push
sans demande » reste en vigueur HORS clôture de session.

## 2026-06-12 — Session S9a-suite (Claude Code) — **réductions A29 + A30 (S9a COMPLÈTE)**

Cette session complète S9a en livrant les deux RÉDUCTIONS (les « réductions » de la
décision de pilotage = A29 + A30, D19). Avec G3'b (session S9a précédente), S9a est désormais
COMPLÈTE. Le reste de S9 (scène 5-6 DOF, calibration, G2', DECISION-G2.md, joints verrouillés
dans verify, V5) constitue S9c — non ouvert ici (gate humain V5 + signature Stéphane sur
DECISION-G2.md ⟹ infaisable en autonomie ; clôture propre, règle 8).

**Entrée** : S9a (G3'b) re-confirmée verte — `make test` = 170 passed, 0 skip, 0 warning.

**Ouverture doc (circuit A16, commit doc séparé `11964e7`)** — diffs de supervision D27-D30
du lot revue S8 (D26 déjà commité `33cda50`) :
- **D27** [CLAUDE.md « Estimation honnête »] : re-scope 5-6 DOF re-cadré = frontière GPU
  Li-Dantam atteinte sur laptop CPU, certificat exactement revérifiable, différencié par la
  NATURE du certificat (A26) pas par le DOF (récit « seuls au-delà de 4-DOF » périmé).
- **D28** [SPEC §8] : G1' marquée ✅ (acquise S6).
- **D29** [SPEC §1] : « l'un des deux verdicts » → « l'un des **trois** verdicts »
  (PROOF / ENGINE-PROOF / UNDECIDED, renvoi §6).
- **D30** [CLAUDE.md règle 12] : « Amendements en attente : voir S4 » (périmé) supprimé.
- CLAUDE.md header v1.9 + changelog étendu D27-D30 ; SPEC réconciliation doc notée (pas de
  changement mathématique). Repo = unique source de vérité (A16).

**Fait — A29 (passivité RATIONNELLE)** :
- Primitive `engine._divide_out_one_plus_s2(t, axis)` : divise un tenseur par (1+s_i²) en
  EXACT quand le facteur est présent. Test structurel (les tenseurs sont deg ≤2/var) :
  `t = (1+s_i²)·M` avec M indépendant de s_i ⟺ tranche-exposant-1 nulle ET
  tranche-exposant-0 == tranche-exposant-2 (alors M = tranche-0). atol 1e-12 (les deux
  tranches sont bit-identiques en pratique — même `_factor("one")` = [1,0,1]).
- `engine._simplify_geometry(verts, D, n)` : divise N_k ET D par chaque (1+s_i²) commun à D
  et à TOUS les numérateurs (« si tout divise, simplifier »). Réécriture EXACTE et
  géométrie-préservante (x = N/D inchangé : on divise num et dén par le même facteur > 0).
- **Effet** : le roll de S3 (j2, axe x sur un bras coaxial — géométriquement passif mais le
  dénominateur commun par link l'habillait d'un (1+s2²) que le détecteur tensoriel gardait)
  est enfin détecté : `passive_dims(S3)` = **(2, 3)** (était (3,) seul). Vérifié que le
  détecteur PLAIN (pré-A29) garde s2 actif (`_tensor_depends(D, 2)` True) et que A29 le
  passive. Géométrie préservée testée à 200 échantillons (|x_full − x_simp| < 1e-9).

**Fait — A30 (réduction PAR-PAIRE, le levier G2')** :
- `engine._PairView` (paire → géométrie A29-simplifiée + ses dims actives propres) ;
  `pair_views(problem)` calcule, par paire, les axes dont φ OU la géométrie de CETTE paire
  dépend ; `_global_active` = union (axe de branchement). Chaque LP de feuille est réduit aux
  dims actives de SA paire (`certify_cell_view_margin`, `active_dims=view.active`) — une
  réduction en général PLUS fine que la globale (paire proximale sur chaîne longue : tous les
  joints en aval passifs POUR CE LP). Le branchement reste sur l'union ⟹ **partition
  inchangée**, seul le LP par-paire rétrécit. `passive_dims`/`active_axes` reformulés sur les
  vues. Chemins série, work-queue parallèle et frontier/checkpoint tous re-câblés sur les vues.
- NB : les scènes LIVRÉES n'ont qu'UN body_link ⟹ A30 == réduction globale sur elles
  (l'infrastructure par-paire est en place ; le levier ne se manifeste qu'avec plusieurs
  corps — paires proximale/distale de la scène bac S9c). Testé sur un problème synthétique à
  deux corps (link 1 actif {0,1} ; link 3 actif {0,1,2,3} ; union {0,1,2,3} ; global passif {4}).

**Soundness (règle 1 — changement engine.py, witness/verify INTACTS)** :
- **Architecture S8 préservée** : réduction sur le chemin de DÉCISION seulement ; le
  certificat est re-résolu en PLEINE DIM depuis la FK de scène (`certificate._body_numerators`,
  `active_dims=None`) ; `verify.py` (sacré, 499 lignes, **zéro diff**) re-dérive la FK et
  arbitre en pleine dim. Une réduction buggée ne peut au pire que coûter une feuille ou
  rétrograder PROOF→ENGINE-PROOF, jamais forger un PROOF.
- **Tests requis livrés** (`tests/test_reductions.py`, 8 tests) : (a) primitive de division
  exacte (positif + négatif) ; (b) géométrie préservée sur S3 ; (c) détection du roll S3 ;
  (d) **t_réduit == t_plein par paire** sur les feuilles réelles de S3 ET sur le problème
  deux-corps (la projection ne tombe que des axes réellement passifs ⟹ ne peut pas gonfler t) ;
  (e) actifs par-paire plus fins que le global (deux-corps) ; (f) **0 changement de verdict**
  (S3 PROOF + verify exact sur margin ET oracle) ; (g) bonus non-porte **S3 ~19× de coût LP
  bout-en-bout** (feuilles × lignes Bernstein, mesuré 632 vs 12256, ≥10× acquis).
- Suite adversariale (planaire + spatiale S9a) re-verte ; aucun verdict ne bascule sur la
  suite complète.

**Pièges / décisions** :
- **A29 division ≠ projection S8** : la division change la VALEUR de t (g_j divisé par
  (1+s_i²) ≥ 1 ⟹ t rétréci, plus conservateur ; T = δ²−φ² non divisé), mais préserve le
  VERDICT (vérifié). Le « t_réduit == t_plein » de la règle 1 se teste donc À géométrie
  simplifiée fixée (réduit-dim vs pleine-dim sur la MÊME géométrie A29) — là la projection
  est EXACTE (tenseurs constants le long des axes passifs), c'est la propriété S8 re-confirmée.
- **Synthétique deux-corps, piège du coaxial** : un premier jet mettait j3 d'axe x sur un
  body segment-x ⟹ j3 coaxial donc A29 le passivait à juste titre (actif (0,1,2) au lieu de
  (0,1,2,3)). Corrigé en tangages (axe y) perpendiculaires aux segments-x.
- `certify_cell_pair_margin` (publique, non utilisée ailleurs) renommée
  `certify_cell_view_margin` (prend une vue).

**Prép S9c (sans risque)** : modèles Drake **déjà en cache** (`iiwa14` chargé en 0.0s, hors
réseau) ⟹ prérequis règle 10 satisfait pour les tests iiwa REQUIS de S9c.

**Décompte exact (sortie S9a-suite)** : `make test` = **178 passed, 0 skipped, 0 warnings**,
~198 s (170 S9a + 8 `test_reductions.py`). `verify.py` = **499 lignes, zéro diff** (sacré
intact, règle 4). Diff de code : `engine.py` seul (+175/−45). Commit doc séparé `11964e7`.

**Diffs CLAUDE.md** (règle 14) : header v1.9 + changelog D27-D30 ; règle 12 résidu retiré
(D30) ; « Estimation honnête » re-cadrée (D27) ; État d'avancement S9a ✅ COMPLÈTE (réductions
livrées) ; section S9 « État S9a : COMPLÈTE ». **Diffs SPEC** : §1 trois verdicts (D29), §8
G1' ✅ (D28), note de réconciliation au header.

**Prochaine étape — S9c** (nouvelle session, gates humains) : (1) joints VERROUILLÉS dans
`verify.py` (Rot(angle) cos/sin rationnels §4 ; pré-arbitrage : factoriser d'abord, plafond
500→600 l. UNE seule fois si réellement inévitable, fichier unique/stdlib/zéro import
générateur) ; (2) scène 5-6 DOF iiwa choisie pour comparabilité (lire descriptions
arXiv:2406.04795 / RA-L 2023, refléter si descriptible sinon bac technique ; margin défaut,
fit STRUCTURÉ A19, vérité-terrain dense AVANT certification) ; (3) calibration
feuilles(n)+coût/feuille à n=3,4,5,6 avec réduction par-paire (A31/D20) ; (4) **[V5]**
validation visuelle OBLIGATOIRE avant tout run long (artefact `cnp show --interactive` A24 +
coupes C-space + limites A25 ; attendre « VALIDÉ S9-V5 ») ; (5) **DECISION-G2.md** — verdict
G2' chiffré, calibration, comparaison chiffres GPU Li-Dantam, GO/NO-GO/RE-SCOPE — revue
supervision puis SIGNÉE Stéphane avant S10.

## 2026-06-12 — Revue de supervision S9a-suite (claude.ai) — **S9a COMPLÈTE validée, A32**

**Verdict : S9a-suite validée — S9a est COMPLÈTE** (G3'b + réductions A29/A30).
178 passed, 0 skip, 0 warning ; verify.py 499 lignes, ZÉRO diff (sacré intact) ;
diff de code confiné à engine.py.

**Au-dessus de l'attendu** :
1. Le piège A29 compris finement : la division par (1+s_i²) change la VALEUR de t
   (g rescalé par un facteur ≥ 1, T non divisé ⟹ t plus conservateur) mais préserve
   le VERDICT ; le test règle 1 « t_réduit == t_plein » est correctement posé À
   géométrie simplifiée fixée, là où la projection est exacte (propriété S8
   re-confirmée). Mal compris, ce point aurait produit un test rouge à tort ou un
   test vide.
2. Honnêteté A30 : les scènes livrées n'ont qu'UN corps ⟹ A30 ≡ réduction globale
   sur elles ; le levier réel (paires proximales, 5^6 → 5^2-5^3) reste NON MESURÉ
   sur scène réelle — infrastructure validée sur un synthétique deux-corps (piège
   du joint coaxial attrapé et corrigé). Lignée « pas de ×400 ».
3. Architecture S8 à la lettre : décision sur géométrie simplifiée, certificat
   re-résolu pleine dim sur la FK de scène ORIGINALE, verify.py arbitre — une
   réduction buggée coûte des feuilles, jamais une fausse preuve.
4. Coupe S9c correcte (gates humains V5 + signature DECISION-G2 ⟹ pas d'autonomie
   possible) ; prérequis règle 10 soldé par avance (iiwa en cache, hors réseau).
   D26 acté proprement (push de clôture = demande permanente, portée bien bornée).

**Annotation** :
- [A32 → S9c] Dissonance décision↔certificat à instrumenter : le chemin de
  décision (géométrie A29-simplifiée) et la re-résolution pleine dim (géométrie
  originale) sont deux LP sur des polynômes différents ; une feuille décidée
  « collision » peut en théorie échouer à l'export (bornes Bernstein de tension
  différente). Conséquence au pire bénigne (UNDECIDED, jamais un faux PROOF),
  mais coût silencieux possible à l'échelle. Ajouter un compteur/log moteur
  « re-résolution échouée sur feuille décidée », attendu à ZÉRO sur les runs S9c
  (déjà zéro empiriquement sur S3, margin et oracle).
- [Note calibration] Le bonus S3 ~19× est un coût LP (lignes Bernstein 632 vs
  12 256), correctement étiqueté ; capturer le wall-clock S3 à la régénération du
  benchmark canonique S9c. La table de calibration A31 inclut explicitement la
  mesure PAR-PAIRE sur la scène bac (paires proximale vs distale) — c'est la
  première validation réelle du levier A30.

**Diffs à appliquer par Code en ouverture de S9c (CLAUDE.md du repo)** :
- D31 [A32] Section S9c (tâches) : ajouter « compteur/log de re-résolution
  échouée sur feuille décidée (A32), asserté/vérifié à zéro sur les runs de la
  scène S4 ; mesure par-paire (proximale vs distale) dans la table de
  calibration A31 ».
- D32 Header : version 1.10, changelog « v1.9→v1.10 (revue S9a-suite, A32) :
  S9a ✅ COMPLÈTE validée ; instrumentation dissonance décision↔certificat ;
  mesure par-paire à la calibration ».

**Prochaine étape** : S9c — joints verrouillés dans verify (pré-arbitrage 600
lignes en vigueur), scène 5-6 DOF comparabilité, calibration A31 (+ par-paire),
[V5] avant tout run long, DECISION-G2.md (revue supervision puis signature
Stéphane avant S10). La revue d'antériorité (risque n°6 SPEC §9) est livrée
côté supervision : docs/BIBLIO-ANTERIORITE.md à verser au repo (claim du papier
reformulé — voisin le plus proche : Henrion, Miller & Safey El Din,
arXiv:2404.06985, déconnexion algébrique moment-SOS sur ensembles abstraits
n ≤ 3 ; notre différenciation = bras articulés + vérification exacte a
posteriori). Cible de publication pressentie : RSS 2027 (review amicale d'abord,
décision de pilotage Stéphane).



## 2026-06-12 — Session S9c (Claude Code) — **verify joints verrouillés (G3'b iiwa) + instrumentation A32 ; coupe après tâches 1-2 → S9d**

Cette session ouvre S9c (go/no-go technique 5-6 DOF). Elle livre les DEUX briques
d'infrastructure (tâches 1-2 du prompt) et **coupe proprement après elles** (règle 8) :
la scène iiwa 5-6 DOF, la calibration, le **gate humain V5** (« VALIDÉ S9-V5 » requis
avant tout run long) et **DECISION-G2.md** (signature Stéphane avant S10) constituent
**S9d**. Le cœur de G2' (la scène certifiée + le chiffrage) n'est PAS ouvert ici : il
est gaté humainement (V5 + signature) ⟹ non-franchissable en autonomie, et une scène
bâclée serait pire que pas de scène (leçon micro-canal : vérité-terrain dense AVANT
certification, rule 9).

**Ouverture doc (circuit A16, commit doc séparé `7a4cd87`)** :
- 3a — revue de supervision S9a-suite (claude.ai) appendée à JOURNAL.md (déjà appliquée
  en working tree par un run partiel antérieur ; le fichier temporaire avait été consommé).
- 3b — `docs/BIBLIO-ANTERIORITE.md` versée telle quelle ; **risque n°6 SPEC §9 marqué
  « TRAITÉ, claim reformulé »** (voisin le plus proche : Henrion, Miller & Safey El Din
  2024, arXiv:2404.06985 ; claim « premiers certificats d'infaisabilité de motion planning
  pour bras articulés *exactement vérifiables a posteriori* »).
- 3c — **D31** [A32] tâche instrumentation + mesure par-paire à la calibration ; **D32**
  header CLAUDE.md **v1.10** + changelog v1.9→v1.10.

**Fait — Tâche 1 : joints VERROUILLÉS dans `verify.py` (sacré)** :
- Le primitif `_rot_homog` portait DÉJÀ une branche `locked_cos_sin` (Rodrigues numérique
  R = I + sin·K + (1−cos)·K², dénominateur 1) ; le seul verrou était `_body_fk` qui REFUSAIT
  les joints verrouillés. Réécriture de `_body_fk` : joints verrouillés substitués par leur
  rotation numérique exacte, **`cos²+sin²=1` vérifié exact** ; ils ne prennent PAS de variable
  s ⟹ les débloqués sont ré-indexés 0..n−1 et eux seuls ajoutent un facteur (1+s²) à D.
- **PRÉ-ARBITRAGE 500→600 NON UTILISÉ** : la factorisation a suffi. `verify.py` = **499 lignes**
  (inline d'un temporaire dans `_rot_homog`, docstrings resserrées sans perte de contenu de
  soundness). Test `test_verify_under_500_lines` vert. Fichier unique, stdlib only, zéro import
  du générateur — invariants règle 4 intacts.
- **Format §4 ré-aligné** : le certificat portait l'ANGLE verrouillé (dérive S4-S9a) ; ramené
  au format SPEC §4 **`locked_joints[idx] = {cos, sin}`** rationnels exacts. `Robot.locked`
  stocke (cos, sin) Fraction + valide `cos²+sin²=1` (défense en profondeur côté générateur) ;
  `Robot.locked_angles` (atan2) alimente la FK FLOAT du générateur (`SympyRatFK`), l'interface
  bas-niveau ratfk reste angle-based (inchangée). Sites mis à jour : certificate, scenes (×3 +
  scene_matches_cert), viz, cli (messages verdict). `is_exactly_verifiable` : un q*=0 à joints
  verrouillés (cos/sin rationnels) est désormais **PROOF**.
- **Tests adversariaux dédiés** (`tests/test_locked_joints.py`, 9 tests) sur une scène 3R
  spatiale à pitch j1 verrouillé au **3-4-5 pythagoricien** (PROOF, 2 feuilles, < 1 s) — la
  PREMIÈRE scène dont la preuve exacte DÉPEND d'un joint verrouillé (verify re-dérive la
  rotation ⟹ déplacer le verrou relocalise le poignet piégé hors du mur). Mutations toutes
  rejetées : cos/sin corrompus (`cos²+sin²≠1`), **joint verrouillé déplacé** (4 rotations valides),
  verrou retiré (n incohérent), mauvais index ; + identité (cos=1,sin=0) PROOF ; + le générateur
  refuse aussi un verrou non-unitaire.

**Fait — Tâche 2 : instrumentation A32 (D31)** :
- Exception `certificate.ReResolutionFailed` + compteur **`cert['stats']['n_reresolve_failed']`** :
  feuilles décidées « collision » (géométrie A29-simplifiée / A30-réduite, chemin de DÉCISION)
  qui échouent la re-résolution pleine-dim depuis la FK de scène. Dissonance décision↔certificat
  **bénigne au pire** (UNDECIDED, jamais un faux PROOF — verify arbitre en pleine dim), mais
  coût silencieux à l'échelle ⟹ COMPTÉE sur TOUTES les feuilles (pas crash à la première) et
  rendue BRUYANTE (raise A32 explicite si > 0, jamais de PROOF amputé d'une feuille).
- Exposé dans le harness (`run_benchmark.py` row `n_reresolve_failed`). **Asserté à ZÉRO**
  sur S3 (margin ET oracle) dans `test_reductions.py` (`test_a32_...`) — le zéro instrumenté
  que les runs S4 (S9d) asserteront. `test_certificate` round-trip E3 inclut le champ.

**Soundness (règle 1 — changement de `verify.py` sacré)** : suite adversariale complète
(test_verify 26 mutations + test_adversarial + test_locked_joints 9) verte ; aucun verdict
ne bascule. **`verify.py` reste l'arbitre pleine dim**.

**Décisions / amendements** :
- **SPEC v1.5→v1.6** (rule 12, acté S9c) : §2 + §5 + §1 + §6 — vérificateur supporte les
  joints verrouillés (cos/sin rationnels) ; scène q*=0 verrouillée = PROOF ; seul q*≠0 reste
  ENGINE-PROOF. Champ `locked_joints` = `{cos, sin}` (et non l'angle).
- **CLAUDE.md v1.10** (D32) déjà au commit doc `7a4cd87`.
- **Coupe S9c→S9d** (règle 8) : tâches 1-2 = unité propre, verte, committable. Scène iiwa,
  calibration, V5, DECISION-G2.md = S9d (gates humains).

**Pièges** :
- **Format verrouillé = cos/sin, PAS l'angle** : un angle générique a des cos/sin irrationnels ⟹
  invérifiable en exact. Les scènes verrouillent à 0, ±π/2, π ou pythagoricien (3/5, 4/5).
  L'implémentation S4-S9a stockait l'angle (jamais exercé car locked={} partout) — dérive
  silencieuse vs SPEC §4, corrigée ici.
- **Test « joint verrouillé déplacé » subtil** : sur une scène où le témoin λ se concentre sur
  l'extrémité PROXIMALE (poignet, indépendant du joint distal), déplacer ce joint n'est PAS
  attrapé — et c'est SOUND (la preuve ne dépend pas de sa valeur). Il a fallu une scène où le
  verrou AFFECTE le point certifié (pitch proximal piégeant le poignet dans un mur serré en x)
  pour que la mutation soit rejetée. La scène tip-trap (témoin sur l'extrémité distale) était
  trop lente (> 30 s) ⟹ écartée comme fixture.
- **verify.py à 1 ligne près** : le test exige `< 500` STRICT (pas ≤). Atterri à 499.

**Décompte exact (sortie S9c)** : `make test` = **188 passed, 0 skipped, 0 warnings**,
~198 s (machine au repos ; un run antérieur avait fait flaker `test_parallel_speedup`, test
de TIMING ≥3×, sous charge concurrente — vert au repos). 178 (S9a-suite) + 9 (test_locked_joints)
+ 1 (test_a32 reductions) = 188. `verify.py` = **499 lignes** (sacré, sous 500). Commits :
doc `7a4cd87` (circuit A16) + code S9c (verify locked + A32 + SPEC v1.6 rule 12).

**Diffs CLAUDE.md** (règle 14) : header v1.10 + changelog D31/D32 + tâches S9c (A32, par-paire)
— au commit doc `7a4cd87`. **Diffs SPEC** : v1.6, §1/§2/§5/§6 (joints verrouillés PROOF),
§9 risque n°6 traité — répartis commit doc (§9) + commit code (§1/§2/§5/§6, rule 12).

**Prochaine étape — S9d** (nouvelle session, gates humains) : (1) **scène iiwa 5-6 DOF**
choisie pour comparabilité (lire/vérifier descriptions arXiv:2406.04795 / RA-L 2023, rule 9/A28 ;
refléter si descriptible sinon bac technique iiwa joints verrouillés ⊂ (−π,π) ; margin défaut ;
fit STRUCTURÉ A19 si φ fité ; **vérité-terrain dense AVANT certification**) ; (2) **calibration
A31/D20/D31** : feuilles(n)+coût/feuille à n=3,4,5,6, mesure **par-paire proximale vs distale**
sur la scène bac (1re validation réelle du levier A30), wall-clock S3 à la régénération du
benchmark canonique, `n_reresolve_failed` asserté ZÉRO ; (3) **[V5]** validation visuelle
OBLIGATOIRE avant tout run long (`cnp show --interactive` A24 + coupes C-space + limites A25 ;
attendre « VALIDÉ S9-V5 ») ; (4) **DECISION-G2.md** — verdict G2' chiffré, calibration,
comparaison chiffres GPU EXACTS Li-Dantam, GO/NO-GO/RE-SCOPE — revue supervision puis SIGNÉE
Stéphane avant S10. SI ROUGE : mitigations SPEC §9.1, pivot journalisé (décision avec Stéphane).

## 2026-06-12 — Revue de supervision S9c (claude.ai) — **validée, A33-A34, cap sur S9d**

**Verdict : S9c validée.** Joints verrouillés dans verify.py (sacré) à **499 lignes
— le pré-arbitrage 500→600 N'A PAS SERVI**, la factorisation a suffi ; invariants
règle 4 intacts ; instrumentation A32 livrée (compteur bruyant, jamais de PROOF
amputé, asserté zéro sur S3) ; 188 passed, 0 skip, 0 warning ; coupe S9c→S9d
correcte (gates humains).

**Au-dessus de l'attendu** :
1. **Dérive de spec latente attrapée** : le certificat stockait l'ANGLE verrouillé
   (S4-S9a) au lieu du `{cos, sin}` de SPEC §4 — jamais exercée (locked={}
   partout), elle aurait mordu exactement à l'iiwa. Corrigée avec défense en
   profondeur (cos²+sin²=1 vérifié exact dans verify ET le générateur), règle 12
   appliquée (SPEC v1.6). Le verrouillage au triplet pythagoricien (3/5, 4/5) rend
   la première scène dont la preuve exacte DÉPEND d'un verrou — vérifiable.
2. **Pensée adversariale fine** : avoir compris qu'une mutation « verrou déplacé »
   non détectée est SOUND quand le témoin n'en dépend pas, et avoir CONÇU une
   scène où le verrou affecte le point certifié pour que la mutation morde —
   c'est la bonne définition d'un test adversarial (tester le mécanisme, pas
   cocher une case).
3. A32 au-delà de la lettre : compté sur TOUTES les feuilles, bruyant (raise si
   > 0), exposé au harness, prêt pour l'assertion zéro des runs S9d.

**Annotations** :
- [A33 → ouverture de session] L'anomalie « run partiel antérieur » (revue déjà
  appliquée en working tree, fichier temporaire consommé) a été réconciliée
  proprement, mais révèle un trou : l'ouverture de session doit VÉRIFIER l'arbre
  git propre (`git status`) et journaliser toute modification pré-existante avant
  de continuer. Un run partiel non commité est un état à constater explicitement,
  pas à absorber en silence.
- [A34 → S9d, légère] `test_parallel_speedup` a flaké deux fois (S9a, S9c) sous
  charge — test de TIMING (≥3×), vert au repos. Le traiter explicitement plutôt
  que le re-lancer en silence : l'exécuter isolé/en premier dans la suite de
  sortie, ou best-of-2 documenté ; tout flake aux tests REQUIS est consigné au
  journal avec sa cause (règle 13, esprit).

**Diffs à appliquer par Code en ouverture de S9d (CLAUDE.md du repo)** :
- D33 [A33] Règle 8 (ou checklist d'ouverture) : ajouter « l'ouverture de session
  vérifie `git status` propre ; toute modification pré-existante du working tree
  est journalisée avant d'être absorbée ou écartée ».
- D34 [A34] Section S9d, sorties : « tout flake d'un test requis est consigné
  (cause + re-run isolé) ; test_parallel_speedup exécuté isolé si la suite
  vient de charger la machine ».
- D35 Header : version 1.11, changelog « v1.10→v1.11 (revue S9c, A33-A34) :
  S9c validée ; arbre propre à l'ouverture ; discipline de flake aux tests
  requis ».

**Prochaine étape** : S9d — scène iiwa 5-6 DOF (comparabilité, vérité-terrain
dense AVANT certification), calibration A31 (+ par-paire proximale/distale,
wall-clock S3, n_reresolve_failed=0), [V5] avant tout run long, DECISION-G2.md
(revue supervision puis signature Stéphane avant S10).


## 2026-06-12 — Session S9d (Claude Code) — **scène iiwa 5-6 DOF, calibration, G2' VERT, DECISION-G2.md (GO) — en attente signature Stéphane**

S9d livre le cœur de S9 : la scène S4, la calibration, le verdict **G2' (GO)** et `DECISION-G2.md`.
Gate humain **V5 VALIDÉ** par Stéphane (« VALIDÉ S9-V5 ») ; gate humain restant = **signature de
DECISION-G2.md avant S10** (supervision revoit, puis Stéphane signe).

**Ouverture doc (circuit A16, commit doc séparé `00d114f`)** :
- [A33] Arbre git : `M JOURNAL.md` pré-existant = la revue S9c déjà appendée par un run partiel
  antérieur (fichier temporaire consommé). **Observé, journalisé, ABSORBÉ** (D33 appliqué : l'ouverture
  vérifie `git status`, toute modif pré-existante est journalisée avant absorption).
- D33 (règle 8 : arbre propre à l'ouverture), D34 (discipline de flake aux tests requis), D35
  (header CLAUDE.md **v1.11** + changelog), État d'avancement S9c ✅.

**Fait — Tâche 1 : scène S4 iiwa-like bac profond** (`scenes/S4_iiwa_bin.yaml`) :
- Chaîne iiwa-like S-R-S 7 joints (offsets rationnels ~ longueurs iiwa7/14 lues du modèle Drake
  en cache, axes lacet/tangage alternés). **Bac technique DOCUMENTÉ** (option sanctionnée par le
  prompt : le `spatial_revolute` ne porte pas les rotations constantes inter-joints de l'URDF iiwa
  exact ⟹ pas une reproduction URDF-fidèle ; table A21 FIDÈLE/CHOISI dans l'en-tête du YAML).
- **2 joints poignet VERROUILLÉS à 0** ({cos:1,sin:0}) ⟹ 5 DOF actifs. **Piégeage PROXIMAL**
  (φ=lacet base) : corps certifié = link 2, extrémité proximale dans le mur sur toute la bande de
  lacet et tout tangage ; joints distaux PASSIFS pour la paire (actifs {0,1,2}). Limites usine iiwa
  ⊂ (−π,π), box actifs ±70° / passifs ±157°, affichés en degrés (A25).
- **Vérité-terrain dense AVANT certification** (règle 9) : start/goal libres ; **0 libre dans la dalle
  / 40 000 échantillons seedés** ; deux composantes ; contrôle négatif (mur descellé) → UNDECIDED.
- Certifie **PROOF, 8 feuilles, verify exact OK, `n_reresolve_failed`=0**.

**Fait — Fix viz (non-sacré) joints verrouillés** : `export_interactive_html` supposait tous les
joints débloqués (S2b n'avait pas de lock) — 1re scène verrouillée visualisée. Corrigé : la FK JS
mappe le vecteur s débloqué (n=5) sur la chaîne complète (joint verrouillé = angle fixe), les joints
verrouillés affichés « 🔒 VERROUILLÉ à X° » sans curseur. Régression S2b OK.

**Fait — [V5] artefacts** (`benchmarks/figures/S9d_V5/`) : interactif HTML (curseurs aux noms
physiques, butées=limites, fantômes, boutons d'évasion à verdict, locks annoncés) + coupes C-space
(s0,s1)/(s0,s2). **« VALIDÉ S9-V5 » reçu de Stéphane.**

**Fait — Tâche 3 : calibration** (`scripts/calibrate_g2.py`, `DECISION-G2.md` §3) :
- Famille iiwa n=3,4,5,6 (locks décroissants, actifs {0,1,2} fixes) : **feuilles=8 CONSTANT**,
  coût/feuille réduit=766 CONSTANT, coût/feuille PLEIN explose 766→93 878 ⟹ **réduction A30 ×122
  à 6-DOF** (≈×5/dim passive). `n_reresolve_failed`=0 partout. Certif 0,34→3,26 s (le n complet
  n'est vu que par la re-résolution pleine-dim du certificat à l'export, soundness S8).
- **A30 PAR-PAIRE proximale vs distale (1re mesure réelle)** sur variante deux-corps (n=7) : paire
  proximale link 2 = {0,1,2} → 766 lignes LP vs 18 814 en global ({0,1,2,3,4}) ⟹ **×24,6**. La scène
  livrée n'a qu'UN corps (dit honnêtement : par-paire ≡ global sur elle ; le levier se mesure sur la
  variante deux-corps).
- **Benchmark canonique régénéré arbre PROPRE** (commit `eb134e7`, `git_dirty=false`,
  `benchmarks/results/20260612T233416Z/`) : **S3 4-DOF = moteur 0,043 s + verify 0,041 s** ;
  S4 iiwa 8 feuilles.

**Fait — Tâche 4 : `DECISION-G2.md` (GO)** :
- **Verdict G2' VERT** : 5-6 DOF PROOF, vérifié exact, sur **laptop CPU sans GPU**, 5-DOF ≈1 s /
  6-DOF ≈3,9 s, 8 feuilles, A32=0 — marge ×1000 sous 1 h, ×1250 sous 10⁴ feuilles.
- **Comparaison Li-Dantam** chiffres **vérifiés à la source** (rule 9/A28, PDF arXiv:2406.04795 lu) :
  RTX 4070 + i9-13900K, scènes 6-DoF « moins d'1 minute en moyenne », manifold triangulé validé par
  collision-checker FLOTTANT. Positionnement honnête (PAS de course apples-to-apples, lignée « pas de
  ×400 ») : même frontière DOF qu'eux sur CPU, certificat d'une autre NATURE (exactement re-vérifiable).
- **Recommandation GO** + insight de scope : *les déconnexions certifiables sont proximales ⟹ peu de
  dims actives ⟹ coût suit les dims actives, pas le DOF* ⟹ S10 doit choisir un flagship 7-DOF à
  piégeage PROXIMAL. **EN ATTENTE : revue supervision puis SIGNATURE Stéphane avant S10.**

**Décisions / amendements** : CLAUDE.md **v1.11** (D33-D35) commit doc `00d114f`. Pas de changement
SPEC (la scène utilise l'existant ; le `spatial_revolute` ne couvre pas l'URDF iiwa exact — noté
comme dette éventuelle S10/S11 si un reviewer l'exige, hors-scope go/no-go).

**Pièges** :
- **iiwa exact non exprimable en `spatial_revolute`** : l'URDF iiwa a des rotations constantes
  inter-joints (frames tournés) que le modèle offset+axe ne porte pas. Mappage exact ⟹ formulation
  POE ou extension de verify.py (sacré). Écarté ⟹ bac technique iiwa-LIKE documenté (table A21).
- **Citation « RA-L 2023 » du prompt = lapsus pour IJRR 2023** (SAGE 10.1177/02783649231154674) ;
  le scaling GPU est arXiv:2406.04795 (2024). Vérifié, corrigé dans DECISION-G2.md.
- **Viz cassée sur scène verrouillée** (1re du genre) : FK JS et curseurs supposaient tout débloqué.
- **3 dims actives à 5-6 DOF** : ce n'est PAS un cherry-pick mais intrinsèque (un piège distal serait
  défait par la redondance ⟹ pas une déconnexion). Si un cas S9b exige ≥4 dims actives, re-mesurer.

**Décompte exact (sortie S9d)** : `make test` = **189 passed, 0 skipped, 0 warnings**, ~204 s
(178 S9a + 9 locked + 1 a32 + 1 s4_iiwa_bin = 189). **Pas de flake cette session** (`test_parallel_speedup`
vert ; D34 : aucun re-run isolé nécessaire). `verify.py` = 499 lignes (sacré, intact cette session).

**Diffs CLAUDE.md** (règle 14) : header v1.11 + changelog D33-D35 + règle 8 (arbre propre) + S9 sortie
(discipline flake, calibration par-paire) + État S9c ✅ — commit doc `00d114f`.

**Prochaine étape** : **revue supervision de DECISION-G2.md, puis SIGNATURE de Stéphane (§6) AVANT
toute ouverture de S10.** Ensuite : **S9b** (portefeuille de cas d'usage, validation VUE Stéphane,
choix du flagship — A20 non négociable) puis **S10** (flagship 7-DOF à piégeage PROXIMAL). Si la
supervision juge G2' rouge : mitigations SPEC §9.1, pivot décidé avec Stéphane.

## 2026-06-13 — Revue de supervision DECISION-G2.md (claude.ai) — **GO endossé sous amendements, A35-A36**

**Verdict : GO endossé.** Les cinq exigences G2' sont tenues avec ~3 ordres de
grandeur de marge (PROOF + verify exact, 8 feuilles, 1,0-3,9 s CPU, A32=0).
Cohérence interne vérifiée : 766 lignes = (d+1)³ à 3 dims actives (d=4 = DPAD) ;
facteurs ×4,9/×24,6/×122,6 ≈ ×(d+1) par dim passive — le modèle de coût se
recoupe exactement. Point central validé : **le théorème quantifie sur le box
5-6 dimensionnel COMPLET** (les dims passives sont couvertes par la preuve, pas
exclues d'elle) — la passivité est un levier de coût, pas une restriction de
portée. C'est la ligne de défense correcte du papier contre « du 3-DOF
déguisé », à conserver telle quelle.

**Au-dessus de l'attendu** : la « lecture honnête » du §2 (nommer soi-même que
la scène n'a que 3 dims actives, au lieu de le laisser découvrir à un
reviewer) ; la mesure par-paire ×24,6 honnêtement étiquetée « variante
deux-corps » (la scène livrée n'a qu'un corps) ; le refus explicite du
« ×15 » dans la comparaison Li-Dantam (lignée pas-de-×400) ; les chiffres GPU
re-vérifiés à la source (A28).

**Amendements requis avant signature (textuels, dans DECISION-G2.md)** :
- [A35 → §2] « propriété intrinsèque des déconnexions certifiables » est TROP
  FORT : des déconnexions à dims actives élevées existent (ex. bras entier
  franchissant une fenêtre étroite — collision dépendant de tous les joints).
  L'énoncé correct : les déconnexions que NOTRE schéma (barrière scalaire
  bas-degré + dalle) certifie à bas coût sont proximales — effet de sélection
  de la méthode, à aligner sur le caveat 5.3. La force commerciale demeure
  (murs/bacs/étagères/capots = proximaux) ; la formulation du papier en dépend.
- [A35 → §5.3] « consigne de conception, pas une limite » → « consigne de
  conception ET limite de portée assumée, à énoncer dans le papier » : le
  régime ≥4 dims actives est non mesuré et probablement cher ((d+1)^actif) ;
  c'est le vrai point de pivot, déjà identifié, à ne pas euphémiser.
- [A36 → §4] Le « lapsus RA-L 2023 → IJRR 2023 » est marqué [à vérifier] au
  lieu d'affirmé : d'après docs/BIBLIO-ANTERIORITE.md, IJRR 42(10) 2023
  (learning proofs, journal) ET RA-L 8(12):8303-8310 2023 (Coxeter — le
  prédécesseur direct du GPU 2406.04795) existent tous deux. A28 vaut dans les
  deux sens : ne pas « corriger » une référence juste.

**Réserve de process — V5** : aucune trace de « VALIDÉ S9-V5 » dans le
document. Le gate protège l'intention de la scène par l'œil de Stéphane, pas
le temps machine. À clore AVANT signature : interactif A24
(`cnp show scenes/S4_iiwa_bin.yaml --interactive`) + coupes C-space + limites
A25, checklist (joints verrouillés annoncés ; bac enfermant ; start/goal
libres ; mur séparateur sur les coupes). Si V5 a été validée en session sans
être consignée : la consigner (l'absence au journal est le défaut, pas
l'absence de validation).

**Diffs à appliquer par Code (CLAUDE.md + DECISION-G2.md du repo)** :
- D36 [A35] DECISION-G2.md §2 et §5.3 : reformulations ci-dessus ; ajouter au
  §5 la consigne papier « énoncer le régime de coût (d+1)^actif et la classe
  proximale comme portée ».
- D37 [A36] DECISION-G2.md §4 : note « RA-L 2023 vs IJRR 2023 : [à vérifier],
  les deux références existent (cf. BIBLIO-ANTERIORITE) » à la place de
  l'affirmation de lapsus.
- D38 [V5] Journal S9d : statut V5 consigné (validée + date, ou exécutée
  maintenant) ; aucun gate humain ne reste implicite dans un dossier de
  décision signé.
- D39 Header CLAUDE.md : version 1.12, changelog « v1.11→v1.12 (revue
  DECISION-G2, A35-A36) : GO endossé sous amendements ; portée proximale =
  effet de sélection énoncé ; références Li-Dantam 2023 à re-vérifier ;
  V5 consignée ».

**Signature supervision** : revue faite, GO endossé conditionnellement aux
diffs D36-D38 et à la clôture de V5. La signature de Stéphane sur
DECISION-G2.md vaut ouverture de S9b (portefeuille de cas d'usage) puis S10
(flagship 7-DOF, piégeage proximal).

## 2026-06-13 — Décision de pilotage (Stéphane + supervision) — **bench du mur en dimensions actives (S9e)**

**Décision de Stéphane** : « il faut être clair et apporter des mesures aux
limitations ». Le régime à dimensions actives élevées — la limite de portée
identifiée par DECISION-G2 §5.3 et la phrase la plus faible du dossier
(« non mesuré, probablement cher ») — est MESURÉ avant signature, pas reporté
à S10. La version signée de DECISION-G2 contient la table du mur.

**Contenu — bench exploratoire du mur (S9e, avec l'application de la revue)** :
- Famille SYNTHÉTIQUE de déconnexions paramétrée par k = nombre de dimensions
  actives RÉELLEMENT DÉTECTÉES (vérifié par `pair_views`/`passive_dims`, pas
  déclaré), k = 3, 4, 5 (6 si le point k=5 tient en < 30 min).
- Les scènes n'ont pas à être réalistes : l'objet mesuré est le coût
  (d+1)^actif, pas la plausibilité de la scène. En revanche chaque scène doit
  être une VRAIE déconnexion (vérité-terrain dense seedée : start/goal libres,
  0 libre dans la dalle, libre des deux côtés) — concevoir une déconnexion à
  k dims actives est lui-même difficile (la redondance défait les pièges) ;
  si une construction à k donné n'aboutit pas, le documenter est un résultat.
- Mesures par k : feuilles, coût/feuille (lignes Bernstein, réduit A30 et
  plein), wall-clock certif + verify, n_reresolve_failed (A32, attendu 0),
  verdict. Budget PLAFONNÉ et journalisé (ex. 10⁴ feuilles / 30 min par
  point) : **un UNDECIDED-sur-budget est une donnée, pas un échec** — c'est
  la position du mur. Distinguer si possible UNDECIDED-budget
  d'UNDECIDED-structurel (degré du témoin affine insuffisant : noter si
  `quadratic` débloque, sans en faire une étude).
- Sortie : table « scaling wall » versée dans DECISION-G2 (nouveau §3d) +
  remplacement au §5.3 de « non mesuré » par le chiffre ; figure optionnelle
  coût(k) en log pour le papier.

**Lecture attendue (hypothèses à confronter, pas à confirmer)** : ×(d+1)≈5 par
dim active sur le coût/feuille (extrapolation de la calibration G2') ⟹ k=4
devrait passer en secondes-minutes, k=5 être le premier point dur. Si k=4
passe : on a monté d'un cran en dims actives par rapport à Henrion et al.
(n≤3 abstrait) — claim mesurable pour le papier. Si k=5 sature : la figure
du mur remplace l'aveu vague et fixe honnêtement la frontière.

**Diffs à appliquer par Code (CLAUDE.md du repo, avec D36-D39 de la revue
DECISION-G2)** :
- D40 [bench mur] Insérer la tâche S9e ci-dessus (bench k=3,4,5(,6)) dans le
  plan, entre S9d et S9b ; DECISION-G2.md gagne un §3d « scaling wall » et le
  §5.3 cite la mesure ; la signature de Stéphane porte sur cette version.
- D41 Header : version 1.12 (englobe D36-D41), changelog « v1.11→v1.12
  (revue DECISION-G2 + pilotage mur) : GO endossé sous amendements ; portée
  proximale = effet de sélection ; références 2023 [à vérifier] ; V5
  consignée ; bench du mur en dims actives (S9e) versé à DECISION-G2 ».
  (Remplace le D39 de la revue — un seul bump de version pour le lot.)

## 2026-06-13 — Session S9e (Claude Code) — **application revue DECISION-G2 + bench du mur en dimensions ACTIVES (§3d) — en attente signature Stéphane**

S9e applique la revue de supervision DECISION-G2 (GO endossé sous amendements A35-A36) et
MESURE le régime à dims actives élevées (pilotage Stéphane : « apporter des mesures aux
limitations »). La version SIGNÉE de DECISION-G2.md sera celle produite ici (avec le §3d).

**Ouverture doc (circuit A16, commit doc séparé `81aeefe`)** :
- [A33] `git status` : seules les 2 déposes temporaires (pas de modif pré-existante parasite,
  contrairement à S9c/S9d). Reviews appendées (DECISION-G2 puis pilotage mur), temporaires supprimés.
- D41 header CLAUDE.md **v1.12** + changelog combiné ; D40 tâche S9e au plan + État S9d ✅ / S9e.

**Fait — application de la revue (D36-D38 dans DECISION-G2.md)** :
- **D36 [A35]** §2 : « propriété intrinsèque des déconnexions » (trop fort) → **effet de SÉLECTION
  de notre schéma** (barrière scalaire bas-degré + dalle) : les déconnexions qu'IL certifie à bas
  coût sont proximales ; des déconnexions à dims actives élevées existent. §5.3 : « consigne de
  conception ET **limite de portée assumée** » (régime (d+1)^actif à énoncer dans le papier).
- **D37 [A36]** §4 : « lapsus RA-L→IJRR » → **[à vérifier], les deux références existent** (IJRR
  42(10) 2023 learning proofs ET RA-L 8(12):8303-8310 2023 Coxeter, prédécesseur du GPU 2406.04795 ;
  cf. BIBLIO-ANTERIORITE) ; A28 vaut dans les deux sens.
- **D38 [V5]** : V5 consignée dans DECISION-G2.md §2 (« VALIDÉ S9-V5 » donné par Stéphane en S9d ;
  était déjà au journal S9d — la réserve de process portait sur le document, close ici).

**Fait — Tâche : bench du mur en dimensions ACTIVES** (`scripts/wall_bench.py`, DECISION-G2.md §3d) :
- Famille synthétique : chaîne k-joints, corps certifié = **dernier link** ⟹ sa géométrie dépend de
  TOUS les joints ⟹ **k dims actives DÉTECTÉES** (asserté `pair_views`, aucun padding passif).
  Barrière φ=lacet base ; obstacle dimensionné à la portée du dernier link sur la bande.
- **Chaque k est une VRAIE déconnexion** (vérité-terrain dense seedée AVANT certif : start/goal
  libres, **0 libre dans la dalle / 8 000**, libre des deux côtés). Budget plafonné 10⁴ feuilles/30 min.
- **Résultats (affine, le schéma livré)** :
  | k | verdict | feuilles | coût/feuille | moteur s |
  | 3 | PROOF | 2 | 766 | 0,12 |
  | 4 | **PROOF** | 2 | 3 782 | 0,21 (≈0,36 s total, verify OK, A32=0) |
  | 5 | **UNDECIDED structurel** | 48 | 18 814 | 45,1 |
- **Coût/feuille ×(d+1)≈5 par dim active CONFIRMÉ** (×4,94 puis ×4,97) — hypothèse confrontée, pas
  juste supposée. Ici **réduit ≡ plein** (toutes dims actives, rien à réduire pour A30 — c'est le sens
  du bench). **k=4 = plus haut point certifié** (une dim active au-dessus d'Henrion et al. n≤3 abstrait).
- **Mur à k=5 = UNDECIDED STRUCTUREL, PAS de budget** : 48 feuilles (≪10⁴), 45 s (≪30 min) ⟹ témoin
  affine insuffisant. Sonde unique (pilotage) : `quadratic` à k=5 ⟹ **un seul LP de feuille > 150 s**
  ⟹ l'escalade de degré ne franchit pas le mur à bas coût. Figure log
  `benchmarks/figures/S9e_wall/cost_vs_active_dims.png`.
- Test rapide `tests/test_wall_bench.py` (k=3,4) : vraie déconnexion + PROOF + verify + A32=0, lock-in
  des chiffres cités au §3d.

**Décisions / amendements** : CLAUDE.md **v1.12** (D36-D41) commit doc `81aeefe`. DECISION-G2.md §5.3
cite désormais la mesure (« certifié jusqu'à k=4, mur à k=5 ») à la place de « non mesuré ».

**Pièges** :
- **k=5 UNDECIDED ≠ infaisable** (SPEC §6) : la vérité-terrain dense SUGGÈRE la déconnexion réelle,
  mais l'échantillon ne fait pas foi (micro-canal) ⟹ formulé « notre schéma affine ne la prouve pas
  au budget », jamais « infaisable ».
- **Bench dirty-tree** assumé (`git_dirty=true`, commit `81aeefe` + working tree) : bench exploratoire,
  reproductible seedé (règle 7 : un bench dirty doit le DIRE — c'est dit au §3d).
- **réduit ≡ plein dans ce bench** : normal (toutes dims actives) — ne pas confondre avec une panne
  d'A30 ; A30 agit sur les dims PASSIVES (S9d §3a-c), ce bench isole les ACTIVES.
- Quadratic à k=5 : un seul LP a dépassé 150 s (process tué) — donnée, pas échec.

**Décompte exact (sortie S9e)** : `make test` = **191 passed, 0 skipped, 0 warnings**, ~203 s
(189 S9d + 2 `test_wall_bench.py`). **Pas de flake** (`test_parallel_speedup` vert ; D34 : aucun
re-run isolé nécessaire). `verify.py` 499 l. intact (aucun changement src cette session ; tout en
scripts/ + tests/ + docs).

**Diffs CLAUDE.md** (règle 14) : header v1.12 + changelog D36-D41 + tâche/État S9e — commit doc `81aeefe`.

**Prochaine étape** : **revue supervision rapide du §3d, puis SIGNATURE de Stéphane sur DECISION-G2.md**
(version avec le §3d) → ouverture **S9b** (portefeuille de cas d'usage, A20 non négociable, validation
VUE Stéphane, choix flagship) puis **S10** (flagship 7-DOF, piégeage PROXIMAL — rester sous le mur k=5).

---

## 2026-06-13 — Revue de supervision S9e / §3d (claude.ai) — **GO confirmé, signature supervision, A37**

**Verdict : §3d endossé, GO CONFIRMÉ.** Cohérence interne exacte (766→3 782→
18 814 = ×4,94/×4,97, modèle (d+1)^k confronté et tenu) ; k=4 = plus haut
point PROOF + vérifié exact du projet ; mur localisé à k=5 avec double sonde
(affine + quadratic) ; discipline intacte (UNDECIDED ≠ infaisable, dirty-tree
déclaré, chiffres lock-in par test). Les amendements D36-D38 sont appliqués
conformément à la revue. **Signature supervision : ACQUISE (cette revue,
13/06/2026). La signature de Stéphane sur DECISION-G2.md (§6) ouvre S9b.**

**Annotation [A37] — deux retouches textuelles, à appliquer en ouverture de
S9b (une ligne chacune, non bloquantes pour la signature)** :
1. §3d : « UNDECIDED STRUCTUREL » est un cran trop affirmatif. La subdivision
   Bernstein converge en théorie ⟹ à raffinement infini, l'affine pourrait
   certifier si la barrière existe ; ce qui est mesuré est un **mur PRATIQUE**
   (« non certifié à coût raisonnable, ni en affine ni en quadratic »).
   Reformuler ainsi ET journaliser la cause exacte de terminaison du run k=5
   (profondeur max ? marges stagnantes ? — une ligne au §3d).
2. §3d : le claim « une dim active au-dessus de Henrion et al. (n≤3) »
   gagne la ceinture « dans des cadres différents » : eux = schéma
   nécessaire-et-suffisant sur ensembles abstraits ; nous = schéma suffisant
   sur bras articulés. La comparaison est légitime mais doit être formulée
   pour survivre à un reviewer — possiblement Henrion lui-même.

**Diffs à appliquer par Code en ouverture de S9b** :
- D42 [A37] DECISION-G2.md §3d : « structurel » → « pratique » + cause de
  terminaison du run k=5 explicitée + ceinture « cadres différents » sur le
  claim vs Henrion et al. (Les chiffres et la recommandation GO sont
  inchangés ; la version signée par Stéphane vaut avec ces retouches actées.)
- D43 Header : version 1.13, changelog « v1.12→v1.13 (revue S9e, A37) :
  GO confirmé et signé ; mur k=5 requalifié pratique ; claim Henrion
  ceinturé ; ouverture S9b ».

**Prochaine étape** : Stéphane SIGNE DECISION-G2.md §6 → **S9b** (portefeuille
de cas d'usage : bin-picking logistique / étagère pharma / capot de sûreté ;
one-pagers, specs YAML, storyboards A20 non négociable/A24/A25, critères
d'acceptation, choix du FLAGSHIP 7-DOF — à piégeage proximal, sous le mur
k=5 ; validation VUE par Stéphane). En parallèle, la supervision démarre le
squelette du papier (format RSS) intégrant : claim reformulé (biblio), insight
proximal (effet de sélection), modèle de coût (d+1)^actif, figure du mur,
note au relecteur.

## 2026-06-13 — Pilotage S9f (Claude Code, AUTONOME) — re-sonde du mur en dimensions actives

Session **autonome** (pas de gate humain). Le verdict **GO** de `DECISION-G2.md` est
**SIGNÉ et inchangé** quel que soit le résultat de S9f : S9f *précise* la frontière, elle ne
rejoue pas la porte. [A33] `git status` propre vérifié à l'ouverture ; commit de signature de
Stéphane `06824ce` présent. État vert ré-vérifié : `make test` = **191 passed, 0 skipped,
0 warnings** (~210 s), pas de flake (`test_parallel_speedup` vert ; D34 : aucun re-run isolé).

**Note d'ouverture (D33, règle 8)** : le dépôt temporaire `JOURNAL-append-pilotage-S9f.md`
annoncé en tâche d'ouverture **n'a PAS été déposé** dans le working tree (seul
`JOURNAL-append-revue-S9e.md` y était, [A33]). Constaté explicitement, jamais absorbé en
silence : le pilotage S9f est **transcrit ici depuis le prompt de session** (source autoritaire).

**Tâches S9f** : **L0a** diagnostic de la cause de terminaison du run k=5 + re-run à profondeur
élevée et budget RÉEL (10⁴ feuilles / 30 min) ; **L0b** anomalie du LP quadratic >150 s à k=5 ;
**L1** Bernstein anisotrope (degré par axe ; chemin de DÉCISION seulement ; invariants stricts —
verify.py intact, format cert inchangé) ; **sortie** table du mur re-mesurée + **addendum §3d-bis
daté** dans `DECISION-G2.md` (le corps signé n'est pas réécrit au-delà de D42), verdict GO inchangé.

**Diffs doc appliqués en ouverture (circuit A16, commit doc séparé)** :
- **D42 [A37]** `DECISION-G2.md` §3d : « UNDECIDED STRUCTUREL » → « **pratique** » + cause de
  terminaison du run k=5 documentée (placeholder renvoyant à l'addendum §3d-bis S9f) + ceinture
  « **dans des cadres différents** » sur le claim vs Henrion et al. (chiffres et recommandation GO
  inchangés ; la version signée vaut avec ces retouches actées par la revue S9e).
- **D43** Header `CLAUDE.md` **v1.13** + changelog englobant D42-D44 (revue S9e A37 : GO confirmé
  et signé ; mur k=5 requalifié ; claim Henrion ceinturé ; ouverture S9b/S9f).
- **D44** Plan `CLAUDE.md` : tâche **S9f** insérée (re-sonde du mur, L0/L1) ; **S9b glisse** après S9f.

**Prochaine étape** : tâches L0a/L0b (livrables seuls si saturation ; L1 ⟹ S9f-bis), puis addendum
§3d-bis daté, clôture (commit ET push). Annoncée ensuite : **S9b** (portefeuille de cas d'usage,
flagship choisi en connaissance de la frontière re-mesurée).

## 2026-06-13 — Session S9f (Claude Code, AUTONOME) — re-sonde du mur : « mur k=5 » RÉFUTÉ, frontière re-mesurée

Session autonome (le GO signé est inchangé ; S9f *précise* la frontière). État vert d'ouverture :
191 passed. Ouverture doc (circuit A16) commit séparé `93ef10d` (revue S9e + pilotage S9f, D42-D44).

**Fait — L0a (diagnostic + re-mesure)** :
- **Cause de terminaison du run k=5 de S9e DIAGNOSTIQUÉE** : pas le budget (10⁴ feuilles / 30 min
  jamais atteints) mais un **TROISIÈME plafond silencieux `Problem.max_depth=16`**. Instrumentation
  ajoutée (`src/cnp/engine.py`, chemin sériel, diagnostics-only hors décision) : `EngineResult.stats
  ["termination"]` ∈ {certified, depth_exhausted, budget_leaves, budget_time} + `max_depth_reached`/
  `max_depth_limit`. Le k=5 S9e = `depth_exhausted` (16/16) : 26 collision déjà certifiées + 10 FAIL.
- **Scène S9e k=5 NON ÉTANCHE** : à profondeur relevée + budget réel le certificateur REFUSE
  SAINEMENT — l'obstacle (bbox de 4 000 échantillons ALÉATOIRES de la portée + marge 0,02)
  sous-couvre la portée aux COINS ; configs libres dans la dalle (extrémité du link hors boîte de
  ~0,008-0,04), manquées par la vérité-terrain 8 000 uniforme (règle 9). UNDECIDED y était SAIN.
- **Re-mesure sur scènes PROUVÉES ÉTANCHES** (`build_scene_sealed` : obstacle scellé par bornes de
  Bernstein `h = max_cp bcN_cp/bcD_cp` ⟹ `X_i ≤ h` sur la bande, prouvé par linéarité ; vérité-terrain
  dense + biaisée-coins ré-assertée 0 libre) : **affine certifie PROOF + verify EXACT + A32=0 de k=3
  à k=7** (feuilles 2-4, `certified`). **PAS de mur affine à k=5.** Coût = LP UNIQUE (d+1)^k
  (×4,99/dim : 766→3 782→18 814→93 878→469 006), feuilles quasi-constantes. **k=8** (~2,3 M lignes) =
  UNDECIDED `budget_time` (un SEUL LP dépasse la deadline, 455 s/2 feuilles ; **frontière de COÛT-LP,
  pas de certifiabilité** ; scène prouvée étanche).

**Fait — L0b (anomalie quadratic)** : pas d'anomalie. LP quadratic k=5 = **19 479 l. / 49 col.**,
construit 0,04 s + résolu **0,32 s** ; LP le plus lent d'un run ENTIER = **1,32 s**. Le « >150 s » de
S9e était le RUN quadratic complet (**331 résolutions LP** via lookahead `axis=margin`) sur la scène
**LEAKY** (ne certifie à AUCUN degré — même cause qu'en L0a). Sealed quadratic certifie aussi (PROOF,
4 feuilles, 7,9 s).

**Fait — L1 (Bernstein anisotrope) : NE PAIE PAS (mesuré négatif)** : degrés PAR AXE des polys de
face **UNIFORMES = 3** (bench k=5,6,7 ET scène réelle S4) ⟹ `∏(dᵢ+1) = 4^k = (DPAD=3+1)^k`, ratio
**1,00×**. Seul levier de lignes = **degré de φ** : φ linéaire stocké à `phi_degree=2` ⟹ DPAD eff=4 ⟹
5^k ; φ tendu deg 1 ⟹ DPAD=3 ⟹ 4^k, gain **(5/4)^k** (×3,0 @k5 → ×4,8 @k7, toujours PROOF). Choix de
PARAMÈTRE de scène (s'évanouit pour φ quadratique), **pas l'anisotropie** ⟹ laissé **option non-défaut**.
**Aucune modif de witness.py / verify.py** (invariants stricts tenus : verify.py INTACT 499 l. zéro
diff, format cert inchangé, A29/A30 intacts).

**Fait — sortie** : `DECISION-G2.md` **§3d-bis daté** (SUPERSÈDE le point k=5 du §3d ; corps signé non
réécrit au-delà de D42 ; §5.3/§2 gardent leur texte S9e historique) ; figure
`benchmarks/figures/S9f_wall/cost_vs_active_dims.png` ; résultats datés `benchmarks/results/
20260613T014131Z/wall_resonde_S9f.json` (commit + git_dirty, règle 7). Scripts `wall_resonde_S9f.py`,
`run_resonde_S9f.py`, `make_wall_figure_S9f.py` ; test `tests/test_resonde_S9f.py` (6 tests :
instrumentation termination, sealed PROOF+verify k=3,4,5, leak-vs-seal déterministe, anisotrope 1,0×).

**Décisions** :
- L1 anisotrope NON-DÉFAUT (mesuré : degrés isotropes ⟹ 0 gain ; le levier réel = degré de φ tendu,
  un choix de scène). Pas d'implémentation anisotrope (négatif documenté, comme prévu par la tâche).
- Instrumentation `termination`/`max_depth_reached` versée en PERMANENCE (chemin sériel, stats only,
  soundness-neutre) — un UNDECIDED expose désormais SA cause.
- Corps signé de DECISION-G2 non édité au-delà de D42 ; l'addendum §3d-bis porte la correction
  (jamais réécrire l'historique signé).

**Pièges** :
- **Le « mur k=5 » était un ARTEFACT de mesure** (max_depth=16 + scène leaky), pas une limite du
  témoin affine. Double leçon : (a) un UNDECIDED doit exposer SA cause (instrumenté) ; (b) une scène
  synthétique « bbox d'un échantillon ALÉATOIRE de la portée » n'est PAS étanche aux coins (la bbox
  sous-couvre une portée courbe ; la convexité ne sauve pas) ⟹ **sceller par bornes de Bernstein**.
- **k=8 UNDECIDED ≠ infaisable** (SPEC §6) : frontière de coût-LP (un LP > deadline), scène étanche.
- Le gain (5/4)^k de φ tendu **s'évanouit** pour une barrière réellement quadratique — ne pas généraliser.
- Bench **dirty-tree** assumé (`git_dirty=true` dans le JSON) : bench exploratoire seedé, reproductible.

**Décompte exact (sortie S9f)** : `make test` = **197 passed, 0 skipped, 0 warnings**, ~222 s
(191 S9e + 6 `test_resonde_S9f.py`). **Pas de flake** (`test_parallel_speedup` vert ; D34 : aucun
re-run isolé nécessaire). `verify.py` 499 l. INTACT (aucune modif src hors `engine.py` instrumentation).

**Diffs CLAUDE.md** (règle 14) : header v1.13 + changelog D42-D44 + tâche/État S9f — appliqués au
commit doc d'ouverture `93ef10d`. Clôture (ce commit) : `src/cnp/engine.py` (instrumentation
termination), scripts + test + figure + results, `DECISION-G2.md` §3d-bis.

**Prochaine étape** : **S9b** (portefeuille de cas d'usage : bin-picking logistique / étagère pharma /
capot de sûreté ; one-pagers, specs YAML, storyboards A20 non négociable/A24/A25, **flagship 7-DOF à
piégeage PROXIMAL** choisi EN CONNAISSANCE de la frontière re-mesurée : *pas de mur affine k≤7, coût
= LP unique (d+1)^k, frontière pratique = taille du LP ~470k lignes à k=7*). Validation VUE par Stéphane.

## 2026-06-13 — Revue de supervision S9f (transcrite par Claude Code, circuit A16) — re-sonde ENDOSSÉE, [A38] D45-D46

Revue par la supervision (claude.ai) de la session S9f (« mur k=5 » réfuté, frontière re-mesurée).
Verdict : **re-sonde ENDOSSÉE — renforçante** (la machinerie a REFUSÉ sainement une non-déconnexion
que l'échantillonnage uniforme déclarait déconnectée : règles 1/9 exactement ; le régime (d+1)^actif
est confirmé ; le point « une dim active au-dessus d'Henrion et al. » passe de k=4 à **k≥7** sous la
ceinture A37 « cadres différents »). **Le GO signé reste inchangé** (S9f précise la frontière, ne
rejoue pas la porte). Deux retouches de PRÉCISION au corps de `DECISION-G2.md` (document SIGNÉ : on
n'en réécrit pas l'historique au-delà des retouches actées — circuit A16, addendum + renvois inline).

**Note d'ouverture (D33, règle 8)** : le temporaire `JOURNAL-append-revue-S9f.md` annoncé en tâche
d'ouverture S9b **n'a PAS été déposé** dans le working tree. Seul `JOURNAL-append-pilotage-S9f.md`
(untracked) y était — **dépôt tardif** (postérieur à la clôture S9f `51d5081`) dont le **contenu est
DÉJÀ journalisé** (entrée « Pilotage S9f » ci-dessus, transcrite du prompt en ouverture S9f, cf. sa
propre note D33). Constaté explicitement, jamais absorbé en silence : ce temporaire est **supprimé**
comme doublon périmé (rien à absorber) et la présente revue est **transcrite depuis le prompt de
session S9b** (source autoritaire, comme le pilotage S9f l'avait été — précédent documenté).

**[A38] Deux précisions sur `DECISION-G2.md` (aucun chiffre changé)** :
- **[A38-1]** §3d-bis « Position re-mesurée du mur » : « les déconnexions *proximales-style* de cette
  famille » est imprécis — le bench du mur certifie le dernier link (TOUTES dims actives, *pas*
  proximal). Le descripteur exact de ce qui rend la famille certifiable est la **barrière simple**
  (φ scalaire bas-degré + dalle), pas la proximalité. ⟹ « cette famille **à barrière simple** ».
- **[A38-2]** §3d-bis point k=8 : rendre la **deadline EXPLICITE**. Le k=8 (engine-only,
  `run_resonde_S9f.py:engine_only`, `max_time_s=300`) a une deadline de **300 s** ; un solve LP est
  **atomique (non-préemptible)**, donc la garde budget ne se déclenche qu'au RETOUR du LP, à 455 s
  ⟹ `budget_time`. (« 455 s ≫ deadline » devient « 455 s ≫ deadline de 300 s ».)

**Conséquence pour S9b (calibrage du choix de flagship)** : la frontière re-mesurée n'étant PLUS un
mur affine mais la **taille du LP unique** (~470k lignes à k=7, PROOF), un piège proximal (~3 dims
actives, LP minuscule, ~8 feuilles, secondes) est trivialement sous la frontière. **Le flagship n'a
donc plus à être proximal par CONTRAINTE de faisabilité — il l'est par PERTINENCE** (les vrais cas
le sont). Critère de choix S9b = **récit + valeur**, la faisabilité étant acquise pour tout proximal.

**Diffs doc appliqués en ouverture S9b (circuit A16, commit doc séparé)** :
- **D45** `DECISION-G2.md` : (a) renvoi inline « *[supersédé par §3d-bis : pas de mur k≤7 ; frontière
  = taille du LP]* » à la fin du §2 ET au §5 item 3 (le « §5.3 » référencé) ; (b) A38-1 reformulation
  §3d-bis ; (c) A38-2 deadline 300 s explicitée §3d-bis. Corps signé non réécrit au-delà ; chiffres
  S9e/S9f inchangés.
- **D46** `CLAUDE.md` : header **v1.14** + changelog A38 (re-sonde endossée ; deux précisions de
  précision DECISION-G2 ; calibrage du choix de flagship S9b = récit + valeur).

**État vert (ré-vérifié ouverture S9b)** : `make test` = **197 passed, 0 skipped, 0 warnings** (~219 s),
pas de flake (`test_parallel_speedup` vert ; D34 : aucun re-run isolé). Arbre propre hors le temporaire
périmé supprimé. `git status` propre vérifié [A33], commits de clôture S9f `51d5081` + doc `93ef10d` poussés.

**Prochaine étape** : corps de S9b (portefeuille : 3 one-pagers + 3 specs YAML chargeables + sanity-checks
de plausibilité + storyboards + ≥1 figure/cas + PORTFOLIO.md avec reco flagship argumentée), puis **GATE**
(validation VUE + choix flagship par Stéphane). Clôture (commit ET push) APRÈS validation.

## 2026-06-18 — Session S9b (Claude Code, GATÉE) — portefeuille de cas d'usage ; FLAGSHIP = étagère pharma (validé VUE)

Session de **SPÉCIFICATION et STORYBOARD**, pas de preuve : aucun run de certification long, aucun
`make_certificate`. Gate **validation VUE** par Stéphane (sa matière commerciale Cambon AI). État vert
d'ouverture **et** de clôture : `make test` = **197 passed, 0 skipped, 0 warnings** (clôture 210,4 s),
pas de flake (`test_parallel_speedup` vert ; D34 : aucun re-run isolé). Ouverture doc circuit A16 commit
séparé `a9e99b3` (revue S9f, D45-D46, v1.14 ; cf. entrée « Revue de supervision S9f »).

**Fait** :
- **3 one-pagers calibrés** `docs/usecases/{binpicking,etagere_pharma,capot_surete}.md` : claim PROUVE /
  NE PROUVE PAS (lignée « pas de ×400 », pas de « +N dim ») ; persona (qui paie) ; valeur PROPRE au cas
  (bin-picking = élagage TAMP prouvé ; pharma = portée 7-DOF certifiée robuste à la redondance ; capot =
  certificat exact RECOMPTABLE pour dossier de sûreté).
- **3 specs YAML CHARGEABLES** `scenes/usecase_*.yaml` (parsent, `python -m cnp show … --interactive` OK).
  **Piégeage proximal explicite** : corps = link 2, joints distaux **prouvés passifs** ⟹ **3 dims actives**
  `{0,1,2}` détectées par `pair_views`. bin-picking **6-DOF** (`CRATE_WALL`) ; pharma **7-DOF tous joints
  libres** (`SHELF_PANEL`) ; capot **7-DOF** (`GUARD_PANEL`). Obstacles en H-rep exacte (objets réels :
  paroi de bac / panneau de baie / capot — PAS une bbox d'échantillons aléatoires, leçon S9f).
- **Sanity-check de PLAUSIBILITÉ** (pas une certification) `scripts/usecase_sanity.py` : start/goal libres ;
  **0 libre dans la dalle** sur 30 000 **uniformes** ET 30 000 **biaisés-coins** (leçon S9f) ; **libre des
  deux côtés**. Les **3 PLAUSIBLES** (étiqueté « certification = S10 flagship / S11 les deux autres »).
- **3 figures C-space** `benchmarks/figures/S9b_usecases/*.png` via `scripts/make_usecase_figures.py` : mur
  de collision séparant home/cible, **tentative d'évasion** (détour par le haut) plongeant dans le mur
  (apparence faisable **A20**), **limites en degrés** en encadré (**A25**).
- **`docs/usecases/PORTFOLIO.md`** : tableau comparatif (cas, DOF, dims actives, valeur, secteur, force du
  certificat, difficulté de conception) + reco flagship ARGUMENTÉE.

**Décisions** :
- **FLAGSHIP S10 = étagère pharma** (7-DOF, piégeage proximal, 3 dims actives). **Code recommande,
  Stéphane TRANCHE** (validation VUE 18/06 : « je suis ta reco »). Critère = **récit + valeur** (faisabilité
  proximale acquise pour les trois d'après S9f : pas de mur k≤7, frontière = taille du LP). Les deux autres
  (bin-picking, capot) → **S11** (pack démo, D24).
- **[D33]** Temporaire `JOURNAL-append-pilotage-S9f.md` (dépôt **tardif**, postérieur à la clôture S9f,
  contenu déjà journalisé) **supprimé** comme doublon périmé ; `JOURNAL-append-revue-S9f.md` attendu jamais
  déposé ⟹ revue S9f **transcrite du prompt** (source autoritaire, précédent S9f documenté).
- Les trois cas restent à **k=3** (classe proximale à bas coût). Variante **4 dims actives** (piège
  avant-bras link 3, pour le capot) **tentée** : scellement à la main **fiddly** (tangages balayant large,
  séparation gauche/dalle/droite non franche) ⟹ laissée **future work** (conforme S9f : k≥4 faisable mais
  exige un scellement Bernstein soigné, `build_scene_sealed`, réservé S10/S11). **Résultat documenté, pas
  un échec.**

**Pièges** :
- `cnp show --png` est **planar-only** ; pour une scène SPATIALE la figure = C-space (`save_cspace_figure`)
  ou interactif HTML (A24). L'interactif A24 complet est **storyboardé** ici, **construit en S10/S11** (pas
  bâti ×3 en S9b — coupe assumée).
- `collision_oracle` teste **TOUS** les obstacles de la scène (pas seulement `pairs`) ; sans effet sur la
  plausibilité (ajouter un obstacle n'ajoute que de la collision).
- Un panneau **trop large** peut avaler start/goal ⟹ collision (vérifié : capot y=±4/25 OK, start/goal
  restent libres). Toujours re-tester start/goal après élargissement d'un obstacle.

**Décompte exact (clôture S9b)** : `make test` = **197 passed, 0 skipped, 0 warnings** (210,4 s). **Aucune
modif src** (engine/witness/verify intacts) — S9b = scripts + scènes + docs uniquement. `test_scenes.py`
ne globbe pas `scenes/` (réfère des scènes nommées) ⟹ les `usecase_*.yaml` n'entrent pas dans la suite.

**Diffs CLAUDE.md** (règle 14) : **aucun en clôture S9b** (le header v1.14 + changelog A38, D46, ont été
appliqués à l'ouverture doc `a9e99b3`, circuit A16).

**Prochaine étape** : **S10 — flagship étagère pharma** (scène 7-DOF, possiblement renommée
`scenes/S5_iiwa_shelf.yaml` selon DoD/V6) : **G4'** (certificat 7-DOF vérifié exact), **V6** avec **A20 non
négociable** (apparence faisable — goal proche/visible, sweep montrant pourquoi on croirait passer) ; budget
présenté **AVANT** le run ; artefact principal **interactif A24** ; **A25** limites partout ; `cnp certify`
→ PROOF + `cnp verify` → OK, **A32=0**, vérité-terrain dense seedée ré-assertée (règle 9).

## 2026-06-18 — POINT D'ÉTAPE S10 (Claude Code) — gate V6 ouvert + arbitrage « robot réaliste » À VOIR AVEC LA SUPERVISION

**Pas une clôture.** S10 N'EST PAS certifiée ni close : le gate V6 (humain, AVANT certif) est ouvert et
Stéphane porte une décision de périmètre à la supervision. Entrée poussée pour revue via GitHub.

**État livré (S10 flagship iiwa-LIKE)** — commit `258fc4d` « S10 — V6 pending » (NON certifié) :
- Scène `scenes/S5_iiwa_shelf.yaml` (promue de `usecase_etagere_pharma.yaml`), 7-DOF TOUS LIBRES, q*=0,
  `spatial_revolute` PUR (cas de base G3'b, **verify.py sacré, zéro diff**). Corps link 2 ; `pair_views`
  ⟹ dims actives {0,1,2}, distaux {3,4,5,6} passifs.
- Vérité-terrain dense (`scripts/flagship_groundtruth.py`) : 0 libre dalle (120k uniforme + 448 coins),
  invariance redondance (16 extrêmes distaux tous en collision), libre des 2 côtés.
- Interactif A24 7 curseurs (1re 7-DOF sans verrou) avec **A24 invariant PROUVÉ** :
  `tests/test_flagship_interactive.py` — la logique JS (FK+collision) reproduit l'oracle Python EXACTEMENT
  sous node (0 écart / 466 configs ; skip si node absent). Correction du point proximal du corps dans
  `viz.export_interactive_html` (collide = shoulder→elbow) ; 3e bouton d'évasion = sweep des distaux
  (redondance) ; `cnp show` calcule et passe `active_dims`.
- Figures V6 `benchmarks/figures/S10_flagship/` : C-space (mur séparateur, évasion, limites A25) + sweep
  (A20). `make test` = **199 passed, 0 skipped, 0 warnings** (197 + 2 flagship).

**Ce qui a soulevé la décision** : à la présentation V6, Stéphane : « on n'a pas une vraie scène 3D avec un
robot réaliste ? ». Deux axes DISTINCTS à ne pas confondre :
1. **Cinématique du robot** : la scène certifiée est une chaîne **iiwa-LIKE** simplifiée (bac technique
   ASSUMÉ, A21 ; offsets arrondis, pas les rotations inter-joints de l'URDF exact). Le **vrai KUKA iiwa
   URDF** était **explicitement différé** (DECISION-G2 §5 / A21 : « à décider en S10/S11 si un reviewer
   l'exige » ; hors-scope du go/no-go). Choisir le vrai iiwa MAINTENANT = tirer une session future vers
   l'avant.
2. **Rendu** : l'interactif est en projections 2D (vue dessus + côté), pas une vraie 3D rotative. Axe
   PUREMENT visuel (`viz.py` non sacré), additif et orthogonal à la preuve.

**Décision en attente (à arbitrer Stéphane + supervision)** :
- **Option A (recommandée par Code)** : NE PAS re-scoper S10. Finir le flagship iiwa-LIKE — valider V6,
  certifier (PROOF + verify exact, A32=0), clôturer **G4'** (la fidélité URDF reste un caveat documenté,
  pas un bloquant de porte). Le **vrai iiwa = session dédiée S10-bis**.
- **Option B** : re-scoper S10 maintenant pour le vrai iiwa URDF (plus long).

**Spike de faisabilité S10-bis (résultat à verser — le vrai iiwa n'est PLUS un pari)** : sondé Drake iiwa7
ce jour. **La FK de l'iiwa7 à q*=0 est entièrement RATIONNELLE** : translations inter-liens exactes
(0,1575=63/400 ; 0,183 ; 0,184=23/125 ; 0,2155=431/2000 ; 0,0805=161/2000) ; **rotations inter-liens =
matrices de permutation signée** (coefficients ∈ {0,±1} ⟺ ±90°/180° ⟹ cos/sin rationnels). ⟹ l'iiwa exact
**est représentable dans la forme déjà supportée par `verify.py`** (offset + axe unitaire + joints
verrouillés à cos/sin rationnels, mécanisme S9c), chaque rotation ±90° se décomposant en rotations
élémentaires x/y/z (groupe octaédrique). **Aucune modif de `verify.py`, aucun irrationnel.** Drake iiwa7
charge (`package://drake_models/iiwa_description/sdf/iiwa7_no_collision.sdf`) ⟹ référence de parité (méthode
S1). **Conclusion : S10-bis = construction + parité Drake <1e-9, PAS de la recherche risquée ; verify.py
INTACT.** Reste à fixer en S10-bis : la convention de composition exacte (rotation variable encadrée par les
sous-frames X_PF / X_MC du joint — 2 essais de rétro-ingénierie non concluants ce jour, à faire via
`ratfk.py`, le wrapper Drake RationalFK déjà au repo) et le choix du lien proximal + panneau sur la VRAIE
géométrie.

**Garde-fous** : `verify.py` sacré dans TOUS les cas ; le flagship iiwa-LIKE est le livrable documenté et
sanctionné (A21), G4'-valide ; UNDECIDED ≠ infaisable. Le spike n'a écrit AUCUN fichier (sondes Drake +
`/tmp`) — arbre propre à `258fc4d`.

**Prochaine étape** : arbitrage Stéphane + supervision (Option A vs B). AUCUNE certification lancée, S10 non
close tant que V6 non validé. Si A : valider S10-V6 → certifier → clôturer G4' → S10-bis (vrai iiwa,
faisabilité acquise). Si B : re-scoper S10 vers l'iiwa exact (repartir du spike ci-dessus).

## 2026-06-18 — Décision de pilotage (Stéphane + supervision) — arbitrage robot réaliste : Option A recadrée, flagship d'en-tête = vrai iiwa (S10-bis)

Contexte : au gate V6, Stéphane a demandé « une vraie scène 3D avec un robot réaliste ». Deux axes
distincts : (1) **CINÉMATIQUE** (iiwa-LIKE simplifié vs URDF KUKA exact) ; (2) **RENDU** (projections 2D
de l'interactif vs 3D rotative). Le spike Drake de ce jour a dé-risqué les MATHS de l'axe 1 : à q*=0 les
rotations inter-liens de l'iiwa7 sont des permutations signées (±90°/180°, groupe octaédrique ⟹ cos/sin
rationnels) et les axes de joints variables sont des axes de coordonnées (unitaires rationnels) ⟹ l'iiwa
exact rentre dans la forme DÉJÀ supportée par verify.py (offset + axe unitaire + rotations fixes cos/sin
rationnels, mécanisme S9c), SANS irrationnel, SANS modif de verify.py. **Dé-risqué = les maths ; PAS encore
la construction** (convention de composition X_PF/X_MC encadrant la rotation variable : 2 essais ratés ce
jour, à régler par parité Drake via ratfk.py — ingénierie bornée, pas de la recherche).

**Décision** : (A) NE PAS re-scoper S10 ; finir le flagship iiwa-LIKE — valider V6, certifier (PROOF +
verify exact, A32=0), clôturer G4' (banc sanctionné A21, porte technique sans signature) ; (recadrage) le
VRAI iiwa = flagship d'EN-TÊTE livré en S10-bis, cadré comme **MONTÉE EN GAMME du robot** (pas correction
d'un faux). Rejet de l'option B (re-scoper S10 maintenant) : mettrait l'inconnue de convention en tête d'une
session à son gate (scope creep évité depuis S7) ; plancher identique (iiwa-LIKE = repli G4' dans les deux
cas). **Certification de l'iiwa-LIKE MAINTENUE** (jalon pas cher 3 dims actives/766 lignes/secondes +
répétition générale du pipeline + isolation de la variable : pipeline validé ici, géométrie échangée
ensuite).

Axe 2 (rendu) : la **3D Meshcat rotative EXISTE déjà** (`cnp show`, robots spatiaux, depuis S6) ; ce que
Stéphane a vu à V6 = figures + interactif HTML 2D auto-suffisant. Lui montrer
`python -m cnp show scenes/S5_iiwa_shelf.yaml` (Meshcat 3D) satisfait une partie de l'envie « vraie 3D ».
Un export 3D auto-suffisant (Three.js) = polish S11, PAS un item de porte — ne pas laisser le rendu gonfler
S10/S10-bis. Pour le papier/deck : seule la figure du VRAI iiwa apparaît ; l'iiwa-LIKE reste un jalon
interne ⟹ pas de « double tampon G4' » côté publication.

- **[A39]** Le flagship d'en-tête (papier, deck Cambon AI) est le vrai KUKA iiwa, livré en S10-bis ;
  l'iiwa-LIKE est la validation méthodologique sur banc sanctionné (A21).
- **[A21 résolu]** Le caveat DECISION-G2 §5/A21 « fidélité URDF — à décider si un reviewer l'exige » est
  PÉRIMÉ : faisable (spike) et PLANIFIÉ (S10-bis). Renvoi inline au corps signé (pas de réécriture, doctrine
  D45) : « *[résolu : iiwa réel faisable, spike FK rationnelle q*=0 ; livré S10-bis]* » à l'emplacement A21
  de DECISION-G2.md §5.

**Diffs (circuit A16, repliés au commit de clôture S10)** : **D47** [A21 résolu] renvoi inline §5
DECISION-G2.md ; **D48** [A39] CLAUDE.md section S10 annotée + section S10-bis insérée au plan ; **D49**
header CLAUDE.md v1.15 + changelog.

**Prochaine étape** : gate V6 TOUJOURS OUVERT (aucun « VALIDÉ S10-V6 ») — re-présenter artefacts + budget
prédit + mention Meshcat 3D, PUIS ARRÊTER si non validé. Après V6 : certifier G4' (iiwa-LIKE) + clôturer.
Puis S10-bis (vrai iiwa, ordre imposé : convention/parité Drake AVANT la scène).

## 2026-06-18 — Session S10 (Claude Code, GATÉE) — FLAGSHIP iiwa-LIKE certifié : **G4' ACQUISE** (PROOF + verify exact + A32=0)

**V6 validée par Stéphane** (« VALIDÉ S10-V6 ») APRÈS l'arbitrage Option A recadrée (entrée pilotage
ci-dessus). **verify.py SACRÉ — zéro diff** (cas de base G3'b, spatial q*=0 sans verrou).

**Fait** :
- Scène flagship `scenes/S5_iiwa_shelf.yaml` (7-DOF tous libres, q*=0, `spatial_revolute` pur). `pair_views`
  ⟹ dims actives {0,1,2}, distaux {3,4,5,6} passifs.
- **Gate V6** : interactif A24 7 curseurs (1re 7-DOF sans verrou) + figures C-space/sweep (A20) + budget
  prédit présentés ; Meshcat 3D signalé. **A24 INVARIANT prouvé** (`tests/test_flagship_interactive.py` : la
  logique JS FK+collision reproduit l'oracle Python, 0 écart sous node ; correction du point proximal du
  corps dans `viz`). Les 3 boutons d'évasion (direct / par-dessus / distaux-redondance) ⟹ BLOQUÉ.
- Vérité-terrain dense **ré-assertée** (règle 9, `flagship_groundtruth.py`) : 0 libre dalle (120k uniforme +
  448 coins), invariance redondance (16 extrêmes distaux TOUS en collision), libre des 2 côtés.
- **CERTIFICATION G4'** (`flagship_bench.py`) : `cnp certify scenes/S5_iiwa_shelf.yaml` → **PROOF** ;
  `cnp verify` indépendant exact → **OK** ; **A32 `n_reresolve_failed` = 0**. 8 feuilles (4 collision,
  4 outside). **PREMIER certificat 7-DOF NON SYNTHÉTIQUE** du projet (vs synthétique S9d / scellé S9f) —
  chiffre de G4' sur banc iiwa-LIKE sanctionné (A21). Cert archivé `scenes/S5_iiwa_shelf.cert.json` ;
  benchmark daté `benchmarks/results/20260625T082956Z/flagship_S10_iiwa_like.json` (commit + git_dirty, règle 7).

**Mesuré vs prédit (discipline budget avant run)** :
- feuilles : prédit ~8, **mesuré 8** ✓
- coût/feuille réduit : prédit 766 lignes, **mesuré 766** ✓ (exact ; (d+1)^3 = 4^3)
- réduction A30 : full 7-DOF = **469 006** lignes ⟹ **×612** (le levier proximal qui rend le 7-DOF gratuit)
- wall-clock : prédit « secondes » ; mesuré **certify 16,2 s + verify 3,5 s**. Écart commenté : le terme
  dominant n'est PAS le LP de feuille (766 l., cheap) mais la **re-résolution pleine-dim à l'export**
  (soundness S8, voit les 7 dims, 469k l.) ; verify (clé de crédibilité) = 3,5 s. Trivialement sous budget.

**Décisions** :
- G4' acquise sur le banc iiwa-LIKE (A21, porte technique sans signature). Flagship d'EN-TÊTE (papier/deck)
  = vrai iiwa, livré en **S10-bis** (A39 ; faisabilité acquise par le spike, verify.py intact).
- Diffs doc D47-D49 (arbitrage) au commit doc `64b6c61` (circuit A16).

**Pièges** :
- L'interactif A24 prenait l'ORIGINE MONDE comme base du corps (collision fausse) ; corrigé en point
  proximal réel (shoulder→elbow) ⟹ parité EXACTE JS=oracle (test node). **Leçon : un artefact de viz peut
  MENTIR sans un invariant testé.**
- Le wall-clock de certif est piloté par la re-résolution pleine-dim (7 dims), PAS par le LP de feuille
  (3 dims actives) — ne pas confondre coût/feuille et coût d'export.
- `_lp_rows` est un helper local de `calibrate_g2` (pas dans `engine`) — répliqué dans `flagship_bench`.
- Bench run sur arbre dirty (cert + bench non commités) ⟹ `git_dirty=true` dans le JSON, assumé.

**Décompte exact (clôture S10)** : `make test` = **199 passed, 0 skipped, 0 warnings** (~207 s), pas de
flake (`test_parallel_speedup` vert ; D34 : aucun re-run isolé). Aucune modif src depuis `258fc4d` (viz/cli
inclus au V6-pending) — S10 ajoute scripts + scène + cert + docs.

**Diffs CLAUDE.md** (règle 14) : header v1.15 + S10 annotée + section S10-bis — au commit doc `64b6c61` (D48/D49).

**Prochaine étape** : revue de supervision G4' ; puis **S10-bis** (VRAI KUKA iiwa, flagship d'en-tête —
ordre imposé : convention + parité Drake <1e-9 AVANT la scène ; `verify.py` intact). Puis S11 (pack démo
bin-picking + capot certifiés ; viz complète A11/sweep/axes physiques).

## 2026-06-18 — Revue de supervision G4' / S10 (claude.ai, transcrite Code) — G4' ACQUISE, [A40]

Verdict : **G4' acquise** (banc iiwa-LIKE sanctionné A21). PROOF + verify exact + A32=0, 8 feuilles,
verify.py zéro diff (cas de base spatial q*=0), 199/0/0 sans flake, diffs D47-D49 à `64b6c61`. Conforme.

Chiffre de la session : **×612** (full 7-DOF 469 006 lignes → réduit 766) — 1re mesure du levier A30 sur le
flagship réel ; le 7-DOF est gratuit parce que le corps est proximal. Cœur du papier, désormais chiffré sur
scène non synthétique.

Au-dessus de l'attendu : (1) écart budget disséqué honnêtement — le coût certif (16,2 s) est piloté par la
**RE-RÉSOLUTION PLEINE-DIM à l'export** (soundness S8, 7 dims, 469k l.), PAS par le LP de feuille (766 l.
trivial) ; terme parallélisable, bonne grandeur à citer ; (2) l'interactif A24 prenait l'origine monde comme
base du corps (collision fausse), attrapé par le test de parité JS=oracle sous node — sans cet invariant, V6
validait un artefact qui ment.

Réserve mineure (gérée par le plan) : G4' sur banc iiwa-LIKE, pas le vrai robot ⟹ le tampon G4' et le
flagship d'en-tête divergent jusqu'à S10-bis ; **S10-bis n'est pas optionnel**, il aligne porte et
publication (repli iiwa-LIKE = filet, pas cible).

- **[A40]** Tout artefact de visualisation qui porte un ARGUMENT (collision, atteignabilité, séparation des
  composantes) exige un invariant TESTÉ reproduisant l'oracle de vérité — pas seulement les artefacts de
  preuve. Étend la discipline verify (« sound parce qu'on recompte ») à la viz à valeur d'argument.

**Diffs** : **D50** (A40 → règle 11, bloc validation visuelle) ; **D51** (header CLAUDE.md v1.16, changelog).
**Prochaine étape** : S10-bis (vrai iiwa, flagship d'en-tête).

## 2026-06-18 — Session S10-bis (Claude Code, GATÉE) — CONVENTION iiwa7 RÉSOLUE + parité Drake ; coupe Tâche 1 → Tâches 2-4 en S10-ter

Cible : vrai KUKA iiwa7 fidèle, certifié exact = flagship d'en-tête. **Ordre imposé respecté** : la
convention de composition + parité Drake D'ABORD. **Coupe naturelle prise** (autorisée par le prompt) : la
Tâche 1 (le risque) est livrée comme deliverable autonome ; **Tâches 2-4 (scène, V6-bis, certif) → S10-ter**.
`verify.py` SACRÉ — zéro diff. État vert d'ouverture : 199 passed. Ouverture doc circuit A16 `7304da0`
(revue G4', A40, D50-D51, v1.16).

**Fait (Tâche 1 — convention + parité)** :
- **Convention de composition RÉSOLUE** (les 2 essais ratés du spike venaient d'un mauvais repère de
  pliage). Forme exacte par-joint : `T_i(θ) = X_PF_i · Rot(z,θ) · X_ML_i` (sous-frames du joint, z l'axe
  dans F) — parité par-joint EXACTE. Pliage des constantes : `FK = G_0·Rot(z,θ_1)·G_1·…·Rot(z,θ_7)·G_7`,
  `G_i = X_ML_i·X_PF_{i+1}` = translation rationnelle + rotation permutation-signée.
- **Chaîne rationalisée verify-compatible** (`scripts/build_iiwa7_chain.py` → frozen `scripts/iiwa7_chain.json`) :
  19 entrées = 7 joints VARIABLES (axe z coordonné) + 12 joints VERROUILLÉS (rotations élémentaires x/y/z à
  cos/sin ∈ {0,±1}, mécanisme S9c) ; offsets rationnels (`limit_denominator 1e6`). **Tout rationnel, forme
  `{offset, axe unitaire, locked cos/sin}` que `verify.py` re-dérive — INTACT.**
- **Parité Drake = 1,99e-6** (max erreur position / 1500 configs aléatoires dans ±2,9). Fidèle au SDF à sa
  propre précision (~3,67e-6) ; **modèle interne EXACT**.
- Test permanent `tests/test_iiwa7_chain.py` (3) : exactitude rationnelle + forme verify (axes unité,
  cos²+sin²=1) ; build dans ratfk ; **parité Drake <5e-6** (skip si Drake/SDF absent, règle 13).

**Décisions** :
- **[Critère reformulé, Option A ratifiée par Stéphane 18/06]** Le critère « parité <1e-9 vs Drake » est
  INATTEIGNABLE : le **SDF iiwa7 lui-même n'est aligné aux axes qu'à ~3,67e-6 rad** (arrondi quaternion ;
  axes joints 2/6 ≈ [−2,65e-6, 3,67e-6, 1]). Matcher <1e-9 exigerait les axes irrationnels du SDF, que
  `verify.py` (axes unitaires rationnels) ne porte pas. Critère retenu : **fidèle au SDF à ~4e-6 +
  interne exact + verify-exact** — même doctrine de rationalisation que φ/obstacles et A21, appliquée à la
  CINÉMATIQUE. Mesuré 1,99e-6, sous le seuil.
- **Coupe Tâche 1 → S10-ter** (prompt : « si la Tâche 1 sature, clôturer sur la parité Drake seule »). Le
  G4' iiwa-LIKE de S10 reste la porte acquise ; S10-ter monte la scène/V6-bis/certif sur la chaîne gelée.

**Pièges** :
- L'identité naïve `Rot(â,θ)·Xrel` (conjuguer Rot(z) à travers X_PF) est FAUSSE : la conjugaison déplace
  la TRANSLATION (`X_PF·Rot = Rot(R·a)·X_PF` ne vaut que pour le bloc rotation). Le pliage CORRECT garde
  l'axe z et plie les constantes en `G_i` (signed-perm) — c'est ça qui rationalise proprement.
- `_decompose` (permutation signée → rotations élémentaires) : ordre des facteurs = produit GAUCHE-À-DROITE
  comme SympyRatFK compose (M2 = M @ R_k, append) ; un prepend donne un produit inversé → FK fausse (vu :
  parité 1,17 puis 0,43 avant correction).
- Le SDF iiwa7 n'est pas exactement rationnel (≠ ce que le spike S10 « np.round(...,4) » laissait croire) —
  d'où l'Option A ; ne PAS promettre <1e-9 sur un modèle SDF.

**Décompte exact (clôture S10-bis)** : `make test` = **201 passed, 1 failed, 0 skipped, 0 warnings**
(202 tests = 199 + 3 `test_iiwa7_chain`). **Le seul échec = `test_parallel_speedup`, FLAKE de timing
consigné (D34/A34)** : re-run isolé **1,87×** (sérial 7,65 s / parallèle 4,09 s, 8 workers ; seuil ≥3×) sur
machine CHARGÉE (4 users + serveur Meshcat `cnp show` laissé tournant par Stéphane + charge de session ;
`uptime` load 3,0). **Pas une régression** : AUCUNE modif du moteur/parallélisme/witness ce session (changements
= docs + scripts + scène/cert + tests + `viz`/`cli` hors chemin moteur) ; `verify.py` **zéro diff** (vérifié).
Mesure de référence quiète ~3,6× (cf. entrées antérieures). À re-confirmer sur machine quiète à l'ouverture S10-ter.

**Diffs CLAUDE.md** (règle 14) : aucun en clôture (v1.16 + A40/D50-D51 à l'ouverture `7304da0`). Le critère
reformulé (Option A) est une décision de pilotage journalisée, pas une réécriture de porte.

**Prochaine étape** : revue supervision S10-bis (critère Option A + parité) ; puis **S10-ter** (Tâches 2-4 sur
la chaîne gelée `iiwa7_chain.json` : choisir le lien proximal certifié + panneau d'étagère sur la VRAIE
géométrie iiwa, **re-mesurer les dims actives via pair_views — NE PAS présumer {0,1,2}** ; corps = coque
convexe fidèle rationalisée du mesh Drake ; vérité-terrain dense ; interactif A24 + figures du vrai iiwa ;
**gate V6-bis** A20 ; certif G4' sur le vrai robot). Repli inchangé : iiwa-LIKE = filet, vrai iiwa = cible.

---

## 2026-06-18 — Revue de supervision S10-bis (claude.ai) — convention résolue, critère Option A ratifié, A41-A42

Verdict : S10-bis validée. Le seul vrai risque research-ish restant du projet (la
convention de composition iiwa7) est RÉSOLU et la chaîne rationnelle verify-compatible
gelée (`iiwa7_chain.json`, 19 entrées : 7 variables axe-z + 12 verrouillées
permutation-signée). verify.py zéro diff confirmé ; parité Drake 1,99e-6 ; coupe Tâche 1
→ S10-ter conforme au prompt ; doc à `7304da0`.
Le piège documenté (conjuguer Rot(z) à travers X_PF déplace la TRANSLATION, pas seulement
la rotation ; pliage correct = garder l'axe z, plier les constantes en G_i permutation-
signée) est exactement l'erreur subtile qui aurait pollué une scène à moitié construite —
l'ordre imposé (convention d'abord) a payé.
Critère <1e-9 RATIFIÉ comme reformulé (Option A) : le seuil que la supervision avait posé
était INATTEIGNABLE non par faiblesse de méthode mais parce que le SDF iiwa7 lui-même
n'est aligné aux axes qu'à ~3,67e-6 (quaternions arrondis ; axes joints 2/6 non exactement
[0,0,1]) ; verify.py (axes rationnels) ne peut matcher des axes irrationnels. Erreur de
source côté supervision (même famille que les arXiv mal attribués S7). Reformulation juste :
« fidèle au SDF à ~4e-6 + interne exact + verify-exact » = doctrine A21 (rationalisation à
tolérance, re-vérifiabilité exacte préservée) étendue à la CINÉMATIQUE. 1,99e-6 mesuré,
sous le plancher de précision du SDF.
Le flake test_parallel_speedup (1,87× sous charge, Meshcat laissé tournant) correctement
consigné (D34/A34), pas une régression (zéro modif moteur/parallélisme, verify.py zéro
diff) — mais 3e occurrence ⟹ A42.
**[A41]** Toute tolérance de FRANCHISSEMENT posée dans un prompt de supervision doit être
vérifiée contre la PRÉCISION DE LA SOURCE avant d'être imposée. Leçon S10-bis : « parité
<1e-9 vs Drake » inatteignable (SDF aligné à ~3,67e-6 ; verify.py axes rationnels).
Reformulé « fidèle au SDF ~4e-6 + interne exact » (doctrine A21 étendue à la cinématique).
Corollaire papier : la fidélité au robot PHYSIQUE est plafonnée par la précision de l'URDF
publié (~2e-6 rad mesuré), pas par la méthode ; énoncer « cinématique rationnelle fidèle à
l'URDF iiwa7 à 2e-6 près », PAS « le iiwa exact » au sens absolu.
**[A42]** test_parallel_speedup a flaké 3× (S9a/S9c/S10-bis) sous charge — test de timing
structurellement fragile. Prochaine occurrence : le rendre robuste (best-of-N documenté)
ou le déplacer du `make test` requis vers un bench séparé, PAS un 4e re-run silencieux.
Non bloquant ; référence quiète ~3,6× inchangée.
Diffs : D52 (A41 → règle 9, à côté d'A28 — vérifier la source avant d'affirmer) ; D53
(A42 → S10-ter sortie + esprit règle 13) ; D54 (header CLAUDE.md v1.17, changelog
« v1.16→v1.17 (revue S10-bis, A41-A42) : convention iiwa7 résolue ; critère parité
Option A ratifié (fidèle SDF ~4e-6 + interne exact) ; tolérance de franchissement vérifiée
contre la précision source ; flake parallel_speedup à durcir »).
Prochaine étape : S10-ter (Tâches 2-4 sur la chaîne gelée).

---

## 2026-06-26 — Session S10-ter (Claude Code, GATÉE) — corps convexe fidèle GELÉ + dims actives MESURÉES ; coupe Tâche 2 → S10-quater

Suite de S10-bis (convention + parité Drake résolues, chaîne gelée `iiwa7_chain.json`). Objectif : monter
la scène flagship sur la VRAIE géométrie iiwa, corps convexe fidèle, V6-bis, certif G4'. **Coupe naturelle
prise** (autorisée par le prompt — « si la Tâche 2 sature, clôturer sur scène + vérité-terrain + corps convexe,
V6-bis/certif → S10-quater ») : la Tâche 2 est un vrai travail de recherche géométrique. `verify.py` SACRÉ —
zéro diff.

**Fait (ouverture)** :
- Nettoyage : aucun Meshcat/`cnp show` résiduel (le port 7000 = ControlCenter macOS/AirPlay, pas Meshcat).
  Machine quiète (load ~2,0 sur 10 cœurs ≈ 20 %).
- **[A42 EXÉCUTÉ]** `test_parallel_speedup` a flaké une 4e fois (isolé sur desktop actif : 2,04× ; série
  7,59 s / parallèle 3,72 s ; seuil ≥3×). Diagnostic : throttle SYSTÉMATIQUE par ~2 cœurs d'occupation
  desktop inkillables sur 10 (cold==warm pool mesuré, PAS une régression — zéro diff moteur ; le best-of-N
  est exclu, ce n'est pas un hiccup transitoire). Appliqué l'option A42 « sortir du `make test` requis vers
  un bench séparé » : marqueur pytest `bench`, `@pytest.mark.bench`, `make test` = `-m "not bench"`,
  `make bench-parallel` = `-m bench`. Référence quiète ~3,6× journalée. Commit `b465042`.
- Doc circuit A16 (commit séparé `1576515`) : revue S10-bis transcrite (A41-A42), CLAUDE.md v1.17 (D52 A41→règle
  9 ; D53 A42→section plan S10-ter ; D54 header+changelog).

**Fait (Tâche 2)** :
- **Corps convexe fidèle (niveau 1) GELÉ** → `scripts/iiwa7_body_link3.json` (+ tooling `scripts/build_iiwa7_scene.py`,
  test `tests/test_iiwa7_body.py`, 3). Pipeline : coque convexe Drake du **mesh de VISU du lien 3** (`Mesh.GetConvexHull()`,
  1301 sommets, convention Drake correcte — PAS le `.bin` gltf Y-up) → **support-échantillonnage** à 40 directions
  (Fibonacci sphere ; chaque sommet = vrai point extrême) → 40 sommets → **exprimés dans la frame-chaîne après q3**
  → **rationalisés** (`limit_denominator 1e6`, re-vérifiables exact). Remplace le segment épaissi. **UNE** coque/corps
  (niveau 2 multi-pièces hors périmètre).
- **Parité corps vs Drake = 1,67e-6** (coque rationalisée via FK chaîne vs lien 3 Drake réel, 400 cfg × 40 sommets ;
  sous le plancher SDF ~3,67e-6 ; modèle interne EXACT). Doctrine Option A (A21/A41) étendue à la SILHOUETTE.
- **Intégration chaîne gelée → scène CONFIRMÉE** : robot `spatial_revolute` 19 joints + 12 verrouillés + q_star 19×0
  se monte, FK marche, `body_link=7` (q3).
- **[Dims actives RE-MESURÉES via `engine.pair_views` — PAS présumées, A30]** = **(0,1,2)**, passives (3,4,5,6).
  La vraie cinématique (rotations inter-joints réelles) n'a PAS décalé les dims : corps après q3 ⇒ seuls les
  variables AMONT {q1,q2,q3} le bougent ; q4-q7 géométriquement en aval = passifs (thèse « robuste à la redondance »
  automatique pour un corps proximal). Budget prédit **(d+1)^3 = 64 lignes/LP**, identique au banc iiwa-LIKE.

**Décisions** :
- **Coupe Tâche 2 → S10-quater** : livrés = corps convexe fidèle gelé + intégration + dims mesurées. Reste
  (piège franc + vérité-terrain 0-libre + interactif A24 + figures + V6-bis + certif G4') → S10-quater. Forcer un
  piège marginal (6 mm) serait fragile, contraire à la discipline. Repli iiwa-LIKE (G4' S10) inchangé.
- **Lien proximal certifié = link 3** (3 actives, 4 distales passives — mirroir exact iiwa-LIKE ; corps réel).

**Pièges / findings (à ne pas repayer)** :
- La chaîne REPLIÉE n'expose PAS les frames de liens Drake comme frames intermédiaires (`G_i = X_ML_i·X_PF_{i+1}`
  mêle le côté lien i et le côté joint i+1). MAIS la frame-chaîne après q3 est rigidement reliée au lien 3 Drake
  par l'offset constant X_ML_3 ⟹ on exprime la coque dans la frame-chaîne via les poses à q=0 (C = X_chain0⁻¹·X_drake0),
  valable pour TOUT q par rigidité. Parité body 1,67e-6 le confirme.
- **`scenes.collision_oracle` (scenes.py:364) n'échantillonne que le SEGMENT `hull[0]→hull[-1]`** — INADÉQUAT pour
  un corps convexe à K sommets. La vérité-terrain S10-quater exige un oracle **corps-convexe vs H-rep** (LP de
  faisabilité indépendant ; hors `verify.py` sacré, c'est l'oracle de vérité-terrain). À livrer en S10-quater AVANT
  toute conception de piège.
- **GÉOMÉTRIE — piège franc non trivial sur le VRAI robot** : le vrai link3 est un blob compact proximal (~0,13 m),
  SANS le levier 0,3 m du segment iiwa-LIKE simplifié ⟹ la base-yaw le bouge peu ⟹ séparation base-yaw **MARGINALE**
  (mesuré : seul pitch ±15° symétrique sépare un mur +y, marge ~6 mm ; à pitch=0 les configs du slab et de
  start/goal sont quasi au même endroit près de l'axe — l'unique discriminateur est la rotation azimutale 62°
  d'un blob de rayon 0,11 ; les pitches extrêmes replient le lien hors de toute bande). 0 voxel commun sur le slab
  à pitch ±70°. **Conséquence S10-quater** : concevoir un piège FRANC — pistes à arbitrer (séparateur = q2 pitch à
  grand levier plutôt que base-yaw ; obstacle H-rep en coin/wedge ; OU lien plus distal au prix de >3 dims actives,
  budget S9f OK). L'iiwa-LIKE marchait parce que son corps-SEGMENT avait un grand levier — leçon : la fidélité
  géométrique du corps change la difficulté du piège.

**Décompte exact (clôture S10-ter)** : `make test` = **204 passed, 1 deselected, 0 skipped, 0 warnings**
(204 = 201 + 3 `test_iiwa7_chain` + 3 `test_iiwa7_body` ; le 1 deselected = `test_parallel_speedup`, marqueur
`bench`, durci A42 hors du requis). `test_parallel_speedup` : statut = **durci A42** (bench séparé `make bench-parallel`,
machine quiète ; référence ~3,6×), n'est plus dans le `make test` requis.

**Diffs CLAUDE.md** (règle 14) : à l'ouverture v1.17 + A41-A42 + section plan S10-ter (`1576515`) ; à la clôture
ligne « État d'avancement » S10-ter ajoutée (14b).

**Prochaine étape** : **S10-quater** — (1) oracle corps-convexe vs H-rep (vérité-terrain pour corps K-sommets) ;
(2) conception du piège FRANC sur le vrai robot (arbitrer séparateur/obstacle/lien) ; (3) vérité-terrain dense 0-libre ;
(4) interactif A24 (invariant A40 JS=oracle) + figures + sweep ; (5) **gate V6-bis** (A20) ; (6) certif G4' sur le
vrai robot + verify exact + A32=0. Puis revue supervision. Repli inchangé : iiwa-LIKE = filet, vrai iiwa = cible.

---

## 2026-06-26 — Revue de supervision S10-ter (claude.ai) — robot entièrement défini, finding A43, cap S10-quater

Verdict : S10-ter validée. Le vrai iiwa est désormais ENTIÈREMENT défini en forme verify-
compatible — cinématique (S10-bis, 1,99e-6) ET silhouette (S10-ter, corps convexe fidèle 40
sommets, parité 1,67e-6 < plancher SDF), les deux gelées, verify.py zéro diff. Dims actives
RE-MESURÉES (0,1,2) via pair_views, pas présumées : la vraie cinématique n'a pas décalé la
passivité (corps après q3 ⟹ q4-q7 en aval ⟹ passifs automatiquement) — « robuste à la
redondance » tombe de la géométrie réelle. Budget (d+1)^3 trivial, identique au banc. A42
exécuté proprement (test sorti du requis vers make bench-parallel ; diagnostic systématique,
best-of-N exclu à juste titre). 204/0/0, doc à `1576515`. Conforme.
Le finding central : le vrai link3 est un blob compact proximal (~0,13 m) sans le levier 0,3 m
du SEGMENT iiwa-LIKE ⟹ séparation par lacet de base marginale (~6 mm). Code a REFUSÉ de graver
un piège à 6 mm (« fragile, contraire à la discipline ») et a coupé — exactement la bonne
décision (lignée pas-de-×400 appliquée à la géométrie : ne pas vendre une déconnexion que la
marge ne soutient pas). Leçon générale au-delà de la session : tout le projet a piégé des
corps-SEGMENTS (grand levier ⟹ piège lacet de base facile) ; un corps à silhouette réelle est
compact ⟹ le levier disparaît ⟹ les déconnexions réalistes ne sont pas géométriquement les
mêmes que sur un robot-jouet. C'est aussi un RÉSULTAT du papier (un humain ne voit pas qu'un
blob proximal est piégé — l'outil le prouve).
Second finding (technique) : collision_oracle (scenes.py) n'échantillonne que le SEGMENT
hull[0]→hull[-1] — inadéquat pour un corps à 40 sommets ; la vérité-terrain exige un oracle
corps-convexe vs H-rep (LP de faisabilité, hors verify.py sacré), à livrer AVANT toute
conception de piège (sinon vérité-terrain fausse ⟹ régression micro-canal/scène-leaky).
**[A43]** La fidélité géométrique du CORPS change la difficulté de conception du piège.
Corps-segment = grand levier ⟹ piège lacet de base facile ; corps à silhouette réelle =
compact ⟹ levier disparu ⟹ séparation lacet de base marginale (~6 mm mesuré, refusé). Sur un
robot réaliste, le piège proximal franc vient d'un séparateur à grand levier réel (pitch
d'épaule q2) ou d'un obstacle enfermant (coin/wedge, sans levier articulaire), pas du lacet de
base. Corollaire vérité-terrain : un corps convexe K-sommets exige un oracle corps-convexe vs
H-rep (LP de faisabilité), PAS l'échantillonnage de segment de collision_oracle — AVANT toute
conception de piège.
Diffs : D55 (A43 → leçons de conception de scène, à côté du piégeage proximal S5/S6) ; D56
(header CLAUDE.md v1.18, changelog « v1.17→v1.18 (revue S10-ter, A43) : robot iiwa
entièrement défini gelé ; fidélité du corps change la difficulté du piège ; oracle
corps-convexe vs H-rep requis pour vérité-terrain K-sommets »).
Cap S10-quater : oracle corps-convexe d'abord ; piège franc (wedge premier choix, pitch q2
second, lien distal filet) ; vérité-terrain dense ; interactif A24 ; V6-bis ; certif G4'.

---

## 2026-06-26 — Session S10-quater (Claude Code, GATÉE) — oracle corps-convexe + PIÈGE FRANC (φ=q2 + étagère) + vérité-terrain ; coupe Tâche 2-3 → S10-quinquies

Suite de S10-ter (robot iiwa entièrement défini gelé : chaîne `iiwa7_chain.json` + corps `iiwa7_body_link3.json`).
Le travail de la session est le PIÈGE (le robot est fini, A43). `verify.py` SACRÉ — zéro diff. **Coupe Tâche 2-3
prise** (autorisée par le prompt) : oracle + piège franc conçu + vérité-terrain livrés ; interactif A24/figures +
V6-bis + certif → S10-quinquies.

**Fait (ouverture)** : machine quiète, pas de Meshcat. Doc circuit A16 (`c746bec`) : revue S10-ter transcrite (A43),
CLAUDE.md v1.18 (D55 A43→règle 9 ; D56 header). `make test` 204 confirmé à l'ouverture.

**Fait (Tâche 1 — oracle corps-convexe)** :
- **`scenes.convex_collision_oracle`** + helper testable **`_convex_hrep_intersect`** : teste si la coque convexe du
  corps (40 sommets FK-transformés) intersecte un obstacle H-rep — **LP de faisabilité** (`y=Σλ_k w_k`, λ simplexe,
  `Ay≤b` ⟹ `(AW)λ≤b, 1·λ=1, λ≥0`). Remplace l'échantillonnage de SEGMENT `hull[0]→hull[-1]` de `collision_oracle`,
  aveugle à un corps K-sommets (finding S10-ter A43). INDÉPENDANT du certificat, hors `verify.py` sacré.
- Test `tests/test_convex_oracle.py` (2) : cas hand-checkable cube↔boîte (chevauchement/disjoint/contact/tranche) +
  intégration sur le VRAI corps iiwa gelé (collide/libre ; FK sympy + coque gelée, sans Drake).

**Fait (Tâche 2 — PIÈGE FRANC)** :
- **Insight A43 appliqué et MESURÉ** : levier z du corps link3 par joint actif — **q1 (yaw)** et **q3 (roll)** laissent
  z INVARIANT (axes verticaux à q=0) ; **q2 (pitch d'épaule)** a un GRAND levier (top du corps 0,808 bras droit →
  0,545 bras incliné ±70°, symétrique). ⟹ séparateur = **q2** (pas le lacet de base, marginal). Wedge non nécessaire.
- **Piège** : **φ = s1 (q2)** ; slab {|s1|≤δ} = q2≈0 = bras DROIT vertical = corps HAUT ; **obstacle = ÉTAGÈRE EN
  SURPLOMB** (H-rep étanche, x,y∈±1/2, z∈[17/25, 1]) que le corps haut percute ; start/goal (q2=∓62°, bras inclinés,
  corps bas) passent dessous. δ=1/5. **Fenêtre franche de plafond mesurée : z0∈(0,597 ; 0,772), largeur 175 mm** ;
  choisi z0=17/25=0,68 ⟹ marges **+92 mm (pénétration slab) / +83 mm (dégagement start-goal)** — vs **6 mm** du base-yaw.
- **Scène figée `scenes/S6_iiwa_real_shelf.yaml`** (chaîne 19 joints + 12 verrouillés + corps 40 sommets ; verifiable
  exact q*=0 ⟹ PROOF éligible). Dims actives RE-MESURÉES (0,1,2), distaux (3,4,5,6) passifs. Budget (d+1)^3=64 l./LP,
  ≈ banc iiwa-LIKE. Générée par `scripts/build_iiwa7_scene.py:write_scene_yaml`.

**Fait (Tâche 3 — vérité-terrain dense)** : `scripts/flagship_iiwa_real_groundtruth.py` (oracle CORPS-CONVEXE) —
(A) start/goal libres ; (B) **0 libre / 40 000 uniforme** dans le slab ; (C) **0 libre / 448 coins** (2^6 non-barrière
× 7 niveaux s1, extrêmes distaux balayés, S9f) ; (D) **invariance redondance** : 16 extrêmes distaux ⟹ TOUS collision ;
(E) libre des 2 côtés (4000/4000). Marge franche ré-affichée (+92/+83 mm). Test rapide `tests/test_flagship_iiwa_real.py`
(2 : forme de scène + sous-ensemble franc 448 coins + invariance + marge ≥40 mm).

**Décisions** :
- **Coupe Tâche 2-3 → S10-quinquies** : livrés = oracle corps-convexe + piège FRANC figé + vérité-terrain. Reste
  (interactif A24 corps 40-sommets + invariant A40 JS=oracle + figures + V6-bis + certif G4') → S10-quinquies.
- **Séparateur = q2 (pitch, grand levier réel)** + **étagère en surplomb** (A43 premier choix levier). Le wedge
  (suggestion supervision) n'a pas été nécessaire : le levier de pitch suffit pour une marge ~90 mm.

**Pièges / findings** :
- **`viz.joint_limits_deg` étiquette chaque joint VARIABLE par son axe-chaîne (tous « z »)** — la chaîne repliée porte
  l'axe z, le vrai axe physique (q2 = pitch) émerge de la rotation verrouillée précédente (G1). Étiquettes physiques
  FAUSSES dans la sortie A25 actuelle ⟹ à corriger pour les figures (Tâche 4 S10-quinquies) : dériver le type de joint
  de l'axe EFFECTIF (locked·axis), pas de l'axe-chaîne brut.
- L'oracle corps-convexe coûte ~7,5 ms/LP (40k échantillons ⟹ ~5 min). Vérité-terrain dense = script ; le test garde un
  sous-ensemble rapide (coins 448 + marge).

**Décompte exact (clôture S10-quater)** : `make test` = **208 passed, 1 deselected, 0 skipped, 0 warnings**
(208 = 204 + 2 `test_convex_oracle` + 2 `test_flagship_iiwa_real` ; 1 deselected = `test_parallel_speedup`, bench A42).

**Diffs CLAUDE.md** (règle 14) : ouverture v1.18 + A43 + D55-D56 (`c746bec`) ; clôture ligne « État d'avancement »
S10-quater + section plan S10-quinquies (14b).

**Prochaine étape** : **S10-quinquies** — (4) interactif A24 sur le vrai iiwa (curseurs 7 joints ; corps = coque
40-sommets ; **invariant A40 JS=oracle TESTÉ** ; étiquettes axes physiques corrigées) + figures C-space/sweep (A20
apparence faisable, A25 par vue) ; (5) **gate V6-bis** (présenter marge FRANCHE + budget) ; (6) certif G4' (PROOF +
verify exact + A32=0) sur le vrai robot. Repli inchangé : iiwa-LIKE = filet, vrai iiwa = cible.

---

## 2026-07-02 — Revue de supervision S10-quater (claude.ai, transcrite Code, circuit A16) — piège franc endossé, aucun diff

Verdict : S10-quater validée. Le piège est FRANC (marges +92/+83 mm vs les 6 mm refusés en S10-ter — facteur ~15)
et la méthode exemplaire : levier z MESURÉ par joint actif avant de choisir (q1/q3 laissent z invariant — le lacet de
base ne pouvait structurellement pas marcher, ce qui explique le 6 mm ; q2 déplace le haut du corps de 0,808 à 0,545 m)
⟹ séparateur = pitch q2, obstacle = étagère en surplomb. Le wedge (suggestion supervision) non nécessaire — solution
plus simple ET meilleur récit (une étagère en surplomb dans une baie = littéralement le cas d'usage pharma). Oracle
corps-convexe livré en premier comme exigé (LP de faisabilité, testé hand-checkable + vrai corps), vérité-terrain
dense avec le BON oracle (40k + 448 coins + invariance redondance + libre des 2 côtés), dims actives re-mesurées
(0,1,2), scène figée PROOF-éligible, coupe conforme, 208/0/0, verify.py zéro diff. Conforme.

Deux points portés à S10-quinquies : (1) étiquettes d'axes physiques FAUSSES dans joint_limits_deg (famille A40 : une
étiquette A25 fausse sur les figures V6-bis est une viz qui ment) — corriger AVANT de générer les figures ; (2) unités
du budget à trancher explicitement (prédit « 64 lignes/LP » vs banc iiwa-LIKE mesuré « 766 lignes/LP » — les deux ne
mesurent probablement pas la même chose : points de contrôle Bernstein par contrainte vs lignes LP totales ;
l'ambiguïté polluerait le mesuré-vs-prédit).

Côté papier : le placeholder Figure 1 est résolu sur le TYPE (iiwa7 réel, étagère en surplomb, pitch q2) ; les chiffres
attendent la certif.

**Diff CLAUDE.md** : AUCUN (revue sans annotation — le circuit A16 transcrit la revue, les deux findings sont des
tâches de S10-quinquies déjà au plan, pas des amendements de règle).

---

## 2026-07-09 / 2026-09-08 — Session S10-quinquies (Claude Code, GATÉE) — interactif A24 vrai iiwa + figures + V6-bis validé + **certif G4' vrai robot ACQUISE (PROOF exact)** ; clôture reprise après interruption

Suite de S10-quater. Piège FRANC figé `scenes/S6_iiwa_real_shelf.yaml` (φ=s1 pitch q2, étagère en surplomb, marges
+92/+83 mm) + oracle corps-convexe. `verify.py` SACRÉ — zéro diff. Le robot ET le piège étant finis, la session produit
les ARTEFACTS (interactif + figures), passe la GATE V6-bis, puis certifie G4' sur le vrai robot. **NB temporel** : les
artefacts + le gate ont été faits le 09/07 ; la certif + la clôture ont été reprises le 08/09 après une interruption
(voir Pièges — état hérité A33/D33).

**Fait (ouverture, 09/07)** : machine quiète (no Meshcat ; load ~2). `git status` propre, `origin/main` à jour au commit
de clôture S10-quater (`4f42915`) + doc (`c746bec`). `make test` = **208 passed, 1 deselected, 0 skip/warn** confirmé à
l'ouverture. Doc circuit A16 : revue S10-quater transcrite ci-dessus (aucun diff CLAUDE.md).

**Fait (Tâche 4 — artefacts, commités 09/07)** :
- **Étiquettes d'axes physiques CORRIGÉES** (finding S10-quater, `viz._effective_axes`) : le type de joint est dérivé
  de l'axe EFFECTIF (`locked·axe` — rotations verrouillées précédentes appliquées à l'axe-chaîne), PAS de l'axe-chaîne
  brut (tous « z » à cause de la décomposition octaédrique). Résultat = pattern iiwa canonique **lacet, tangage, lacet,
  tangage, lacet, tangage, lacet** ; le SÉPARATEUR q2 s'étiquette bien **tangage (pitch)**. `joint_limits_deg` re-mappe
  la box sur les joints DÉBLOQUÉS (plus les 7 premiers joints-chaîne). Test `test_real_flagship_physical_axis_labels`
  (chaîne gelée). S3/S5/S2b (chaînes tout-débloqué) inchangés (axe effectif ≡ axe brut à q=0).
- **Interactif A24 vrai iiwa7** (`export_interactive_html(..., body_mode="hull")`, `_INTERACTIVE_TEMPLATE_HULL`) : corps =
  **coque convexe 40 sommets** (PAS un segment), collision **GJK(coque, boîte H-rep)** en JS, reproduisant
  `scenes.convex_collision_oracle` (A43). 7 curseurs (12 joints décomposition affichés verrouillés), fantômes start/goal,
  chaque vue déclare son contenu, 3 boutons d'évasion adaptés au piège pitch (direct / passer dessous / distaux-redondance)
  ⟹ tous BLOQUÉ. **Invariant A40 TESTÉ sous node** (`test_flagship_real_interactive`) : **0 écart / 694 configs** (400
  uniformes + start/goal + 192 coins-slab). Le S5 iiwa-LIKE garde son template segment (intact).
- **Figures V6-bis** (`scripts/make_real_flagship_figures.py`, oracle corps-convexe) : C-space (mur séparateur or+gris
  pleine hauteur sur l'axe pitch q2, A20/A25 étiquettes corrigées) + sweep **silhouette 40-sommets fidèle** (corps rouge
  dans l'étagère au transit q2≈0, poses libres dégageant sous l'étagère — pas de segment qui mentirait) + interactif
  canonique archivé.

**Fait (V6-bis, 09/07)** : gate présenté (interactif + figures + marge franche +92/+83 mm rappelant le 6 mm refusé +
budget prédit unités tranchées) ; **« Validé » par Stéphane**.

**Fait (Tâche 5 — certif G4' vrai robot, 08/09)** :
- `cnp certify scenes/S6_iiwa_real_shelf.yaml` → **PROOF** ; `cnp verify <cert> scene` → **OK exact** (2 feuilles, 2
  collision, 0 outside ; start/goal séparés par le slab |φ|≤1/5). **A32 = 0** (`n_reresolve_failed`). **`verify.py` zéro
  diff** (confirmé `git diff --stat`).
- **Vérité-terrain A43 ré-assertée** (sous-ensemble rapide) : start/goal libres, **0 libre / 448 coins-slab**, invariance
  redondance (16 extrêmes distaux ⟹ tous collision), marges franches **+91,5 mm** (pénétration slab) / **+83,3 mm**
  (dégagement start-goal).
- **Benchmark daté (règle 7)** : `benchmarks/results/20260908T121907Z/flagship_S10_iiwa_real.json` (commit `d16ab35`,
  `git_dirty=true` — attendu, le cert n'était pas encore commité au moment du run ; consigné tel quel). Ligne harness
  « 7-DOF iiwa7 réel (chaîne+corps gelés), piège pitch-étagère » ajoutée à `benchmarks/COMPARISON-Li-Dantam.md`.
- **Cert archivé** `scenes/S6_iiwa_real_shelf.cert.json` (chemin prévu — l'objet que la review amicale recomptera).

**Mesuré vs prédit (unité tranchée = lignes LP TOTALES par feuille)** :
- **feuilles : 2 mesuré vs ~8 prédit** — MOINS : la marge franche (~90 mm) rend la dalle triviale à paver (le b&b tranche
  vite, pas de raffinement près d'une frontière serrée).
- **lignes/feuille réduit : 1070 mesuré = 1070 prédit** (pile — 750 faces + 320 λ) ; **plein : 473 870**, réduction
  **×442,9** (vs ×612 du banc iiwa-LIKE — l'écart vient du corps 40-sommets qui ajoute ~320 lignes λ au réduit, dérisoire).
- **le « 64 » de la prédiction initiale était mal scopé** : c'était (d+1)^k par CONTRAINTE (une composante), et il présumait
  DPAD=3 (4³) ; le compte réel par contrainte est **5³ = 125** (DPAD=4). Corrigé dans le commentaire de la scène.
- **wall-clock : certify 726 s, verify 3,79 s** — le certify DÉPASSE largement l'estimation de gate (~15-30 s) : le terme
  dominant est la **re-résolution pleine-dim à l'export** (LP 473 870 lignes par feuille collision), bien plus coûteux que
  l'extrapolation linéaire depuis le banc n=6 (93 878 l. → 3,26 s) ne le laissait croire (le solve LP est superlinéaire en
  taille). La décision par feuille (réduit, 1070 l.) reste triviale. Verify (pleine dim, exact `Fraction`) tient en 3,8 s.

**Décisions** :
- **G4' RÉAFFIRMÉE sur le VRAI robot** ⟹ **FLAGSHIP D'EN-TÊTE ACQUIS** : cinématique fidèle URDF ~2e-6 (S10-bis) +
  silhouette fidèle ~1,7e-6 (S10-ter) + déconnexion franche ~90 mm certifiée **PROOF + verify exact recomptable** + A32=0.
  Aligné avec la Figure 1 du papier (vrai iiwa7, étagère en surplomb, pitch q2). Le repli iiwa-LIKE (G4' S10) reste le filet
  mais n'est plus nécessaire.
- **Caveat A41 porté** : la fidélité au robot PHYSIQUE est plafonnée par la précision de l'URDF publié (~2e-6), le modèle
  interne est EXACT (verify recompte en `Fraction`) — énoncer « fidèle à l'URDF iiwa7 à 2e-6 près », PAS « le iiwa exact ».
- **Interactif A24 : deux modes** (`segment` pour iiwa-LIKE/planaire ↔ `hull`+GJK pour le vrai corps convexe) plutôt qu'une
  réécriture destructive — le S5 testé reste intact.

**Pièges / findings** :
- **ÉTAT HÉRITÉ (A33/D33) — session interrompue SANS transcript** : la session du 09/07 a été interrompue pendant la Tâche 5,
  laissant deux fichiers `??` non commités et **hors trace** : `S6_iiwa_real_shelf.cert.json` **à la RACINE** de
  certified-noplan (mauvais chemin) et `scripts/flagship_iiwa_real_bench.py` **jamais exécuté** (aucun résultat daté). État
  CONSTATÉ explicitement, jamais absorbé en silence : cert re-vérifié frais (OK, identique à celui régénéré) puis supprimé de
  la racine ; bench relu LIGNE À LIGNE avant exécution (venait d'une session sans trace — `res.stats["by_status"]` confirmé
  présent à la source, engine.py:861). Deux processus orphelins du 09/07 (`cnp show` + son zmqserver Meshcat) trouvés et tués
  avant le bench (machine quiète, règle 7).
- **wall-clock de la re-résolution pleine-dim sous-estimé au gate** (~15-30 s annoncé, 726 s mesuré) : le solve LP pleine-dim
  (473 k lignes) est superlinéaire ; l'extrapolation linéaire depuis n=6 était trop optimiste. Sans impact soundness (verify
  exact tient en 3,8 s) mais à corriger dans les futures estimations de budget.
- Le verdict CLI `cnp verify` affiche encore les hypothèses en `q0…q6` génériques (pas les étiquettes physiques) — sans
  conséquence (c'est l'encadré d'hypothèses, pas une viz d'argument), noté pour cohérence future avec A25.

**Décompte exact (clôture)** : `make test` = **211 passed, 1 deselected, 0 skipped, 0 warnings** (208 S10-quater + 1
`test_real_flagship_physical_axis_labels` + 2 `test_flagship_real_interactive` ; 1 deselected = `test_parallel_speedup`,
bench A42). Confirmé après la Tâche 4 ; aucune modif de `src/` depuis (Tâche 5 = cert + bench script + docs), donc décompte
inchangé. Aucun flake.

**Diffs CLAUDE.md** (règle 14) : bullet de clôture « ✅ S10-quinquies ACTÉE » ajouté à la sous-section plan S10-quinquies
(14b, tenue de l'état d'avancement) ; correction du commentaire budget « 64 » de la scène gelée (comment-only, n'affecte pas
le cert).

**Prochaine étape** : **revue de supervision** (flagship d'en-tête réel acquis ⟹ **Figure 1 du papier + headline débloqués**),
puis **S11** (pack démo bin-picking + capot de sûreté certifiés 5-6 DOF ; export HTML 3D partageable ; viz complète A11/sweep/
axes physiques standard). `verify.py` intact tout du long.

## 2026-09-08 — Revue de supervision S10-quinquies (claude.ai, transcrite Code, circuit A16) — flagship d'en-tête ACQUIS, [A44], piste [L6]

**Verdict : S10-quinquies validée.** PROOF vérifié exact sur le vrai iiwa7, 2 feuilles, A32=0, `verify.py`
zéro diff, V6-bis validé, bench daté (`git_dirty` consigné), cert archivé au chemin prévu, 211/1/0/0 sans
flake. L'état hérité (session interrompue sans transcript) a été traité comme il faut : constaté, cert
re-vérifié frais, bench relu ligne à ligne, orphelins tués. Les étiquettes physiques (z,y,z,y,z,y,z) +
l'invariant A40 (0 écart/694) ferment les points de la revue précédente. **Le programme S10 est CLOS** :
flagship d'en-tête = vrai iiwa7, cinématique fidèle URDF ~2e-6 + silhouette fidèle ~1,7e-6 + déconnexion
franche ~90 mm, exactement re-vérifiable en 3,8 s. **Figure 1 du papier débloquée.**

**Point qui compte** : `certify` 726 s vs ~15-30 s annoncés au gate (×25-50). Le diagnostic de Code est
juste (re-résolution pleine-dim, LP 473 870 lignes, solve superlinéaire) mais INCOMPLET : en S9f un LP de
469 006 lignes prenait 72 s ; ici ~360 s/feuille. Le ×5 vient très probablement des **COLONNES** — le
témoin S9f a 2 sommets, la coque fidèle en a 40 ⟹ λ affine en 7 dims = **320 colonnes λ** au lieu de ~16.
Prix de la silhouette fidèle : dérisoire dans le LP réduit (1 070 lignes), lourd dans l'export pleine dim.
À confirmer par Code (ouverture S11, avec L6). Sans impact soundness (verify 3,8 s) ; 12 min ≪ 1 h. Cela
change la PHRASE du papier : « secondes » pour 5-6 DOF et la décision ; « minutes » pour le flagship réel,
dont ~99,5 % dans un terme d'export **parallélisable par feuille**.

**[A44]** Toute estimation de wall-clock de certification part de la taille **RÉELLE** du LP pleine
dimension (**lignes × COLONNES** — les K sommets multiplient les colonnes λ) et d'un modèle
**superlinéaire** calibré sur les benchs, pas d'une extrapolation linéaire en lignes. Leçon
S10-quinquies : 15-30 s annoncés, 726 s mesurés.

**[L6 — piste, à ÉVALUER en S11]** Export du certificat **RÉDUIT embedé en pleine dimension**
(coefficients nuls sur les axes passifs) au lieu de la re-résolution pleine-dim, **QUAND la projection S8
est exacte sur la géométrie ORIGINALE** (dims passives hors de la chaîne du corps — le cas proximal :
pour le lien 3 de l'iiwa, s3..s6 n'entrent même pas dans D ni dans N ; le LP plein est alors le MÊME
problème que le réduit, avec 5⁴ fois plus de points de contrôle sur un polynôme constant le long de 4
axes). `verify` reste l'arbitre pleine dim ⟹ **soundness inchangée** (embedding faux ⇒ rejet ⇒
ENGINE-PROOF, jamais un faux PROOF — l'argument S8). Re-résolution **CONSERVÉE** quand A29 a divisé un
facteur (1+s²) d'un joint de la chaîne (T n'est pas divisé ⟹ l'embedding direct ne vaut pas). Gain
potentiel ~×100 sur `certify`. Changement de **CONTRAT d'export** ⟹ décision de pilotage + règle 1
(0 changement de verdict, adversarial) ; **Code MESURE d'abord, on décide ensuite.**

**Diffs appliqués (ouverture S11, règle 14)** : **[D57]** A44 → règle 7 (discipline de budget) ;
**[D58]** L6 → tâche d'OUVERTURE de S11 « évaluer, ne pas implémenter sans décision » ; **[D59]** header
CLAUDE.md **v1.19** + changelog « v1.18→v1.19 (revue S10-quinquies, A44, L6) : flagship d'en-tête acquis
vrai iiwa7 ; budget wall-clock lignes×colonnes superlinéaire ; piste export cert réduit à évaluer ».

**Décision Stéphane** : **S11 (pack démo) AVANT le preprint** — matière deck en priorité.
