# FACTCHECK v0.2 — brouillon de papier §§ 6-9 confronté aux BENCHS ARCHIVÉS et au code

**Session P2 (Claude Code, autonome) — 10 septembre 2026.**
Cible : `docs/papers/PAPER-DRAFT.md` v0.2 (§§ 6 Cost model, 7 Experiments, 8 Limitations,
9 Note to reviewers). Les numéros `l.NNN` renvoient aux lignes de la v0.2 déposée par Stéphane.
Base : HEAD `4fda533` (ouverture DOC P2). Working tree : `docs/papers/PAPER-DRAFT.md` et
`PAPER-SKELETON.md` modifiés par Stéphane, rien d'autre.
État vert : `make test` = **240 passed, 1 deselected, 0 skipped, 0 warnings** (1 090 s, machine
chargée par les mesures de la session).

**Cette session n'a modifié aucun code** (`src/`, `tests/`, `scripts/`, `benchmarks/` : zéro diff).
Tout ce qui suit est lecture des JSON datés, lecture de code, et **quatre mesures** faites hors
dépôt (§3). Le brouillon n'est pas modifié par Code ; les phrases de remplacement sont en §2.

Raccourcis de chemins (tous sous `benchmarks/results/`) :

| alias | fichier | commit / dirty |
|---|---|---|
| **R6** | `20260612T233416Z/results.json` (relay, comb, anchor, bin) | `eb134e7` / false |
| **CAL** | `20260612T233416Z/calibration.json` | *aucune clé commit/dirty* (voisin de R6) |
| **WALL** | `20260613T014131Z/wall_resonde_S9f.json` | `93ef10d` / true |
| **A44** | `20260908T141015Z/A44_columns_check.json` | *aucune clé commit/dirty* |
| **F11** | `20260908T121907Z/flagship_S10_iiwa_real.json` (pré-S12) | `d16ab35` / true |
| **B11 / C11** | `20260908T150151Z/usecase_binpicking_iiwa7.json` / `20260908T151019Z/usecase_capot_surete_iiwa7.json` (pré-S12) | `f24bb51` / true |
| **F12 / B12 / C12** | `20260909T092652Z/flagship_S10_iiwa_real.json` / `20260909T092748Z/usecase_binpicking_iiwa7.json` / `20260909T092845Z/usecase_capot_surete_iiwa7.json` (post-S12) | `dbaaab8` / **true** |

---

## 1. Table de contrôle

### § 6 — Cost model

