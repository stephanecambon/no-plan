# CLAUDE.md — certified-noplan

Version 1.5 — 11 juin 2026 (révision post-S6 ; v1.0..v1.4 dans git).
Règles binding pour Claude Code (modèle : Opus) + plan de développement par
sessions. Lire SPEC.md avant toute session. Tenir JOURNAL.md à jour.

Changements v1.0 → v1.1 : S0-S2 actées ; protocole de **validation visuelle
humaine** (règle 11) ; anti-dérive de SPEC (règle 12) ; anti-skip silencieux
(règle 13). Changements v1.1 → v1.2 (revue S3, annotations A8-A10) : règle 11
amendée — la validation ne bloque jamais le commit du code ; S3 actée ; S8
re-scopé (cvxpy réveille mosek à l'import ⟹ HiGHS déjà défaut depuis S3) ;
note heuristique d'axe en S9. Changements v1.2 → v1.3 (revue S4, annotations
A11-A14) : S4 actée ; CONTRAT engine↔verify « coupe au milieu » (A14, règle 9) ;
gardes d'ouverture S5 (A12 q*≠0 bruyant sur chemin sympy ; A13 arrondi λ
adaptatif + boucle de re-résolution) ; figures prêt-papier slab-aware (A11 →
S11). Changements v1.3 → v1.4 (revue S5, annotations A15-A17) : S5 actée ;
gouvernance CLAUDE.md (règle 14) ; circuit doc par diffs journalisés (les revues
ne livrent plus de fichiers entiers — le repo est l'unique source de vérité) ;
verdicts à trois statuts PROOF / ENGINE-PROOF / UNDECIDED (S6) ; résidus v1.3
appliqués (A11 → S11). Changements v1.4 → v1.5 (revue S6, annotations A18-A20) :
S6 actée, **G1' franchie** ; `margin` devient le défaut pour toute scène nouvelle
(A10 tranché par les faits : peigne 3-DOF 736 FAIL oracle vs 54 feuilles margin) ;
« dims passives par intervalles » devient la tâche n°1 de S8 (A18) ; fit STRUCTURÉ
des dims passives en S9 (A19) ; critère « apparence faisable » ajouté aux
checklists V4-V6 (A20) ; vue sweep + nommage physique des axes deviennent des
composants standard en S11 (D10). Revue V4 (S7, A21/A23) : checklist V4 amendée — une
scène de BENCHMARK doit répondre aux objections naturelles (vue de côté + sweeps lacet
ET tangage, contrainte bloquante explicite) ; « apparence faisable » (A20) réservé aux
scènes-vitrines V5/V6 (non négociable) ; tableau de correspondance géométrique
papier↔YAML archivé (A21) ; **[A24] artefact de validation principal d'une scène
spatiale = HTML interactif auto-suffisant (`cnp show --interactive`) — curseurs,
collision visuelle, fantômes start/goal sur toutes les vues, boutons d'évasion ;
chaque vue déclare ce qu'elle montre** (règle 11 amendée, standard V4-V6) ; **[A25]
limites articulaires explicites partout (encadré figures, cadre=limites sur C-space,
butées des curseurs = limites, verdict CLI rappelle ses hypothèses en degrés)**. Détail :
entrées « Revue de supervision » de JOURNAL.md.

---

## Règles non négociables

1. **Soundness avant tout.** On ne « fait jamais passer un test » en affaiblissant
   un certificat. Tout changement dans witness.py / engine.py / verify.py exige de
   relancer la suite adversariale (`pytest tests/test_adversarial.py` dès qu'elle
   existe — S6 ; d'ici là, les contrôles négatifs de test_witness/test_exp34). Si un
   certificat passe sur une prémisse fausse : STOP, bug bloquant, rien d'autre
   n'avance.
2. **Le signe de Putinar est g − μT ≥ t** (g + μT est unsound — démontré par
   tests/test_putinar_sign.py et test_witness_sign_is_frozen sur instances à
   prémisse réellement fausse). Le paramètre `_putinar_sign` n'existe que pour ces
   tests ; interdiction de l'utiliser ailleurs ou de changer le défaut.
3. **Aucun SDP, aucun Mosek dans le chemin critique.** Bernstein-LP uniquement.
   Le SOS de cross-check vit dans tests/regref.py, jamais importé par src/cnp.
   Attention : le wheel Drake tire mosek en transitif — un test-garde (S3) vérifie
   qu'aucun import du cœur ne le réveille.
4. **verify.py est sacré** : < 500 lignes, `fractions.Fraction` seulement,
   FK rationnelle recalculée indépendamment (même substitution demi-angle « maison »
   que ratfk, ré-implémentée — c'est le but de l'approche C choisie en S1), aucune
   importation depuis le générateur. Toute feature du générateur doit être
   vérifiable par verify.py AVANT d'être mergée.
5. **Tout résultat affiché = vérifié.** Un run n'est « certifié » que si
   `cnp verify` retourne OK en arithmétique exacte. Sinon le verdict affiché est
   UNDECIDED, même si le générateur dit avoir réussi.
6. **Honnêteté des verdicts** : UNDECIDED ≠ infaisable ≠ faisable. Les messages
   utilisateur et le README le disent explicitement.
7. **Reproductibilité** : toute randomisation est seedée ; chaque run de benchmark
   écrit dans benchmarks/results/<date-heure>/ (jamais d'écrasement) avec le
   commit hash.
8. **Discipline de session** : une session = un objectif de la liste ci-dessous.
   On n'attaque pas la session N+1 si les critères de sortie de N ne sont pas
   verts. Fin de session : mise à jour de JOURNAL.md (Fait / Décisions / Pièges /
   Prochaine étape), commit.
9. **Pièges connus à ne pas redécouvrir** : signe de Putinar (règle 2) ; coupes
   dyadiques vs frontières de dalle non dyadiques (⟹ certificat slab-aware
   obligatoire) ; **la grille d'échantillonnage ne fait pas foi** (micro-canal raté
   par 41 points, attrapé par le certificateur) ; profondeur de b&b = paramètre de
   coût, pas de faisabilité ; coin (3,3) des homogènes = den, pas 1 (bug S1) ;
   padder D et φ² au degré de travail DPAD avant Bernstein (piège S2) ;
   **CONTRAT [A14, v1.3] : le moteur ne coupe les cellules QU'AU MILIEU** —
   verify reconstruit le pavage sous cette hypothèse ; tout point de coupe
   « intelligent » casserait la vérification (faux rejet) : si nécessaire un
   jour, amender engine ET verify ET la SPEC dans le même commit ; verify
   calcule Bernstein AU MÊME DEGRÉ que le générateur (plus bas = borne plus
   lâche = faux rejets, piège S4) ; q* est absorbé dans s pour les joints
   débloqués (piège S4 — garde A12 en S5).
10. **macOS arm64** : Python Homebrew 3.12, venv `.venv`, `make setup`
    (installe `.[drake,dev]` depuis S1). Modèles Drake téléchargés une fois
    (cache local) ; pré-télécharger avant les sessions qui en dépendent (S9-S10).

11. **Validation visuelle humaine (NOUVEAU).** À chaque point marqué **[V*]** dans
    le plan, la session DOIT s'arrêter et demander une validation à Stéphane avant
    de continuer, au format exact suivant :

    ```
    === DEMANDE DE VALIDATION VISUELLE (S<X>-V<k>) ===
    Commande à lancer : <commande exacte, copiable>
    Ouvrir            : <fichier PNG / URL Meshcat http://localhost:PORT>
    Vérifier          :
      1. <point de contrôle concret et observable>
      2. <...>
      3. <...>
    Critère de réussite : <phrase unique, binaire>
    Réponse attendue  : « VALIDÉ S<X>-V<k> » ou description de l'anomalie.
    ```

    La session ATTEND la réponse (fin de tour) ; les critères de sortie de la
    session incluent la validation obtenue. COMMIT [A8, v1.2] : le code de la
    session est commité IMMÉDIATEMENT en fin de travaux (message
    « S<X> — V<k> pending ») ; la validation obtenue fait l'objet d'un
    micro-commit de clôture consigné au journal. Une validation en attente
    bloque le passage à la session suivante, jamais la sauvegarde du travail.
    PORTÉE : la validation visuelle vérifie
    **l'intention et la conception** (la scène est bien celle qu'on veut prouver,
    la figure raconte la bonne histoire). Elle ne vérifie JAMAIS la soundness —
    l'œil humain rate les micro-canaux aussi ; seul le certificat + verify fait
    foi sur la vérité mathématique. Ne jamais présenter une validation visuelle
    comme une preuve.
    **[A24] Artefact principal pour une scène SPATIALE = interactif ou animé.**
    L'artefact de validation principal d'une scène spatiale est un
    **`cnp show <scene> --interactive`** exportant un **HTML auto-suffisant** (curseurs
    articulaires, détection de collision visuelle, fantômes start/goal, boutons rejouant
    les tentatives d'évasion naturelles avec verdict) — ou, à défaut, un GIF animé de ces
    tentatives. Les figures statiques restent des compléments. De plus : (a) les poses
    start/goal apparaissent en **fantômes étiquetés sur TOUTES les vues d'espace de
    travail** (pas seulement en symboles dans le C-space) ; (b) **chaque vue déclare ce
    qu'elle montre** (bras complet vs bras supérieur/corps certifié seul). Standard pour
    V4 (livré S7) et obligatoire pour V5/V6.
    **[A25] Limites articulaires EXPLICITES partout.** Le théorème prouve la déconnexion
    DANS les limites articulaires (la boîte P) : elles doivent donc être affichées, en
    degrés (q = 2·arctan(s)), sur (a) un **encadré « limites : ... »** sur chaque figure ;
    (b) une mention **« le cadre de ce graphe = les limites articulaires »** sur les
    C-space (le rectangle tracé EST la boîte) ; (c) les **butées des curseurs = les
    limites** dans l'artefact interactif, dit explicitement, degrés affichés ; (d) le
    **verdict CLI** (`certify` et `verify`) qui rappelle ses hypothèses à chaque
    PROOF/ENGINE-PROOF : limites en degrés + pas de wrap-around (⊂ (−π,π)) + obstacles
    statiques + corps = polytopes + géométrie exacte. Helpers `viz.joint_limits_deg` /
    `viz.limits_caption`.

12. **Anti-dérive de spec (NOUVEAU).** Si l'implémentation diverge délibérément de
    SPEC.md (exemples actés en S1-S2 : s = tan((q−q*)/2) avec q* de référence au
    lieu de tan(θ/2) ; dénominateur commun PAR LINK ; exposant p=1 suffisant), la
    session qui acte la divergence AMENDE SPEC.md dans le même commit, avec mention
    « amendé en S<X> ». Une spec fausse est pire que pas de spec. Amendements en
    attente : voir S4.

13. **Aucun skip silencieux aux sorties de session (NOUVEAU).** `make test` peut
    skipper des tests réseau au quotidien, mais les critères de sortie d'une
    session listent explicitement les tests REQUIS, et un skip sur un test requis
    = sortie rouge. La sortie de session colle le décompte exact
    (passed/skipped/warnings) dans JOURNAL.md.

14. **Gouvernance de CLAUDE.md (NOUVEAU, A15).** Code PEUT modifier CLAUDE.md
    pour : (a) réconcilier avec des décisions de supervision journalisées,
    (b) tenir l'« État d'avancement », (c) le changelog. Code ne modifie JAMAIS
    de sa propre initiative une règle, un critère de sortie ou une porte. Tout
    diff de CLAUDE.md est listé dans l'entrée de journal de la session.
    Corollaire (A16) : les revues de supervision ne livrent plus de fichiers
    CLAUDE.md entiers (risque de copie périmée) — elles livrent une entrée de
    journal + instructions de diff explicites, appliquées en tâche d'ouverture
    de la session suivante. Le repo est l'unique source de vérité.

## Definition of Done (rappel global)

Démonstrateur : `cnp certify scenes/S5_iiwa_shelf.yaml` produit un certificat
7-DOF vérifié en arithmétique exacte + visualisation Meshcat + tables de
benchmark vs Li-Dantam (4-DOF) — portes G0'-G4' dans SPEC §8.

---

## État d'avancement

- ✅ **S0** — environnement, squelette, régression E1-E4 (**G0' vert**, 43 tests).
- ✅ **S1** — FK rationnelle 3D, Drake + repli sympy, parité < 1e-9 (51 tests).
- ✅ **S2** — témoin 3D slab-aware n-dim, parité E3 < 1e-7, exit 3-DOF 1e5
  échantillons / 0 violation, isolation back-end prouvée (HiGHS cross-check)
  (65 tests).
- ✅ **S3** — moteur b&b n-dim : work-queue parallèle à certificat
  octet-identique (3.56× / 8 workers), checkpoint/resume kill-9 avec empreinte
  SHA, HiGHS par défaut (mosek-free), garde Mosek 3 volets, make test-fast,
  figures (82 tests, 0 skip). **V1 validée** (annotation A11 → S11, voir JOURNAL.md).
- ✅ **S4** — certificat JSON exact (certificate.py) + vérificateur indépendant
  exact (verify.py, 498 lignes, Fraction-only, zéro import du générateur) + CLI
  `cnp verify`. Round-trip E3 (46) / E4 (78) reproduisant l'oracle, vérifiés en
  exact ; 26 mutations adversariales toutes rejetées ; SPEC §2/§4/§5 amendée
  (cond. i en espace-s, q* absorbé, schéma finalisé) (117 tests, 0 skip).
- ✅ **S5** — pipeline φ (phifit.py) : échantillonnage seedé + fit SVM / moindres
  carrés (oracle de collision générique) + δ auto (quantile de marge ∩ cond. i) +
  boucle de retry ; gardes d'ouverture A12 (q*≠0 refusé sur chemin sympy) et A13
  (arrondi λ adaptatif + boucle de re-résolution sur verify exact). E4-planaire
  certifié+vérifié via le pipeline complet (76 feuilles) ; scène 3-DOF spatiale
  certifiée moteur-PROOF + 0 point libre dans la dalle sur 300k échantillons
  (130 tests, 0 skip). **V2 validée** (figures phi_E4/phi_3dof).
- ✅ **S6** — parser YAML (scenes.py) → modèle Scene exact ; obstacles box/H-rep,
  hull extrait du link ; CLI `cnp certify` bout-en-bout + `cnp verify cert scene`
  (cross-check scène) + `cnp show` Meshcat minimal ; **verdicts à trois statuts
  PROOF / ENGINE-PROOF / UNDECIDED (A17)** ; builtin `spatial_revolute` côté
  moteur (→ ENGINE-PROOF). **G1' vert** : S2-peigne 3-DOF certifié end-to-end +
  vérifié exact (54 feuilles) + 0 point libre / 300k ; suite adversariale
  tests/test_adversarial.py (micro-canal : grille grossière 0-libre mais moteur
  refuse) zéro faux certificat ; SPEC §6 amendée (149 tests, 0 skip). **V3 validée**
  (figures workspace/C-space/sweep du peigne + 3R spatial).
- 🟡 **S7** — code vert, **V4 validée côté figures, widget A24 livré (re-soumission)**.
  Scène épaule-coude 4-DOF fidèle (Li-Dantam RSS2021) → ENGINE-PROOF + 0 libre/300k ;
  harness benchmarks/ + table comparative honnête + balayage dims passives (margin plat
  8 / oracle 8→36) ; figures sweep+côté+C-space + **widget interactif HTML
  (`cnp show --interactive`, A24)** + table géométrie A21 (158 tests, 0 skip).
  **Réserve G3'** : la moitié « + vérifiée (exact) » est reportée à S9 (verify spatial)
  — Option A actée avec Stéphane.

---

## Plan de développement (sessions Opus) — tenu à jour (voir changelog)

Chaque session : **Entrée** / **Tâches** / **Sortie** (critères vérifiables).
Une session = un contexte Opus ; si débordement, couper au critère partiel le
plus proche et journaliser.

### S3 — Moteur branch-and-bound n-dim (engine.py)
- Entrée : S2 vert (re-vérifier : `make test`, 65 passed attendus).
- Tâches :
  1. Généraliser à n dims le flot de référence documenté dans le scaffold b&b de
     tests/test_witness.py (test outside par Bernstein de φ, heuristique d'axe :
     frontière de dalle d'abord, puis pire marge LP des échecs) ;
  2. checkpoint/resume sur disque ; parallélisme multiprocessing sur les
     feuilles ; budgets (temps, profondeur, feuilles) avec verdict UNDECIDED
     propre et diagnostic (cellules en échec exportées) ;
  3. le moteur émet les données de partition (cellules, statuts, paires, marges)
     dans un format consommable par les figures ;
  4. `make figures` : figures de partition pour les scènes de régression E3/E4
     (généralisation de sandbox_reference/make_figure.py) ;
  5. **test-garde Mosek** : après import de cnp + un solve témoin, asserter que
     `mosek` ∉ sys.modules (règle 3) ;
  6. `make test-fast` (sous-ensemble < 30 s, sans les rejouages E1/E2 SOS) vs
     `make test` complet (requis en sortie de session).
- **[V1] Validation visuelle** : figures de partition E3 et E4.
  Vérifier : (1) bande dalle (or) continue entre start et goal, aucune cellule
  FAIL (noir) ; (2) relais des trois couleurs de paires (UP/DOWN/MID) cohérent
  avec le panneau vérité-terrain ; (3) raffinement des cellules concentré près
  des frontières de dalle et des zones de relais, pas uniforme.
- Sortie : E3/E4 certifiées via le nouveau moteur (mêmes feuilles/statuts que
  l'oracle à heuristique égale, ou écarts journalisés) ; test resume (kill -9 en
  cours de run, reprise, même certificat) ; speedup parallèle ≥ 3× sur 8 cœurs ;
  garde Mosek verte ; **V1 validée** ; décompte exact des tests dans le journal.

### S4 — Certificat + vérificateur exact (certificate.py, verify.py)
- Entrée : S3 vert.
- Tâches :
  1. Format JSON SPEC §4 ÉTENDU et amendé (règle 12) : ajouter **q_star**, joints
     verrouillés (valeurs cos/sin exactes utilisées), définition explicite de la
     substitution demi-angle « maison » (approche C de S1) et du dénominateur
     commun par link — tout ce que verify recalcule doit être défini dans le
     certificat ou la scène, pas dans le code du générateur ;
  2. rationnels exacts, arrondi vers l'intérieur avec re-résolution si la marge
     ne couvre pas ;
  3. verify.py from scratch : Fraction uniquement, substitution demi-angle
     ré-implémentée indépendamment, vérification de l'arbre (partition exacte),
     des feuilles outside (Bernstein φ) et collision (Σλ≡1, λ≥0, g − μT ≥ 0) ;
  4. CLI `cnp verify` ; **amender SPEC §2 et §4** (q_star, D par link, p=1).
- Sortie : round-trip generate→verify OK sur toutes les scènes de régression ;
  test de mutation : ≥ 20 certificats corrompus (coeff λ, μ, coupe, paire,
  q_star) ⟹ tous rejetés ; audit imports de verify (règle 4) ; SPEC amendée.

### S5 — Pipeline φ (phifit.py)
- Entrée : S4 vert.
- Tâches : échantillonnage C_free/C_obs (collision checker Drake, seedé) ; fit
  SVM + approximation polynomiale deg ≤2/var ; sélection δ automatique
  (quantiles de marge + condition (i)) ; boucle de retry (si UNDECIDED : re-fit
  pénalisant les cellules en échec).
- **[V2] Validation visuelle** : pour E4-planaire puis pour le 3-DOF, figure
  « C-space échantillonné + lignes de niveau de φ + dalle ».
  Vérifier : (1) la bande {|φ|≤δ} est entièrement dans la zone collision
  échantillonnée (rappel : l'échantillon ne prouve pas — on vérifie l'INTENTION,
  le certificat tranchera) ; (2) start (★) et goal (✚) de part et d'autre avec
  marge visible ; (3) δ pas dégénéré (bande visible, pas un trait).
- Sortie : E4-planaire reproduit via le pipeline complet ; sur la scène 3-DOF de
  S2 : φ trouvé automatiquement et certifié sans hint manuel ; **V2 validée**.

### S6 — Scènes, CLI et visualisation minimale (scenes.py + YAML + cnp show)
- Entrée : S5 vert.
- Tâches :
  1. Parser YAML SPEC §6 (sommets/coupes rationnels) ; extraction des enveloppes
     convexes des links depuis la géométrie de collision (branchement sur
     `vertex_numerators` de S1) ;
  2. scènes S1 (régression) et S2 « peigne 3-DOF » finalisées ;
  3. **`cnp show scene.yaml`** : visualisation Meshcat minimale (robot aux configs
     start/goal commutables, obstacles, repères) — avancé depuis S11, car
     l'inspection visuelle de la géométrie AVANT certification fait partie de la
     conception de scène ;
  4. CLI `cnp certify <scene>` bout-en-bout ; **verdicts à trois statuts
     PROOF / ENGINE-PROOF / UNDECIDED (A17)** : PROOF = vérifié exact ;
     ENGINE-PROOF = moteur OK mais vérification exacte indisponible (ex. 3-DOF
     spatial avant S9), TOUJOURS affiché avec son avertissement ; UNDECIDED =
     pas de certificat. README et messages alignés (règles 5/6) ;
  5. suite adversariale initiale tests/test_adversarial.py (obstacles rétrécis,
     micro-canal inséré exprès).
- **[V3] Validation visuelle** : `cnp show scenes/S2_peigne.yaml`, ouvrir l'URL
  Meshcat affichée (typiquement http://localhost:7000).
  Vérifier : (1) le bras 3-DOF est dessiné aux configs start puis goal (bascule
  indiquée par la session) et n'intersecte visiblement aucun obstacle dans ces
  deux poses ; (2) le peigne a le bon nombre de dents, aux positions du YAML,
  échelle plausible (~mètres) ; (3) les enveloppes convexes des links recouvrent
  bien le maillage visuel du robot (pas de link « nu »).
- Sortie : **G1'** — S2-peigne certifiée end-to-end (`cnp certify` → `cnp verify`
  OK) + zéro faux certificat sur l'adversarial ; **V3 validée** ; demo console
  propre.

### S7 — Ancrage Li-Dantam (scène S3, 4-DOF)
- Entrée : G1'.
- Tâches : retrouver scènes/code Li-Dantam (web autorisé) ; reproduire la scène
  bookshelf 4-DOF (sinon ré-implémentation documentée depuis arXiv 2406.04795 /
  2501.11434) ; harness benchmarks/ ; premier tableau comparatif (leurs temps
  publiés vs nôtres) ; **produire la vue sweep de la scène (A20)** (éventail des
  poses start→goal, collisions en rouge — montre pourquoi le chemin a l'air
  faisable).
- **[V4] Validation visuelle** : **artefact PRINCIPAL = `cnp show <scene>
  --interactive` (HTML auto-suffisant, A24)** ; figures statiques (sweep dessus + côté
  + C-space) en compléments ; côte-à-côte vs figure du papier (référence citée).
  Vérifier : (0) **[A23] la figure RÉPOND AUX OBJECTIONS NATURELLES du spectateur**
  (« pourquoi pas par-dessus / autour ? ») — vue de CÔTÉ montrant la hauteur réelle
  des obstacles vs la portée du bras, ET les sweeps pertinents (lacet ET tangage),
  en disant EXPLICITEMENT quelle contrainte bloque (hauteur de mur vs limite
  articulaire). NB A23 : le critère A20 strict « apparence faisable » est réservé aux
  scènes-VITRINES V5/V6 (non négociable là-bas) ; une scène de BENCHMARK doit avant
  tout désamorcer les objections, pas forcément « avoir l'air faisable » ; (1) même
  topologie d'obstacles (nombre, agencement relatif) ; (2) même robot / mêmes joints
  actifs ; (3) start/goal qualitativement conformes au scénario du papier ;
  (4) **[A21] tableau de correspondance géométrique papier↔YAML archivé** (longueurs,
  dimensions d'obstacles, limites articulaires — ce qui est fidèle vs choisi par nous,
  les chiffres du papier n'étant pas publiés) dans benchmarks/.
- Sortie : **G3'** — S3 certifiée + vérifiée, tableau dans benchmarks/results/,
  écarts commentés honnêtement dans JOURNAL.md (y compris si on est plus lents à
  4-DOF : le titre se joue à 5+) ; **V4 validée**.

### S8 — Performance (back-end HiGHS direct, profiling)
- Entrée : S7 vert. NOTE v1.2 [A9] : le défaut HiGHS est DÉJÀ acté (S3, via
  scipy.linprog), conséquence de la découverte « import cvxpy réveille mosek » ;
  et l'isolation back-end était acquise dès S2. Cette session = optimisation
  pure.
- Tâches :
  1. **[A18, TÂCHE N°1] dimensions passives par intervalles** (lignes (d+1)^k au
     lieu de (d+1)^n) : le risque n°1 s'est matérialisé dès n=3 (S6, peigne :
     UNE dim passive s2 ⟹ axe `oracle` gaspille la profondeur, 736 feuilles /
     256 FAIL / UNDECIDED, là où `margin` certifie en 54). Mitigation prioritaire
     car c'est le levier de G2' (S9 5-6 DOF) ;
  2. highspy direct sur WitnessLP (API bas niveau, warm starts entre cellules
     sœurs) ; exploitation de la sparsité des tenseurs FK ; degré de témoin
     adaptatif par feuille ; profiling (py-spy) ; ré-évaluer fork vs spawn une
     fois les workers mono-thread (solder les 20 DeprecationWarning fork) ;
     **élucider les 5 warnings Clarabel** journalisés depuis S0 (résoudre ou
     documenter pourquoi structurellement bénins).
- Sortie : sur la scène S3 : ≥ 10× plus rapide que cvxpy ; mémoire bornée ;
  **le peigne 3-DOF certifie avec `axis=oracle` après mitigation (la profondeur
  n'est plus gaspillée dans la dim passive)** ; aucun changement de verdict sur
  la suite complète + adversarial (soundness re-validée) ; warnings traités.

### S9 — Scène S4 (bac profond, 5-6 DOF)
- Entrée : S8 vert. Pré-télécharger les modèles Drake (hors-ligne interdit ici :
  les tests iiwa sont REQUIS, règle 13).
- Tâches : iiwa joints verrouillés (7→5 puis 6) ; conception géométrique de la
  scène bac ; **vue sweep de la scène (A20)** ; vérité-terrain par échantillonnage
  dense AVANT certification (intention seulement — leçon du micro-canal) ; tuning
  heuristiques d'axe —
  NOTE [A10, TRANCHÉ (S6)] : `margin` = défaut pour toute scène nouvelle ;
  `oracle` = parité de régression uniquement (données : peigne 3-DOF, 736 FAIL
  oracle vs 54 feuilles margin ; S3 : margin bat l'oracle sur E4, 56 vs 78,
  perd sur E3, 54 vs 46) — levier anti-explosion n°1 pour G2'. **Fit STRUCTURÉ
  [A19]** : pénaliser/zéroter les coeffs des dims passives détectées (par
  sensibilité) au fit φ — leçon S6 : lstsq surajuste un degré-2 parasite sur la
  dim passive s2 ⟹ φ tordu ⟹ UNDECIDED. Micro-tâche : mesurer feuilles(n) sur la
  même scène à n = 3,4,5,6 joints débloqués (distinguer dims actives/passives)
  pour ajuster l'exposant empirique du modèle de coût.
- **[V5] Validation visuelle — OBLIGATOIRE AVANT TOUT RUN LONG** :
  **artefact PRINCIPAL = `cnp show scenes/S4_bac.yaml --interactive` (HTML, A24)** ;
  + coupes 2D du C-space échantillonné (paires de joints les plus actives) +
  vue sweep (A20) en compléments.
  Vérifier : (0) **[A20] la scène a l'air FAISABLE — goal proche/visible, la vue
  sweep montre pourquoi on croirait passer** (scène-VITRINE, NON NÉGOCIABLE — A23) ;
  (1) le bac enferme réellement
  l'objet cible et la caisse avant bloque l'accès frontal — c'est bien le
  scénario « inatteignable sans retirer la caisse » qu'on veut PROUVER ;
  (2) start (home) et goal (prise) visuellement sans collision ; (3) sur les
  coupes C-space, la zone collision sépare plausiblement start de goal. Réponse
  « VALIDÉ S9-V5 » = autorisation de lancer les runs longs.
- Sortie : **G2'** — S4 certifiée < 1 h, < 10⁴ feuilles, verify OK ; **V5
  validée**. SI ROUGE : session(s) mitigations SPEC §9.1 avant S10 — point de
  pivot du projet, le journaliser comme tel ; la décision de re-scope se prend
  avec Stéphane, pas dans Claude Code.

### S10 — Flagship 7-DOF (scène S5)
- Entrée : G2'.
- Tâches : scène étagère iiwa complète ; **vue sweep de la scène (A20)** ;
  extrapolation de budget depuis S9 (feuilles, temps) présentée AVANT de lancer ;
  runs longs avec checkpoints ; si φ deg ≤2 insuffisant : φ par morceaux
  (théorème composé, amender SPEC).
- **[V6] Validation visuelle + go/no-go** : **artefact PRINCIPAL = `cnp show
  scenes/S5_iiwa_shelf.yaml --interactive` (HTML, A24)** + budget estimé (temps,
  feuilles, RAM) + vue sweep (A20) en compléments.
  Vérifier : (0) **[A20] la scène a l'air FAISABLE — goal proche/visible, la vue
  sweep montre pourquoi on croirait passer** (scène-VITRINE, NON NÉGOCIABLE — A23) ;
  (1) étagère + panneau obstruant
  conformes au scénario « case haute inatteignable depuis home » ; (2) home et
  goal sans collision visuelle ; (3) budget acceptable pour la machine (sinon :
  décision cloud avec Stéphane). « VALIDÉ S10-V6 » = autorisation du run flagship.
- Sortie : **G4'** — certificat 7-DOF vérifié exact ; **V6 validée** ; archiver
  certificat + scène + commit en l'état.

### S11 — Visualisation complète et assets (viz.py)
- Entrée : G4' (ou en parallèle après G2' si S10 traîne).
- Tâches : `cnp viz <cert>` complet (Meshcat : scène, configs, animation de la
  dalle projetée, feuilles en échec si UNDECIDED) ; figures C-space/partition
  généralisées (coupes pour n>2) ; tables/courbes de benchmark auto-générées.
  **[A11, V1]** : rogner ou hachurer la partie hors-dalle des feuilles
  slab-aware et tracer la frontière de dalle {|φ|=δ} sur le panneau partition
  (sans quoi un lecteur croit qu'on certifie de la collision en zone libre).
  **[D10, V3]** : la **vue sweep** (éventail des poses start→goal, collisions en
  rouge) et le **nommage physique des axes** (type d'articulation rotoïde/rotule,
  axes du C-space par leur sens — lacet/tangage) deviennent des composants
  STANDARD de `cnp viz` et des figures (leçon V3 : 5 itérations pour rendre la
  déconnexion lisible).
- **[V7] Validation visuelle** : pack de figures prêt-papier.
  Vérifier : (1) chaque figure raconte une histoire lisible sans légende orale ;
  (2) les chiffres des tables correspondent aux JSON de benchmarks/results/ ;
  (3) la figure flagship (7-DOF) est compréhensible par un non-spécialiste.
- Sortie : `cnp viz` fonctionne ; pack dans benchmarks/figures/ ; **V7 validée**.

### S12 — Durcissement
- Entrée : S11.
- Tâches : élargir l'adversarial (fuzzing de scènes à prémisse fausse,
  micro-canaux générés aléatoirement, limites frôlant ±π → refus propre) ;
  messages d'erreur ; README honnête (verdicts, hypothèses, limites).
- Sortie : CI complète verte, zéro skip requis ; zéro faux certificat sur ≥ 200
  scènes adversariales générées.

### S13 — Reproductibilité et buffer
- Entrée : S12.
- Tâches : `make reproduce` one-shot (toutes scènes + benchmarks + figures) ;
  gel des versions ; rattrapage ; revue finale JOURNAL → liste des claims
  soutenus par artefacts (matière à papier).
- Sortie : `make reproduce` regénère tout sur machine vierge ; tag v1.0.

---

## Estimation honnête (inchangée sur le fond)

S0-S2 ont tenu en 3 sessions nominales, ce qui est encourageant mais ne prédit
pas S9-S10 (les sessions à risque de recherche : explosion de feuilles, degré de
φ). 13 sessions nominales + 2-4 de contingence. Si G2' est rouge après
mitigations : re-scope avec Stéphane (résultat-titre à 5-6 DOF, toujours
au-delà de l'état de l'art rigoureux à 4) plutôt que forcer.