| # | Affirmation (ligne v0.2) | Verdict | Preuve + correction |
|---|---|---|---|
| **G1** | l.600-608 : balayage 3 joints × 6 directions × 2 motifs ; un seul piège franc, tangage d'épaule en surplomb **+175 mm** ; lacet de base **−73 à −299 mm** ; roulis et paroi négatifs partout | **VRAI — provenance journal seulement** | `JOURNAL.md:3193-3203` (table S11, `scripts/measure_iiwa7_lever.py`, +174,8 mm). **Aucun JSON daté** ne porte ces valeurs : la convention binding du squelette (« numbers only from dated benchmark JSONs ») n'est pas tenue ici. Voir D-P2-B. |
| **G2** | l.609-610 : « we say so in each scene file » | **IMPRÉCIS** | Dit en clair dans `scenes/usecase_binpicking_iiwa7.yaml:13-18` et `scenes/usecase_capot_surete_iiwa7.yaml:18-23`. **Pas** dans `scenes/S6_iiwa_real_shelf.yaml` : son en-tête (l.12-15) explique pitch vs lacet (A43) mais précède la mesure S11 et ne dit rien du mécanisme partagé. → « in each use-case scene file ». |
| **G3** | l.612-613 : séparation lacet de base de 6 mm mesurée et refusée | **VRAI** | `JOURNAL.md:2829, 2877-2878` ; `S6_iiwa_real_shelf.yaml:13-14`. |
| **G4** | l.619-626 : bac iiwa-like, 0 → 3 joints passifs, 8 feuilles constantes, LP réduit 766 constant, plein 766 → 3 782 → 18 814 → 93 878, ×4,9 par joint passif, ×122,6 à six joints | **VRAI** | **CAL** `family[0..3]` : `leaves = 8`, `cost_leaf_reduced_rows = 766`, `cost_leaf_full_rows` 766/3782/18814/93878, `reduction_x` 1.0/4.9/24.6/**122.6**. La famille est **S4 avec 7 − n joints distaux verrouillés, n = 3..6** (`scripts/calibrate_g2.py:3, 40-41`) ; S4 lui-même est le point n = 5. |
| **G5** | l.626-627 : ×443 sur le flagship (1 070 vs 473 870) | **VRAI** | **F12** `row.cost_leaf_reduced_rows = 1070`, `cost_leaf_full_rows = 473870`, `reduction_x = 442.9`. |
| **G6** | l.627-630 : variante à deux corps, paire proximale 766 lignes vs 18 814 en réduction globale, ×24,6 | **VRAI** | **CAL** `per_pair.pairs[0]` : `PROX_link2`, `lp_rows_per_pair = 766`, `lp_rows_global = 18814` (18 814 / 766 = 24,56). |
| **G7** | l.633-639 : mur scellé, barrière linéaire, k = 3..7 certifiés par témoin affine en 2-4 feuilles, lignes 766 → 469 006, ×4,99 | **VRAI** | **WALL** `rows[0..4]` : `verdict = PROOF`, `lam_degree = affine`, `leaves` 2/2/4/4/2, `cost_leaf_full_rows` 766/3782/18814/93878/469006, `verify_ok = true`. φ = s₀ linéaire : `scripts/wall_bench.py:64`, réutilisé `scripts/wall_resonde_S9f.py:82`. Scellement prouvé par Bernstein : `wall_resonde_S9f.py:17-20, 50-53`. |
| **G8** | l.638-640 : à k = 8 (~2,3 M lignes) un seul LP dépasse le budget temps, UNDECIDED | **VRAI — à préciser** | **WALL** `rows[5]` : `verdict = UNDECIDED`, `termination = budget_time`, `engine_s = 455.5`, `exact_verify = "not run (>= laptop single-run budget at ~2.3M rows)"`. **Le budget est 300 s** (`scripts/run_resonde_S9f.py:27`, `max_time_s=300`) ; le LP est atomique et rend la main à 455 s (`JOURNAL.md:2420-2422`). Attention : le bloc `budget.max_time_s = 1800` en tête de **WALL** **ne décrit pas** la ligne k = 8. |
| **G9** | l.649-651 : le « mur à k = 5 » était un artefact (plafond de profondeur silencieux + scène non déconnectée) | **VRAI** | `JOURNAL.md:2328-2336` (`Problem.max_depth=16`, `depth_exhausted` 16/16 ; obstacle = bbox de 4 000 échantillons). |
| **G10** | l.652-653 : « every UNDECIDED now names its cause » | **IMPRÉCIS** | `termination` n'est posée que sur le **chemin sériel** : `engine.py:870-873` (`ctx.termination()`, défini `engine.py:563-572`). Les chemins **work-queue** (`engine.py:762-763`) et **frontier/checkpoint** (`engine.py:929-930`) ne la renseignent pas ; la CLI ne l'affiche pas (aucune occurrence dans `cli.py`). Le sériel est le défaut (`engine.py:842`, `n_workers=1`). |
| **G11** | l.658-663 : flagship 46,7 s = 39,1 s FK symbolique + 1,3 s b&b + 6,3 s export, dont 4,9 s de vérificateur exact exécuté deux fois | **VRAI** | **F12** `row.certify_s = 46.73`, `phases_s = {build_fk_sympy: 39.09, branch_and_bound: 1.3, export_certificate: 6.34}`. Les 4,9 s : `JOURNAL.md:3444-3448` (2,45 s garde par feuille + 2,41 s `verify_loop`) — **journal, pas JSON**. |
| **G12** | l.664-665 : « re-solving each leaf's LP in full dimension cost 726 s » | **IMPRÉCIS** | 726 s est le **`certify` complet** avant L6 (**F11** `row.certify_s = 726.34`). Le terme de re-résolution pleine dim est **290,8 s par feuille × 2 ≈ 581,5 s** (**A44** `flagship_S6.export_s_per_leaf = 290.76` ; `CLAUDE.md:849`, « 0,29 s vs 581,5 s »). |
| **G13** | l.665-667 : à lignes égales (473 870 vs 469 006) la coque 40 sommets multiplie les colonnes par 14,2 (327 vs 23) et le temps de résolution par feuille par 39,9 (≈ colonnes^1,39) | **VRAI — un mot à corriger** | **A44** : `ratio_rows = 1.010`, `flagship_S6.cols = 327`, `witness_S9f_k7.cols = 23`, `ratio_cols = 14.217`, `ratio_export_time = 39.91`, `implied_exponent_in_cols = 1.389`. Le 39,9 est un rapport de **temps d'export par feuille** (`export_s_per_leaf` : construction du LP + résolution + arrondi), pas de « solve time ». |
| **G14** | l.667-669 : « Faithful silhouettes cost columns in the full-dimension LP **and nothing in the reduced one** » | **FAUX** | Les colonnes λ valent `nz = K · B` (`witness.py:409-411`) dans **tout** LP, réduit compris ; colonnes = `nz + nmu + 1` (`witness.py:205, 268`). **Mesuré (§3.3)** sur le flagship : LP réduit **K = 40 × B = 4 → 160 + 6 + 1 = 167 colonnes** (1 070 lignes) ; LP plein **40 × 8 + 6 + 1 = 327** (473 870 lignes, = **A44**). Avec un corps-segment (K = 2) le LP réduit aurait 15 colonnes : la silhouette coûte **×11 en colonnes dans le réduit aussi**. Ce qui est vrai : le réduit reste minuscule (b&b total 1,3 s). |
| **G15** | l.673-680 : table « nature du certificat » | **Colonne « This work » VRAI ; autres colonnes HORS PÉRIMÈTRE (A28)** | « ≤ 7 DoF, Bernstein-LP, exact rational, laptop CPU, sufficient only » : conforme (P1 F7, A1/A4). Colonnes externes conformes à `BIBLIO-VERIFIED.md` A6 (RTX 4070 + i9, 5-6 DoF), B1 (n ≤ 3, N&S, SDP), B2 (7-DOF iiwa, SOS). **Non couverts par BIBLIO pour la version 2024** : « asymptotically » complet (BIBLIO A3 = WAFR 2022) et « float collision checker » (BIBLIO A2 = RSS 2021). À confirmer par la supervision (A28). |

### § 7 — Experiments

| # | Affirmation (ligne v0.2) | Verdict | Preuve + correction |
|---|---|---|---|
| **H1** | l.689-690 : MacBook Apple Silicon, CPU seul, Python 3.12, HiGHS via `highspy` | **VRAI** | `.venv/bin/python --version` = 3.12.13 ; `engine.py:61` (P1 E3b). |
| **H2** | l.690-691 : « Every benchmark is written with its commit hash and a dirty-tree flag » | **IMPRÉCIS** | `20260611T195208Z/results.json` : commit **sans** `git_dirty` ; **CAL** et **A44** : **ni** commit **ni** `git_dirty`. Et les trois benchs post-S12 (**F12/B12/C12**) portent **`git_dirty = true`**. Voir D-P2-C. |
| **H3** | l.691 : « every sampling step is seeded » | **VRAI** (scripts contrôlés) | `scripts/flagship_iiwa_real_groundtruth.py:71` (`GT_SEED`) ; `scripts/wall_resonde_S9f.py:95` ; `scripts/build_iiwa7_chain.py:172` (`default_rng(7)`) ; `tests/test_adversarial.py:84` (`seed=0`). |
| **H4** | l.692-695 : vérité-terrain **toujours** établie « with a convex-body-versus-polytope oracle (an LP feasibility test) » | **FAUX** | L'oracle corps-convexe (`scenes.convex_collision_oracle`) n'existe que depuis S10-quater (`JOURNAL.md:2918-2921`) et ne sert qu'aux trois scènes iiwa7 (`flagship_iiwa_real_groundtruth.py:67`). Le mur scellé utilise l'**échantillonnage de segment** `scenes.collision_oracle(sc, n_samples=50)` (`wall_resonde_S9f.py:92`) ; relay, comb, anchor, bin sont des corps-segments antérieurs. Et l'échantillonnage biaisé-coins n'existe que depuis S9f (`JOURNAL.md:2340`) : S3 (150 000) et S4 (40 000) sont uniformes. |
| **H5** | l.700-702 : relay 46 feuilles, 38 collision sur trois paires, 8 outside | **VRAI** | **R6** `scenes[0]` (`S1_relais`) : `n_leaves = 46`, `by_status = {outside: 8, collision: 38}` ; trois paires : `JOURNAL.md:172` (UP 12 / DOWN 12 / MID 14). |
| **H6** | l.702-703 : barrière apprise, 78 feuilles | **VRAI** (test + journal, pas JSON) | `JOURNAL.md:47` (E4, φ appris, 78 feuilles). Aucun bench daté. |
| **H7** | l.703-704 : « reproduce, **coefficient for coefficient** at 10⁻⁷, an earlier **sum-of-squares** implementation » | **FAUX** | La parité mesurée porte sur la **marge t\* par cellule** (< 1e-7), pas sur les coefficients, et contre l'oracle 2-D **Bernstein-LP** `regref.certify_slab` → `certify_cell_pair` (`tests/regref.py:286-298, 225-231` : « Bernstein(g − μ·T) ≥ t ») — **pas** le SOS (qui vit à `tests/regref.py:110` et ne concerne que E1/E2). Parité t\* sur **E3 seulement** (`JOURNAL.md:170-175, 199`) ; pour E4, identité du nombre de feuilles (78). |
| **H8** | l.705-707 : comb 54 feuilles ; l'heuristique widest-axis explose (736, UNDECIDED) « while **the active-axis rule** certified — the origin of §3.6 » | **IMPRÉCIS** | En S6 c'est le look-ahead **`margin`** qui certifie en **54** (`JOURNAL.md:822-827` ; **R6** `scenes[1]` : `axis = margin`, `n_leaves = 54`), contre 736 feuilles **dont 256 FAIL** en widest-axis. La restriction du choix d'axe aux dims actives (S8, §3.6) a ensuite fait certifier le **widest-axis en 46** (`JOURNAL.md:1350-1353`). Le « 54 » et l'« active-axis rule » ne vont pas ensemble. |
| **H9** | l.715-717 : anchor PROOF 8 feuilles, moteur 0,043 s, vérif 0,041 s ; roulis et coude passifs | **VRAI** | **R6** `scenes[2]` : `n_leaves = 8`, `engine_s = 0.0426`, `verify_exact_s = 0.0415` (chronomètre `verify.verify` seul, `benchmarks/run_benchmark.py:115-118`) ; passifs (2,3) = roulis, coude (`CLAUDE.md:433`). |
| **H10** | l.717-718 : 0 libre dans la dalle sur 150 000 échantillons | **VRAI** (journal, pas JSON) | `JOURNAL.md:1218, 1276`. |
| **H11** | l.718 : panneau rétréci ⟹ UNDECIDED | **VRAI** | `JOURNAL.md:1027` (rétréci en y). |
| **H12** | l.718-719 : leur temps publié « minutes on a CPU » | **HORS PÉRIMÈTRE (A28)** | `BIBLIO-VERIFIED.md` A2 : « less than 4 minutes on average » — le **CPU** n'est pas consigné dans BIBLIO. |
| **H13** | l.723-726 : chaîne S-R-S, deux joints de poignet verrouillés à 0 (5 DOF), bac à paroi scellée, 0 libre / 40 000, PROOF 8 feuilles | **VRAI** | `scenes/S4_iiwa_bin.yaml:14-19, 32` ; `JOURNAL.md:2004` ; **R6** `scenes[3]` : `n_unlocked = 5`, `n_leaves = 8`, `verdict = PROOF`. |
| **H14** | l.725-726 : « The trapped body is link 2; **joints 3–6 are passive** for the pair (3 active dimensions) » | **IMPRÉCIS** | En indices 0-based du YAML (`S4_iiwa_bin.yaml:24-28`) : actifs {0,1,2}, **j3, j4 passifs** (débloqués), **j5, j6 VERROUILLÉS** — ce ne sont pas des dimensions. Et §7.4 écrit q₁…q₇ en 1-based : deux conventions dans la même section. |
| **H15** | l.727-729 : « certify + verify ≈ 1.0 s » ; « 3.3 s certify at 6 DOF before the export contract » | **IMPRÉCIS (provenance composite, date non dite)** | Aucune clé ne porte 1,0 s : c'est `DECISION-G2.md:19`, reconstruit de **CAL** `family[2].engine_s = 0.766` (qui chronomètre `cert.certify` = moteur + export, **sans** verify : `scripts/calibrate_g2.py:71-74`) + **R6** `scenes[3].verify_exact_s = 0.1574` ≈ **0,92 s**. Le moteur seul vaut **0,15 s** (**R6** `engine_s`). Le 3,3 s = **CAL** `family[3].engine_s = 3.343` (moteur + export, sans verify) ✓. **Les deux chiffres précèdent le contrat d'export** (juin, `eb134e7`) ; le brouillon ne le dit que pour 6 DOF. Depuis S12, S4 est exporté par embedding (4/0/0, `JOURNAL.md:3410-3412`) et **n'a pas été re-benché**. |
| **H16** | l.729-730 : « three orders of magnitude of margin on every criterion » | **IMPRÉCIS** | Critères G2' (`CLAUDE.md:686-687`) : < 1 h, < 10⁴ feuilles, verify OK, `n_reresolve_failed = 0`. Seuls les deux premiers sont chiffrés (8 vs 10⁴ ; ~1 s vs 3 600 s, `DECISION-G2.md:19` « marge ×1000 ») ; les deux autres sont binaires. |
| **H17** | l.736-739 : 19 entrées de chaîne (7 variables, 12 verrouillées, cos, sin ∈ {0, ±1}), offsets rationalisés au dénominateur 10⁶ | **VRAI** | `scripts/iiwa7_chain.json` : `joints` = 19, `locked` = 12, `variable_indices = [1,4,7,9,12,14,17]` ; (cos, sin) ∈ {(1,0), (0,1), (−1,0)} ; dénominateurs des offsets {1, 125, 400, 1000, 2000, 10⁶}, tous diviseurs de 10⁶. |
| **H18** | l.743-744 : parité FK vs Drake sur 1 500 configurations « **in the factory limits** » à 1,99·10⁻⁶ | **IMPRÉCIS** | `scripts/build_iiwa7_chain.py:172-173` : `uniform(-2.9, 2.9, 7)` sur **tous** les joints. **Limites constructeur lues dans le plant Drake (§3.2)** : ±170° j1, j3, j5 ; **±120° j2, j4, j6** ; ±175° j7. Les tirages **sortent** des limites sur j2, j4, j6 — le test est plus large que ce que dit le papier. L'erreur est la **position** de l'origine de la bride `L7end` (`build_iiwa7_chain.py:176-179`), en **mètres**. |
| **H19** | l.745-752 : axes SDF à 3,67·10⁻⁶ ; coque de 1 301 sommets → 40 directions de Fibonacci → 40 points extrêmes ; parité corps 1,67·10⁻⁶ sur 200 configurations | **VRAI** | P1 E1b/E1c ; `JOURNAL.md:2813-2814` ; `scripts/iiwa7_body_link3.json` : `k_vertices = 40`, `drake_body_parity = 1.674e-06`. |
| **H20** | l.754-757 : φ = s₂ (tangage d'épaule), δ = 1/5, dessous de l'étagère z = 17/25 ; bras droit, sommet du lien à 0,808 m | **VRAI** | Cert `S6_iiwa_real_shelf.cert.json` : `phi = {'0,1,0,0,0,0,0': '1'}` (2ᵉ variable) ; `S6_iiwa_real_shelf.yaml:136` `delta: 1/5` ; `JOURNAL.md:2929` z ∈ [17/25, 1]. **Mesuré (§3.1)** : sommet à q₂ = 0 = **0,8080 m**. |
| **H21** | l.757-758 : « with the arm inclined **at ±62° it clears at 0.545 m** » | **FAUX (mesuré)** | **Mesuré (§3.1)** : aux poses start/goal (s₂ = ∓3/5, `S6_iiwa_real_shelf.yaml:145-146`, q₂ = ∓61,93°) le sommet est à **0,5967 m** ; **0,544-0,545 m** correspond à **q₂ = ±69,98°**, bord de la boîte (s = ±7/10, `yaml:138-140`). Le journal est juste (`JOURNAL.md:2926-2927`, « 0,545 bras incliné ±70° ») : le brouillon a fusionné les poses (±62°) et le bord de boîte (0,545). Cohérence : 680 − 596,7 = **83,3 mm** = le dégagement du JSON. |
| **H22** | l.758-762 : marges 91,5 / 83,3 mm ; 0 libre sur 40 000 uniformes **et 448 échantillons biaisés-coins** ; 16 combinaisons distales toutes en collision ; libre des deux côtés | **VRAI — un mot IMPRÉCIS** | **F12** `groundtruth.slab_penetration_mm = 91.5`, `startgoal_clearance_mm = 83.3`, `slab_corner_free = 0`, `redundancy_all_collide = true`. Les **448 sont des coins déterministes** (2⁶ extrêmes des joints non-barrière × 7 niveaux de s₂ ; `JOURNAL.md:2937-2938`), pas des échantillons. Le 40 000 n'est pas dans le JSON : défaut `nb=40_000` (`flagship_iiwa_real_groundtruth.py:45`) et `JOURNAL.md:2937`. 16 combinaisons : `groundtruth.py:100-105` ; deux côtés, 4 000 tirages par côté : `groundtruth.py:109-120`. |
| **H23** | l.764-768 : PROOF, 2 feuilles collision, actifs (q₁, q₂, q₃), 1 070 vs 473 870 (×443), certify 46,7 s (39,1 / 1,3 / 6,3), verify 2,42 s, embedded 2 / re-solved 0 / rejected 0, dissonance 0 | **VRAI** | **F12** `row` : `leaves = 2`, `by_status.collision = 2`, `active_dims = [0,1,2]`, `verify_s = 2.42`, `n_leaves_embedded = 2`, `n_leaves_resolved = 0`, `n_embed_rejected = 0`, `n_reresolve_failed = 0`. |
| **H24** | l.776-780 : bac euro empilé 600 × 400 × 220 mm, dessous à 0,720 m, boîte ±62°, δ = 3/20, fenêtre 138,7 mm, +66,9 / +71,7 mm, PROOF 2 feuilles | **VRAI** | `JOURNAL.md:3221-3223` ; **B12** `groundtruth` 66.9 / 71.7, `leaves = 2`, `verify_msg` « \|phi\| <= 3/20 ». |
| **H25** | l.782-786 : capot 50 mm, ±0,60 m, dessous 0,695 m, ±66°, δ = 9/50, fenêtre 168,4 mm, +83,1 / +85,3 mm, PROOF 4 feuilles (2 + 2) | **VRAI** | `JOURNAL.md:3221-3223` ; **C12** `groundtruth` 83.1 / 85.3, `by_status = {outside: 2, collision: 2}`, « \|phi\| <= 9/50 ». |
| **H26** | l.780 « verify 2.45 s » ; l.786 « verify 2.54 s » | **IMPRÉCIS (bench périmé)** | 2,45 et 2,54 viennent des benchs **S11 pré-S12** (**B11** / **C11** `row.verify_s`, commit `f24bb51`, certificats d'avant la bascule L6). Les certificats livrés sont ceux de S12 : **B12** `verify_s = 2.43`, **C12** `verify_s = 2.50`. Le brouillon mélange les deux campagnes (certify ~46 / ~47 s = S12). |
| **H27** | l.790-792 : storyboard « traverser la paroi du bac » abandonné après la mesure du levier | **VRAI** | `JOURNAL.md:3207-3209`. |
| **H28** | l.796-805 : table §7.6, colonne « certify » ; comb verify 0,18 s | **IMPRÉCIS (structurel)** | La colonne mélange **trois définitions** : **moteur seul** pour relay (< 1 s = **R6** `engine_s` 0,48), comb (~1 s = 1,36) et anchor (0,04) ; **moteur + export pré-S12** pour le bac (~1 s = **CAL** 0,77) ; **`certify` bout-en-bout post-S12, build FK compris** pour les trois iiwa7 (46,7 / 46,1 / 47,1). Comb : `verify_exact_s = 0.1727` → **0,17 s**, pas 0,18. Crate / guard : 2,43 / 2,50 (H26). Table corrigée en §2.7. |
| **H29** | l.805 : mur scellé, certify « **0.1 s – 72 s** » | **FAUX (non sourcé)** | Aucune clé de **WALL** ne donne 72 : `engine_s` 0,1 → **65,1** ; `cert_s` (export) 0,05 → 14,57 ; `verify_s` 0,01 → 6,82. 72 ≈ 65,1 + 6,82 (moteur + vérif) alors que 0,1 est le moteur seul. Moteur + export : 0,15 → **79,7 s**. |
| **H30** | l.796-807 : nombres de feuilles, dims actives, vérité-terrain, « All PROOF, all exactly verified, dissonance counters zero » | **VRAI** | **R6/CAL/WALL/F12/B12/C12** : `n_reresolve_failed = 0` partout, `verify_ok = true` / `verdict = PROOF` partout ; comb 0/300k (`CLAUDE.md:401-403`), anchor 0/150k (H10), bac 0/40k (H13), iiwa7 0/40k + 448 (`JOURNAL.md:3234`), mur 0/8 000 uniforme + 8 000 biaisé-coins (`wall_resonde_S9f.py:89-102`). |
| **H31** | l.814-818 : micro-canal — dents rétrécies de 5 %, grille 11³ sans libre, échantillonnage dense qui en trouve, moteur UNDECIDED sans certificat, test permanent | **VRAI** | `tests/test_adversarial.py:137-156` : `_peigne(0.95)`, grille `n=11` (comb 3-DOF plan ⟹ 11³), `_dense_free_in_slab` (15 000 tirages, l.84) > 0, `res.verdict != "PROOF"`, `make_certificate` lève. |
| **H32** | l.816 : « through a channel **a few millimetres wide** » | **NON SOURCÉ** | Aucune largeur de canal n'a jamais été mesurée : le test (l.151) et le journal (`JOURNAL.md:803-806`) établissent seulement l'**existence** de configurations libres. À retirer, ou à mesurer. |
| **H33** | l.819-829 : scène leaky — k = 5, bbox de 4 000 échantillons + marge, 0 libre / 8 000 uniformes, refus à profondeur relevée et budget réel, bout du lien dépassant de 8 à 40 mm | **VRAI** | `JOURNAL.md:2333-2336` (marge 0,02 ; dépassement ~0,008-0,04) ; `wall_resonde_S9f.py:9-11`. |
| **H34** | l.831-837 : deux artefacts de viz fidèles mais insuffisants, attrapés par le gate humain | **VRAI** | `CLAUDE.md:334-341` (A45). |
| **H35** | l.842-844 : « `cnp verify <cert> <scene>` reproduces every PROOF … on a standard Python installation **with no third-party package** » | **FAUX** | `cli.py:42-49` : `_cmd_verify` importe `certificate` pour charger le cert (`certificate.py:45-48` : **numpy**, `engine`, `witness`, `ratfk`) et `scenes` pour le recoupement (`scenes.py:53-58` : **numpy, yaml**, `engine`, `ratfk`). Seul le **module** `verify.py` est stdlib-only (P1 F7). **Mesuré (§3.4)** : `cnp.verify.verify_file` sous `python -S -I` (site-packages désactivé) re-prouve le flagship, **zéro module tiers chargé** — mais c'est une autre commande, sans le recoupement de scène. |
| **H36** | l.841-844 : « The verifier, **the certificates** and the scene files are released … reproduces **every PROOF in the tables** » | **FAUX** | Le dépôt ne livre que **4** certificats (`scenes/*.cert.json`) : flagship, bac empilé, capot — et `S5_iiwa_shelf.cert.json` (iiwa-LIKE, **absent des tables**, pré-S12). Relay, comb, anchor, bac S4 et la famille du mur **n'ont pas de certificat livré** : ils sont régénérés par `cnp certify` / les scripts de bench. |
| **H37** | l.844-845 : générer les certificats demande « Drake, HiGHS » | **IMPRÉCIS** | Dépendances du générateur (`pyproject.toml` `dependencies`) : numpy, scipy, **sympy**, **highspy**, **pyyaml** (+ cvxpy, clarabel, scikit-learn, matplotlib, meshcat). **Drake est un extra optionnel** (`[project.optional-dependencies] drake`) : les certificats iiwa7 se génèrent par `SympyRatFK` (`certificate.py:48, 210`) depuis la chaîne gelée ; Drake ne sert qu'à re-dériver chaîne et corps (`scripts/build_iiwa7_chain.py`, `build_iiwa7_scene.py`). |
| **H38** | l.845-846 : « Each figure's numbers are read from the dated benchmark files, not retyped » | **VRAI** (Figure 1, seule figure du brouillon) | `scripts/make_paper_fig1.py:35` (`BENCH_GLOB = "benchmarks/results/*/flagship_S10_iiwa_real.json"`). La **table** §7.6, elle, est saisie à la main — c'est l'objet de ce contrôle. |

### § 8 — Limitations

| # | Affirmation (ligne v0.2) | Verdict | Preuve + correction |
|---|---|---|---|
| **I1** | l.854-855 : « our real scenes have three active dimensions » | **VRAI** | **F12/B12/C12** `n_active = 3` ; bac S4 : 3 (**CAL** `family[2].n_active`). |
| **I2** | l.867-868 : barrières livrées fournies par la scène, toutes linéaires en un joint | **VRAI** | Les 4 `scenes/*.cert.json` : φ = un seul monôme de degré 1 (S5 : s₀ ; S6 / bac / capot : s₁), `degree_per_var = 2` déclaré (cf. P1 B-bis). |
| **I3** | l.868-869 : pipeline de fit automatique « validated on planar scenes only » | **IMPRÉCIS** | Validé avec vérification exacte sur E4 plan (`JOURNAL.md:599-603`), **et** φ trouvé automatiquement sur une scène **3-DOF spatiale**, moteur-PROOF + 0 libre / 300 000 (`JOURNAL.md:604-612`), à une époque où le vérificateur exact était plan. |
| **I4** | l.869-870 : sur un joint passif le fit sur-ajuste | **VRAI** | `CLAUDE.md:653-655` (A19, leçon S6). |
| **I5** | l.872-874 : « symbolic kinematics construction (39 s of 47), **built twice per run** » | **IMPRÉCIS** | `_body_numerators` (construit `SympyRatFK`, `certificate.py:200-210`) est bien appelé deux fois (`certificate.py:244, 561`), mais le second appel coûte **1,21 s**, cache sympy chaud (`JOURNAL.md:3444-3445`). Les 39 s sont payées **une fois par process** (**F12** `phases_s.build_fk_sympy = 39.09`). |
| **I6** | l.874-876 : le vérificateur tourne deux fois comme garde ; taille du LP unique à k ≥ 8 = frontière | **VRAI** | `JOURNAL.md:3446-3448` ; **WALL** `rows[5]`. |
| **I7** | l.860-865 : un seul corps convexe par corps certifié, obstacles polytopes statiques, pas de wrap-around, chaînes révolutes seulement | **VRAI** | `SPEC.md:54-55` (chaîne révolute, limites dans (−π, π)), hypothèses §2 (`SPEC.md` « Hypothèses du théorème »). |

### § 9 — Note to reviewers

| # | Affirmation (ligne v0.2) | Verdict | Preuve + correction |
|---|---|---|---|
| **J1** | l.896 : « a 499-line exact program » | **VRAI** | P1 D1 (`wc -l src/cnp/verify.py` = 499 ; dernier commit sur le fichier `3d2f00f`, S9c). |
| **J2** | l.899-901 : « the pipeline produced a wrong scene and a wrong ground truth, and **the artefact designed to be independent of it caught both** » | **FAUX (attribution)** | Dans les **deux** épisodes de §7.7, c'est le **moteur** — le certificateur, qui fait partie du pipeline de génération — qui refuse : `tests/test_adversarial.py:153-156` (`res.verdict != "PROOF"`, `make_certificate` lève) ; `JOURNAL.md:2333-2336` (UNDECIDED). **Le vérificateur indépendant n'a jamais vu de certificat.** De plus le micro-canal est une scène **construite exprès** (test adversarial), pas une erreur du pipeline : seule la scène leaky est « une mauvaise scène + une mauvaise vérité-terrain ». L'argument tient, mais il faut l'attribuer à l'exigence de certificat (un témoin LP sur **chaque** cellule), pas au vérificateur. §7.7 dit juste (« the certifier ») ; §9 dit faux. |
| **J3** | l.920-921 : « faithful to the published description to **2·10⁻⁶ rad** » | **FAUX (unité)** | 1,99·10⁻⁶ est une **erreur de position en mètres** à l'origine de la bride (`build_iiwa7_chain.py:176-179` : `np.linalg.norm(W - Xwb(...)[:3, 3])`). Seul le plancher d'alignement des axes du SDF (3,67·10⁻⁶) est un angle. **Même unité fausse hors §§ 6-9** : Abstract l.36, §1 l.135 et l.152, `PAPER-SKELETON.md:31, 190`, et `CLAUDE.md` règle 9 (corollaire A41, « ~2e-6 rad mesuré »). Voir D-P2-A. |
| **J4** | l.925-929 : la preuve prend un point où φ = 0 ; test outside large, et correct | **VRAI** | `verify.py:139-141, 390` (P1 A1/A4) ; SPEC §2 (i) désormais strict (D67). |
| **J5** | l.908-910 : le théorème quantifie sur toute la boîte 7-D ; les dims passives sont couvertes par la preuve | **VRAI** | `S6_iiwa_real_shelf.yaml:137-144` (7 intervalles, passifs ±3 en s) ; verify arbitre en pleine dimension (`SPEC.md` v1.7, contrat d'export). |
| **J6** | l.901-904 : les deux artefacts qui mentaient (figures) attrapés seulement par le gate humain | **VRAI** | `CLAUDE.md:334-341` (A45). |

---

## 2. Corrections à porter au brouillon (phrases prêtes à coller)

### 2.1 § 6.3 — colonnes du LP réduit (G14) et 726 s (G12, G13)

> Before the export contract, certification took 726 s, of which about 580 s was re-solving
> the two leaves' LPs in full dimension (291 s per leaf), and the cost was not in rows: at
> nearly equal row count (473 870 vs 469 006), the 40-vertex faithful hull multiplies LP
> columns by 14.2 (327 vs 23) and export time per leaf by 39.9 (about columns^1.39). Each
> hull vertex carries its own multiplier, so a faithful silhouette multiplies columns in the
> reduced LP too — but the reduced LP stays small (1 070 rows × 167 columns on the flagship),
> which is why the reduced witness, embedded, is the right thing to export.

### 2.2 § 6.2 — cause de terminaison (G10) et k = 8 (G8)

> … and at k = 8 (about 2.3 million rows) a single LP outlasts the 300 s deadline — it
> returns after 455 s — and the verdict is UNDECIDED on budget.

> … because the diagnosis changed how the engine reports termination — the serial engine,
> the default, now records why it stopped (certified, depth exhausted, leaf budget or time
> budget) — and because …

### 2.3 § 6.1 — fichiers de scène (G2)

> … claim; we say so in each use-case scene file.

### 2.4 § 7, préambule (H2, H4)

> All runs: MacBook (Apple Silicon), CPU only, Python 3.12, HiGHS via `highspy`. Every
> benchmark directory records its commit hash, and every sampling step is seeded. Ground
> truth is always established *before* certification (start and goal free; no free sample
> in the slab; free space on both sides) with a collision oracle independent of the
> certificate: point sampling along the link for segment-shaped bodies, and a
> convex-body-versus-polytope LP feasibility test for the faithful iiwa7 link. Since the
> leaky-scene episode of §7.7, ground truth also includes a corner-biased pass.
> Verification times are for the exact verifier of §5.

*(Si la supervision veut garder « dirty-tree flag », dire que les trois benchs iiwa7 post-S12
portent `git_dirty = true` — voir D-P2-C.)*

### 2.5 § 7.1 — parité et comb (H7, H8)

> Two planar 2-DOF scenes fix the ground: a three-obstacle relay in which the middle link is
> trapped by three "teeth" in turn (46 leaves: 38 collision across three pairs, 8 outside)
> and a scene with a learned barrier (78 leaves). The relay reproduces, cell by cell, the
> certified margin of an earlier two-dimensional Bernstein-LP implementation to 10⁻⁷; the
> learned-barrier scene reproduces its partition. A 3-DOF "comb" lifts the relay by one
> passive joint and was the first scene on which the widest-axis rule wasted its depth on
> the passive joint (736 leaves, 256 of them failed, UNDECIDED) while a one-step look-ahead
> rule certified in 54 leaves; restricting axis choice to active dimensions (§3.6) later let
> the widest-axis rule certify it too, in 46 leaves.

### 2.6 § 7.3 — bac iiwa-like (H14, H15, H16)

> A 7-joint S-R-S chain with iiwa-like link lengths and the two wrist joints locked at 0
> (5 DOF), reaching into a deep bin with a sealed front wall. The trapped body is the
> shoulder–elbow segment: the three proximal joints are active for the pair, the two
> unlocked distal joints are passive. Ground truth 0 free over 40 000 samples. PROOF,
> 8 leaves; engine 0.15 s, verification 0.16 s, about 0.9 s end to end with the
> full-dimension export that preceded the export contract of §3.7. Releasing the locks one
> at a time gives the passive-dimension calibration of §6.2 (8 leaves throughout; 3.3 s
> engine and export at 6 DOF, also before the export contract). The scene met our 5–6-DOF
> gate with more than three orders of magnitude of margin on time and leaf count, and it is
> where the proximal insight of §6.1 was first written down.

### 2.7 § 7.4 — parité, hauteurs, coins (H18, H21, H22)

> Forward kinematics agrees with Drake's on 1 500 configurations drawn uniformly in ±2.9 rad
> on every joint — beyond the ±120° factory limits of joints 2, 4 and 6 — to 1.99·10⁻⁶ m
> (maximum position error at the flange); the SDF's own joint axes are aligned with the
> coordinate axes only to 3.67·10⁻⁶ rad, so this is the fidelity of the published
> description itself.

> With the arm upright the link's top reaches 0.808 m and strikes the shelf; at the start
> and goal poses (shoulder pitch ∓61.9°) it tops out at 0.597 m and passes beneath.
> Margins: the trapping band penetrates the shelf by 91.5 mm; start and goal clear it by
> 83.3 mm. Ground truth with the convex-body oracle: start and goal free; 0 free in the slab
> over 40 000 uniform samples and at 448 slab corners (2⁶ extremes of the non-barrier
> joints × 7 barrier levels); all 16 combinations of extreme distal-joint values in
> collision (the redundancy invariance the proof will make exact); free on both sides.

### 2.8 § 7.5 — temps de vérification (H26)

> … PROOF, 2 leaves, verify 2.43 s. …
> … PROOF, 4 leaves (2 collision, 2 outside), verify 2.50 s. …

### 2.9 § 7.6 — table (H28, H29, H26)

| Scene | DOF | active | leaves | engine | certify (end to end) | verify | ground truth |
|---|---|---|---|---|---|---|---|
| Planar relay (E3) | 2 | 2 | 46 | 0.48 s | — | 0.09 s | — |
| Comb | 3 | 2 | 54 | 1.36 s | — | 0.17 s | 0 / 300k |
| Shoulder-elbow (anchor) | 4 | 2 | 8 | 0.04 s | — | 0.04 s | 0 / 150k |
| iiwa-like bin | 5 | 3 | 8 | 0.15 s | 0.77 s † | 0.16 s | 0 / 40k |
| iiwa7 shelf (flagship) | 7 | 3 | 2 | 1.3 s | 46.7 s | 2.42 s | 0 / 40k + 448 corners |
| iiwa7 stacked crate | 7 | 3 | 2 | 1.3 s | 46.1 s | 2.43 s | 0 / 40k + 448 corners |
| iiwa7 safety guard | 7 | 3 | 4 | 1.6 s | 47.1 s | 2.50 s | 0 / 40k + 448 corners |
| Sealed wall, k = 3…7 | k | k | 2–4 | 0.1 – 65 s | 0.15 – 80 s | 0.01 – 6.8 s | 0 / 8k + 8k corner-biased |

> † Before the export contract (§3.7). "Engine" is the branch-and-bound decision alone;
> "certify" adds certificate export (and, for the iiwa7 scenes, the 39 s symbolic kinematics
> build). All PROOF, all exactly verified, dissonance counters zero.

*(Sources : relay/comb/anchor/bac **R6** + **CAL** ; iiwa7 **F12/B12/C12** `phases_s.branch_and_bound`,
`certify_s`, `verify_s` ; mur **WALL** `engine_s`, `engine_s + cert_s`, `verify_s`. Les « — » sont des
mesures qui n'existent pas : `run_benchmark.py` ne chronomètre pas l'export.)*

### 2.10 § 7.7 — micro-canal (H32)

> … an 11³ grid finds no free sample in the slab; a denser sampling finds free
> configurations in it; the engine refuses (UNDECIDED) and never writes a certificate.

### 2.11 § 7.8 — reproductibilité (H35, H36, H37)

> The verifier, the scene files and the certificates of the three iiwa7 scenes are released
> with the paper. The verifier is a single standard-library module: `cnp.verify.verify_file`
> re-proves a certificate in exact arithmetic with no third-party package installed. The
> command-line form `cnp verify <cert> <scene>` adds the cross-check against the authored
> scene file, which parses YAML and needs the package's dependencies. The other rows of
> §7.6 are regenerated by `cnp certify` and the benchmark scripts, which require the
> generator's dependencies (NumPy, SymPy, PyYAML, HiGHS); Drake is needed only to re-derive
> the frozen iiwa7 kinematics and body from Drake's model. Figure 1 reads its numbers from
> the dated benchmark file, not retyped.

### 2.12 § 8 — fit et coût FK (I3, I5)

> … The automatic fitting pipeline is validated with exact verification on a planar scene;
> it also found the barrier of a 3-DOF spatial scene that was certified before the spatial
> verifier existed. On a passive joint it over-fits …

> **Time.** The dominant cost is now symbolic kinematics construction: 39 s of 47 on the
> flagship, paid once per process (a second, cache-warm pass at export costs about 1 s);
> caching per scene, or Drake's rational kinematics directly, would remove most of it. …

### 2.13 § 9 — attribution des épisodes (J2) et unité (J3)

> … The episodes of §7.7 are the other half of the argument: dense sampling vouched for a
> disconnection that did not exist — once in a scene we had authored ourselves — and the
> requirement of a certificate refused it: the engine could not find a witness on every
> cell, so no certificate was written and the verifier was never reached. The verifier
> guards the opposite failure, a generator that would write a wrong certificate. Two
> artefacts that did lie — figures — …

> *"The iiwa is not exact."* Correct, and neither is its URDF (§4). We certify a rational
> kinematics that reproduces the published description to 2·10⁻⁶ m at the flange.

*(À propager hors §§ 6-9 : Abstract l.36, §1 l.135 et l.152 — même unité.)*

---

## 3. Mesures faites cette session (hors dépôt, aucune écriture dans le repo)

### 3.1 Hauteur du sommet du lien 3 en fonction du tangage d'épaule (H20, H21)

`scenes._body_fk` + les 40 sommets de `S6_iiwa_real_shelf.yaml`, autres joints à 0, même calcul
que `topz` de `scripts/flagship_iiwa_real_groundtruth.py:126-127` :

| s₂ | q₂ | sommet (m) |
|---|---|---|
| 0 | 0° | **0,8080** |
| ±1/5 (bord de dalle) | ±22,62° | 0,7775 / 0,7757 |
| ∓3/5 (start / goal) | ∓61,93° | **0,5967** |
| ±7/10 (bord de boîte) | ±69,98° | **0,5442 / 0,5449** |

Observation annexe : à q₂ = 61,9°, faire varier q₁ et q₃ sur la boîte fait monter le sommet de
0,566 à **0,627 m** (toujours sous 0,68). `JOURNAL.md:2926` (« q1 et q3 laissent z INVARIANT »)
n'est donc vrai qu'à q₂ = 0 ; le brouillon ne reprend pas cette affirmation.

### 3.2 Limites constructeur iiwa7 (H18)

Lues dans le plant Drake construit par `scripts/build_iiwa7_chain.py:_extract` :
j1, j3, j5 **±2,9671 rad (±170°)** ; j2, j4, j6 **±2,0944 rad (±120°)** ; j7 **±3,0543 rad (±175°)**.
Le tirage `uniform(-2.9, 2.9)` sort des limites sur j2, j4, j6.

### 3.3 Colonnes des LP réduit et plein sur le flagship (G14)

`witness.build_witness_lp` sur la paire unique du flagship, `active_dims = (0,1,2)` puis `None` :


| LP | K | colonnes λ (`nz`) | `nmu` | colonnes totales | lignes |
|---|---|---|---|---|---|
| réduit, dims (0,1,2) | 40 | 160 | 6 | **167** | 1 070 |
| plein, 7 dims | 40 | 320 | 6 | **327** | 473 870 |

Le plein reproduit **A44** (`flagship_S6.cols = 327`, `rows = 473870`) ; le réduit reproduit
**F12** (`cost_leaf_reduced_rows = 1070`). Les 40 sommets pèsent donc sur les colonnes des **deux** LP.

### 3.4 Vérification sans aucun paquet tiers (H35)

`env -i … python -S -I` (site-packages désactivé), `sys.path = src` :
`cnp.verify.verify_file('scenes/S6_iiwa_real_shelf.cert.json')` → `True, "PROOF verified exactly:
2 leaves (2 collision, 0 outside) …"` ; modules numpy / sympy / yaml / scipy / highspy / pydrake /
cvxpy chargés : **aucun**. (6,1 s sous charge, la suite de tests tournait en parallèle.)

---

## 4. Décisions de supervision requises (proposées, NON appliquées)

### D-P2-A — L'unité « rad » du chiffre de fidélité cinématique [J3]

Le 1,99·10⁻⁶ est une erreur de **position** (m). « rad » apparaît dans le brouillon (Abstract,
§1 ×2, §9), le squelette (l.31, l.190) **et dans une règle** : `CLAUDE.md` règle 9, corollaire A41
(« fidélité … plafonnée par la précision de l'URDF publié (~2e-6 rad mesuré) »). Code ne modifie
pas une règle de sa propre initiative (règle 14). **Proposition** : « ~2e-6 m (position de la bride,
1 500 configurations), axes du SDF alignés à ~3,7e-6 rad » dans la règle, le squelette et le papier.

### D-P2-B — Des chiffres du papier ne viennent pas d'un JSON daté [G1, G11, H10, H22]

La convention binding du squelette dit « numbers only from dated benchmark JSONs ». Ne la tiennent
pas : le balayage de levier (+175 / −73…−299 mm, journal seulement) ; les 150 000 échantillons de S3 ;
le compte de 40 000 de la vérité-terrain iiwa7 ; les 4,9 s de double vérification ; le 581,5 s.
**Deux issues** : (a) élargir la convention à « JSON daté **ou** entrée de journal mesurée et datée »
— coût nul, honnête ; (b) archiver ces mesures en JSON datés lors de `make reproduce` (S14).
**Recommandation** : (a) pour le preprint, (b) en S14.

### D-P2-C — Benchs post-S12 à `git_dirty = true` ; bac S4 non re-benché [H2, H15]

Les trois benchs iiwa7 cités par le papier (**F12/B12/C12**) ont été écrits d'un arbre sale (commit
`dbaaab8`). Et le bac S4 n'a que des chiffres **pré-contrat d'export** (juin). Aucune des deux choses
n'affecte un verdict (verify arbitre, certificats livrés re-vérifiés par la suite), mais un relecteur
qui ouvre les JSON verra le drapeau. **Proposition** : dire les deux dans le papier (phrases §2.4 et
§2.6) maintenant ; re-bench propre des 8 lignes de §7.6 dans `make reproduce` (S14).

### D-P2-D — Certificats livrés vs lignes des tables [H36]

Seuls les trois certificats iiwa7 (plus `S5_iiwa_shelf`, absent du papier) sont au dépôt.
**Proposition** : phrase honnête maintenant (§2.11) ; livrer les certificats de relay, comb, anchor,
bac et mur en S14 avec `make reproduce`. Et décider du sort de `S5_iiwa_shelf.cert.json` (pré-S12,
sans compteurs L6) : le garder comme artefact iiwa-LIKE ou le retirer de ce que le papier appelle
« released ».

---

## 5. Récapitulatif

**Vérifié : 66 affirmations** (§ 6 : 15 ; § 7 : 38 ; § 8 : 7 ; § 9 : 6).

- **FAUX : 9** — G14 (silhouette « gratuite » dans le LP réduit : ×11 en colonnes, mesuré),
  H4 (oracle corps-convexe « toujours » : trois scènes sur huit), H7 (parité « coefficient par
  coefficient » avec un « SOS » : c'est t\* par cellule contre un oracle Bernstein-LP), **H21**
  (« ±62° … 0,545 m » : 0,597 m à ±62°, 0,545 m à ±70°, mesuré), H29 (« 72 s » : aucune clé),
  **H35** (« no third-party package » pour `cnp verify <cert> <scene>`), **H36** (certificats des
  tables « released » : 3 sur 8), **J2** (épisodes « attrapés par l'artefact indépendant » : c'est le
  moteur qui refuse, le vérificateur n'a rien vu), **J3** (« 2·10⁻⁶ rad » : ce sont des mètres).
- **IMPRÉCIS / NON SOURCÉ : 16** — G2, G10, G12, H2, H8, H14, H15, H16, H18, H22, H26, H28, H32, H37,
  I3, I5.
- **VRAI mais à préciser : 3** — G1 (provenance journal), G8 (budget 300 s, pas 1 800), G13
  (« export time », pas « solve time »).
- **VRAI : 36.**
- **Hors périmètre (A28, références externes) : 2** — G15 (colonnes externes de la table § 6.4),
  H12 (« minutes on a CPU »).

**Les trois points qu'un relecteur attaquerait en premier** : (1) **§ 7.8 / H35-H36** — la promesse
de reproductibilité est la première chose qu'on teste, et la commande annoncée importe numpy et
yaml ; la vraie propriété (le module `verify` re-prouve sans aucun paquet tiers) est **mesurée** et
plus forte que ce qu'on croyait devoir concéder. (2) **§ 9 / J2** — la note au relecteur attribue au
vérificateur un rattrapage fait par le moteur ; c'est l'argument central de la section, il faut le
réattribuer. (3) **§ 7.6 / H28-H29** — la colonne « certify » mélange trois définitions et contient
un nombre qu'aucun fichier ne porte.

**Écarts hors brouillon**, relevés au passage (aucun appliqué) : unité « rad » dans la règle 9
(D-P2-A) ; `JOURNAL.md:2926` sur l'invariance de z en q₃ (vraie seulement à q₂ = 0, §3.1) ; bloc
`budget` de `wall_resonde_S9f.json` qui ne décrit pas la ligne k = 8 (G8) ; `calibration.json` et
`A44_columns_check.json` sans commit (H2).
