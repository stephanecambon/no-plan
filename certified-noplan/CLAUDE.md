# CLAUDE.md — certified-noplan

Version 1.18 — 26 juin 2026 (révision post-S7/S8 + pilotage + D26 + revues S9a-suite/S9c/DECISION-G2/S9e/S9f/G4'/S10-bis/S10-ter + arbitrage robot réaliste S10 ; v1.0..v1.17 dans git).
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
entrées « Revue de supervision » de JOURNAL.md. Changements v1.5 → v1.6 (revue S7,
A26-A28) : **repositionnement état-de-l'art [A26]** — Li-Dantam scalent à 5-6 DOF sur
GPU (arXiv 2406.04795, vérifié S8) ; le récit « rigoureux plafonne à 4-DOF » est périmé ;
notre différenciateur = NATURE du certificat (algébrique, exactement revérifiable, CPU/LP,
murs réutilisables) ; **G3' scindée a/b** (G3'a S7 ✅ scène 4-DOF chiffrée ENGINE-PROOF /
G3'b S9 vérif exacte spatiale) ; G2'/G4' relus selon A26 ; **règle 9 amendée [A28]** —
toute référence externe est vérifiée à sa première utilisation ; harness enregistre
l'état git clean/dirty [A27]. Changements v1.6 → v1.7 (revue S8, A29-A31, D18-D21) :
**critère perf reformulé [D18]** — « ≥10× sur S3 » remplacé par « ≥10× de coût/feuille dès
2 dims passives (mesuré 28×-733×) ET S3 ≥5× bout-en-bout (mesuré 6×) », ✅ acquis, réserve
S8 levée ; **passivité RATIONNELLE [A29]** (diviser N_k ET D par (1+s_i²) en exact ⟹ détecte
le roll de S3) et **réduction par-paire des LP de feuille [A30, levier G2']** (passivité =
propriété de la PAIRE) en ouverture S9 ; **calibration du modèle de coût [A31]**. Changements
v1.7 → v1.8 (décision de pilotage Stéphane + supervision, D22-D25) : **S9 re-scopée go/no-go
technique pur** avec sortie **`DECISION-G2.md` signée par Stéphane avant S10** ; **S9b nouvelle
session** « portefeuille de cas d'usage » (bin-picking / étagère pharma / capot de sûreté,
validation VU) ; A20 « apparence faisable » RETIRÉ de V5 (déplacé en S9b/V6) ; S10 implémente
le flagship choisi en S9b, S11 += pack démo des deux autres cas. Détail : entrées « Revue de
supervision S8 » et « Décision de pilotage » de JOURNAL.md. Changement v1.8 → v1.9 (D26-D30) :
**règle 8 amendée — la clôture de session = commit ET push** (D26 ; sans push, le journal lu
par la supervision via GitHub a une session de retard ; le push de clôture lève la règle
globale « jamais de push sans demande ») ; **[D27]** « Estimation honnête » re-cadrée
(re-scope 5-6 DOF = frontière GPU Li-Dantam atteinte sur laptop CPU, certificat exactement
revérifiable — différenciation par la NATURE du certificat A26, pas par le DOF) ; **[D30]**
règle 12, « Amendements en attente : voir S4 » (périmé) supprimé. Diffs SPEC jumeaux du même
lot : **[D28]** §8 G1' marquée ✅ (acquise S6) ; **[D29]** §1 « l'un des deux verdicts » →
« l'un des trois verdicts » (PROOF / ENGINE-PROOF / UNDECIDED, cf. §6).
Changements v1.9 → v1.10 (revue S9a-suite, **[A32]**) : **S9a ✅ COMPLÈTE validée** par
la supervision ; **[D31]** instrumentation de la dissonance décision↔certificat
(compteur de re-résolution pleine-dim échouée sur feuille décidée collision, asserté à
ZÉRO sur les runs S4) ; mesure PAR-PAIRE (proximale vs distale) ajoutée à la table de
calibration A31. Détail : entrée « Revue de supervision S9a-suite » de JOURNAL.md.
Changements v1.10 → v1.11 (revue S9c, **[A33-A34]**) : **S9c validée** (verify joints
verrouillés à 499 l. sans le pré-arbitrage 600 ; format §4 `{cos,sin}` ré-aligné, SPEC v1.6 ;
A32 livrée) ; **[D33]** arbre git PROPRE vérifié à l'ouverture, modification pré-existante
journalisée (règle 8) ; **[D34]** discipline de flake aux tests requis (consigné + re-run
isolé ; `test_parallel_speedup` isolé si la suite vient de charger la machine).
Détail : entrée « Revue de supervision S9c » de JOURNAL.md.
Changements v1.11 → v1.12 (revue DECISION-G2 + pilotage mur, **[A35-A36]**, D36-D41) : **GO
endossé sous amendements** ; **[A35]** portée proximale = **effet de SÉLECTION** de notre schéma
(barrière scalaire bas-degré + dalle), pas propriété intrinsèque des déconnexions — consigne de
conception ET **limite de portée assumée** (régime de coût (d+1)^actif à énoncer dans le papier) ;
**[A36]** références Li-Dantam 2023 « [à vérifier] » (IJRR 42(10) ET RA-L 8(12) existent toutes
deux, cf. BIBLIO-ANTERIORITE) ; **[D38]** V5 consignée ; **[D40]** bench du mur en dims actives
(S9e) versé à DECISION-G2.md §3d. Détail : entrées « Revue DECISION-G2 » + « pilotage mur » de
JOURNAL.md.
Changements v1.12 → v1.13 (revue S9e **[A37]** + pilotage S9f, **D42-D44**) : **GO confirmé et
SIGNÉ** (Stéphane 13/06 + supervision S9e du §3d) ; **[D42]** DECISION-G2.md §3d : mur k=5
requalifié « **pratique** » (la subdivision Bernstein converge en théorie ⟹ pas « structurel ») +
cause de terminaison à documenter (placeholder → addendum §3d-bis S9f) + ceinture « **dans des
cadres différents** » sur le claim vs Henrion et al. (nécessaire-et-suffisant sur ensembles abstraits
vs suffisant sur bras articulés) ; **[D44]** tâche **S9f** (re-sonde du mur, L0 diagnostic + L1
Bernstein anisotrope) insérée au plan, **S9b glisse** après S9f. La signature de Stéphane vaut avec
les retouches D42 actées. Détail : entrées « Revue de supervision S9e » + « Pilotage S9f » de JOURNAL.md.
Changements v1.13 → v1.14 (revue S9f **[A38]**, D45-D46) : **re-sonde du mur ENDOSSÉE — renforçante**
(le « mur k=5 » était un artefact : max_depth=16 silencieux + scène leaky ; sur scènes prouvées étanches,
PAS de mur affine k≤7 — PROOF + verify exact ; frontière = taille du LP unique (d+1)^k, ~470k l. à k=7) ;
**[A38-1]** §3d-bis « proximales-style » → « famille à **barrière simple** » (le bench certifie le dernier
link, toutes dims actives — *pas* proximal) ; **[A38-2]** deadline k=8 explicitée (300 s ; solve LP atomique
⟹ overrun à 455 s) ; **[D45]** renvois inline de supersession au §2/§5.3 de `DECISION-G2.md` (corps signé non
réécrit) ; **[D46]** header v1.14 + ce changelog. **Calibrage S9b** : flagship choisi par RÉCIT + VALEUR (la
faisabilité d'un piège proximal est acquise — LP minuscule, secondes). Détail : entrée « Revue de supervision
S9f » de JOURNAL.md.
Changements v1.14 → v1.15 (arbitrage robot réaliste S10, **[A39]**, D47-D49) : à la présentation V6,
Stéphane demande « une vraie scène 3D + robot réaliste » ⟹ **Option A recadrée** (Stéphane + supervision) :
on NE re-scope PAS S10 (finir le flagship **iiwa-LIKE** : V6 → certif → clôture G4', banc sanctionné A21),
et le **vrai KUKA iiwa devient le flagship d'EN-TÊTE livré en S10-bis** (montée en gamme, pas correction
d'un faux). **[A39]** flagship d'en-tête papier/deck = vrai iiwa (S10-bis) ; iiwa-LIKE = validation méthodo.
**[A21 résolu]** spike Drake du 18/06 : FK iiwa7 rationnelle à q\*=0 (rotations inter-liens = permutations
signées ±90° ⟹ cos/sin rationnels ⟹ forme `verify.py` S9c, INTACT) ⟹ iiwa réel faisable, ni POE ni
extension de verify ; **[D47]** renvoi inline §5 DECISION-G2.md, **[D48]** section S10-bis insérée au plan,
**[D49]** ce header+changelog. Détail : entrée « Décision de pilotage — arbitrage robot réaliste » de JOURNAL.md.
Changements v1.15 → v1.16 (revue G4', **[A40]**, D50-D51) : **G4' ACQUISE** sur banc iiwa-LIKE sanctionné
(PROOF + verify exact + A32=0, 8 feuilles, ×612 A30, verify.py zéro diff) ; **[A40]** tout artefact de viz à
valeur d'ARGUMENT exige un invariant TESTÉ reproduisant l'oracle de vérité (règle 11 amendée, D50) — bug S10
de l'interactif A24 (base du corps à l'origine monde) attrapé par le test de parité JS=oracle ; **[D51]** ce
header+changelog. S10-bis (vrai iiwa, flagship d'en-tête) confirmé non optionnel. Détail : entrée « Revue de
supervision G4' / S10 » de JOURNAL.md.
Changements v1.17 → v1.18 (revue S10-ter, **[A43]**, D55-D56) : **robot iiwa ENTIÈREMENT défini gelé** —
cinématique (`iiwa7_chain.json`, 1,99e-6) ET silhouette (`iiwa7_body_link3.json`, corps convexe fidèle 40
sommets, parité 1,67e-6 < plancher SDF), verify.py zéro diff ; dims actives RE-MESURÉES (0,1,2), distaux
passifs AUTOMATIQUEMENT (corps proximal après q3). **[A43]** la fidélité géométrique du CORPS change la
difficulté de conception du piège (corps-segment = grand levier ⟹ piège lacet de base facile ; corps à
silhouette réelle = compact ⟹ levier disparu ⟹ séparation lacet de base marginale ~6 mm, refusée) → règle 9 ;
le piège proximal franc d'un robot réaliste vient d'un séparateur à grand levier (pitch d'épaule) ou d'un
obstacle enfermant (coin/wedge), PAS du lacet de base ; corollaire vérité-terrain : un corps K-sommets exige
un oracle corps-convexe vs H-rep (LP), pas l'échantillonnage de segment de `collision_oracle` ; **[D55]** A43
→ règle 9 ; **[D56]** ce header+changelog. Détail : entrée « Revue de supervision S10-ter » de JOURNAL.md.
Changements v1.16 → v1.17 (revue S10-bis, **[A41-A42]**, D52-D54) : **convention iiwa7 RÉSOLUE** et chaîne
rationnelle verify-compatible gelée (`scripts/iiwa7_chain.json`, parité Drake 1,99e-6, verify.py zéro diff) ;
**critère parité Option A RATIFIÉ** (« fidèle au SDF ~4e-6 + interne exact + verify-exact » — doctrine A21
étendue à la cinématique ; le seuil <1e-9 était inatteignable, le SDF iiwa7 n'est aligné aux axes qu'à
~3,67e-6) ; **[A41]** toute tolérance de FRANCHISSEMENT d'un prompt de supervision est vérifiée contre la
PRÉCISION DE LA SOURCE avant d'être imposée (→ règle 9, à côté d'A28) ; corollaire papier : fidélité physique
plafonnée par la précision URDF publié (~2e-6), énoncer « fidèle à l'URDF iiwa7 à 2e-6 près », PAS « le iiwa
exact » ; **[A42]** `test_parallel_speedup` (timing ≥3×) structurellement fragile (flaké S9a/S9c/S10-bis sous
charge) : 4e occurrence ⟹ le rendre robuste OU le sortir du `make test` requis vers un bench séparé, jamais un
re-run silencieux (→ S10-ter sortie + esprit règle 13) ; **[D52]** A41 → règle 9 ; **[D53]** A42 → section
S10-ter + esprit règle 13 ; **[D54]** ce header+changelog. Détail : entrée « Revue de supervision S10-bis »
de JOURNAL.md.

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
   verts. **Ouverture [D33, A33]** : la session vérifie `git status` PROPRE ; toute
   modification pré-existante du working tree (run partiel antérieur non commité,
   etc.) est **journalisée** avant d'être absorbée ou écartée — un état à constater
   explicitement, jamais à absorber en silence. Fin de session : mise à jour de
   JOURNAL.md (Fait / Décisions / Pièges / Prochaine étape), **commit ET push [D26]**.
   Le push est partie intégrante de la clôture : sans lui, le journal que la
   supervision lit via GitHub a une session de retard. (D26 lève, pour la clôture de
   session, la règle globale « jamais de push sans demande » — la clôture EST la
   demande permanente, actée par Stéphane.)
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
   débloqués (piège S4 — garde A12 en S5). **[A28, S8] Toute référence externe
   (papier, chiffre, benchmark, arXiv) citée dans SPEC/CLAUDE.md est VÉRIFIÉE à sa
   première utilisation par la session qui s'en sert** (leçon S7 : deux arXiv mal
   attribués par la supervision ; corrigé S7-S8). **[A41, S10-bis] Toute TOLÉRANCE DE
   FRANCHISSEMENT (seuil de parité/précision) posée dans un prompt de supervision est
   vérifiée contre la PRÉCISION DE LA SOURCE avant d'être imposée** (même esprit qu'A28 :
   on vérifie la source avant d'affirmer). Leçon : « parité <1e-9 vs Drake » était
   inatteignable — le SDF iiwa7 n'est aligné aux axes qu'à ~3,67e-6 (quaternions arrondis)
   et verify.py porte des axes rationnels ; reformulé « fidèle au SDF ~4e-6 + interne exact »
   (doctrine A21 étendue à la cinématique). Corollaire papier : la fidélité au robot PHYSIQUE
   est plafonnée par la précision de l'URDF publié (~2e-6 rad mesuré), pas par la méthode —
   énoncer « cinématique fidèle à l'URDF iiwa7 à 2e-6 près », PAS « le iiwa exact ».
   **[A43, S10-ter] La FIDÉLITÉ GÉOMÉTRIQUE DU CORPS change la difficulté de conception du
   piège.** Tout le projet a piégé des corps-SEGMENTS (grand levier ⟹ déconnexion par lacet de
   base facile, S5/S6) ; un corps à SILHOUETTE RÉELLE est compact ⟹ le levier disparaît ⟹ la
   séparation par lacet de base devient marginale (vrai link3 iiwa : ~6 mm mesuré, REFUSÉ à
   juste titre — ne pas graver une déconnexion que la marge ne soutient pas, lignée pas-de-×400
   appliquée à la géométrie). Sur un robot réaliste, le piège proximal FRANC vient d'un
   séparateur à GRAND LEVIER réel (pitch d'épaule) ou d'un obstacle ENFERMANT (coin/wedge, sans
   levier articulaire), PAS du lacet de base. **Corollaire vérité-terrain** : un corps convexe
   à K sommets exige un oracle CORPS-CONVEXE vs H-rep (LP de faisabilité), PAS l'échantillonnage
   de SEGMENT de `collision_oracle` (scenes.py) — sinon vérité-terrain fausse ⟹ régression
   micro-canal/scène-leaky. C'est aussi un RÉSULTAT du papier (un humain ne voit pas qu'un blob
   proximal est piégé — l'outil le prouve).
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
    **[A40, revue G4'] Invariant TESTÉ pour toute viz à valeur d'ARGUMENT.** Un artefact de
    visualisation qui porte un argument (collision, atteignabilité, séparation des composantes —
    pas seulement de l'habillage) DOIT être adossé à un test qui reproduit l'oracle de vérité et
    asserte l'égalité (ex. S10 : la logique JS FK+collision de l'interactif A24 rejouée sous `node`
    contre `scenes.collision_oracle`, 0 écart). La discipline verify (« sound parce qu'on
    recompte ») s'étend à la viz argumentative : sans cet invariant, un gate visuel peut valider un
    artefact qui ment (bug S10 : base du corps prise à l'origine monde, attrapé par le test).

12. **Anti-dérive de spec (NOUVEAU).** Si l'implémentation diverge délibérément de
    SPEC.md (exemples actés en S1-S2 : s = tan((q−q*)/2) avec q* de référence au
    lieu de tan(θ/2) ; dénominateur commun PAR LINK ; exposant p=1 suffisant), la
    session qui acte la divergence AMENDE SPEC.md dans le même commit, avec mention
    « amendé en S<X> ». Une spec fausse est pire que pas de spec.

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
- ✅ **S7** — **V4 validée** (« VALIDÉ S7-V4 »). Scène épaule-coude 4-DOF fidèle
  (Li-Dantam RSS2021) → ENGINE-PROOF + 0 libre/300k ; harness benchmarks/ + table
  comparative honnête + balayage dims passives (margin plat 8 / oracle 8→36) ; figures
  sweep+côté+C-space + **widget interactif HTML (`cnp show --interactive`, A24)** +
  table géométrie A21 + limites explicites partout (A25) (158 tests, 0 skip).
  **G3' SCINDÉE (revue S7, A26)** : **G3'a ✅ ACQUISE en S7** (scène 4-DOF fidèle
  chiffrée, ENGINE-PROOF + contrôles : start/goal libres, 0 libre/150k dalle, libre
  des deux côtés, contrôle négatif refusé) ; **G3'b = vérification exacte spatiale,
  livrée avec S9** (`spatial_revolute` dans verify.py).
- ✅ **S8** — perf. **Tâche n°1 [A18] dims passives par intervalles livrée** : le moteur
  détecte les joints passifs (`engine.passive_dims`), ne branche jamais dessus, et réduit
  chaque LP de cellule aux dims actives (`(d+1)^k` au lieu de `(d+1)^n`). **Le peigne 3-DOF
  certifie maintenant avec `axis=oracle`** (46 feuilles + vérifié exact, vs UNDECIDED/736).
  Back-end **highspy direct** (défaut moteur, Mosek-free) ; parallélisme **forkserver**
  par défaut (les 20 DeprecationWarning fork résolues) + 5 warnings Clarabel documentés
  (cross-check SOS test-only). Soundness re-validée (suite + adversarial, 0 changement de
  verdict). **Honnêteté perf** : le gain back-end seul est ~2× (PAS 10×) ; le ≥10× vient
  de la réduction `(d+1)^k` (mesuré 7× à 1 dim passive → 733× à 4) — sur S3 (1 dim passive
  détectée) ~6× bout-en-bout. **Critère « ≥10× sur S3 » REFORMULÉ par la revue S8 [D18] et
  ✅ ACQUIS, réserve LEVÉE** : « ≥10× de coût/feuille dès 2 dims passives (mesuré 28×-733×)
  ET S3 ≥5× bout-en-bout (mesuré 6×) ». Détection rationnelle plus fine (roll de S3) traitée
  en S9 [A29]. (voir JOURNAL.md S8 + revue S8.)
- ✅ **S9a** (coupe de S9, COMPLÈTE) — **G3'b acquise** : `verify.py` (sacré, 499 lignes)
  vérifie en arithmétique exacte les chaînes `spatial_revolute` (FK 3-D re-dérivée des
  `joints` offset/axe du certificat ; axe unitaire exigé). **S2b ET l'ancrage 4-DOF S3
  passent ENGINE-PROOF → PROOF** (G3'a renforcée). **RÉDUCTIONS livrées (S9a-suite)** :
  **[A29] passivité RATIONNELLE** — division exacte de N_k ET D par (1+s_i²) (test
  structurel slice0==slice2, slice1==0) ⟹ **le roll de S3 est enfin détecté passif**
  (`passive_dims(S3)` = (2,3), était (3,)) ; **[A30] réduction PAR-PAIRE** — chaque LP de
  feuille réduit aux dims actives de SA paire (`_PairView`), branchement sur l'union
  globale. Architecture soundness S8 préservée (décision seulement, cert re-résolu pleine
  dim, **verify.py INTACT** — 499 l., zéro diff). Bonus non-porte : **S3 ~19× de coût LP
  bout-en-bout** (feuilles × lignes Bernstein, ≥10× acquis). Suite adversariale (spatiale +
  planaire) + frontière à deux couches re-vertes ; **178 passed, 0 skip, 0 warning** (170 +
  8 `test_reductions.py`) ; SPEC v1.5, CLAUDE.md v1.9. **Reste de S9 (= S9c)** : scène 5-6
  DOF (iiwa, modèles Drake déjà en cache), calibration feuilles(n)+coût/feuille (A31/D20),
  **G2'**, `DECISION-G2.md` signée, joints VERROUILLÉS dans verify (Rot(angle) cos/sin §4 —
  pré-arbitrage 500→600 l. UNE fois si la factorisation ne suffit pas), **V5** (gate humain).
  Circuit doc S8→S9 appliqué (header v1.9, S9 re-scopée, S9b insérée, D27-D30). (voir JOURNAL.md S9a.)
- ✅ **S9c** (coupe de S9, tâches 1-2) — **joints VERROUILLÉS dans `verify.py`** (sacré, 499 l.,
  **pré-arbitrage 600 NON utilisé** — factorisation suffisante) : `_body_fk` substitue la
  rotation numérique exacte (`cos²+sin²=1` vérifié), ré-indexe les débloqués 0..n−1 ; **format §4
  `locked_joints={cos,sin}` ré-aligné** (dérive S4-S9a qui stockait l'angle, corrigée ; SPEC v1.6,
  règle 12). Une scène q*=0 verrouillée = **PROOF**. 9 tests adversariaux (verrou déplacé/corrompu/
  retiré). **[A32] instrumentation** : compteur `n_reresolve_failed` (dissonance décision↔certificat,
  bruyant, asserté ZÉRO sur S3). **188 passed, 0 skip, 0 warning** ; CLAUDE.md v1.10. **Reste de S9
  (= S9d)** : scène iiwa 5-6 DOF, calibration (+ par-paire), **G2'**, `DECISION-G2.md` signée, **V5**
  (gate humain). (voir JOURNAL.md S9c + revue S9c.)
- ✅ **S9d** (coupe de S9) — **scène S4 iiwa-like bac profond 5-DOF** (piège PROXIMAL, 2 joints
  verrouillés ; bac technique documenté A21) ; **V5 VALIDÉE** (Stéphane) ; **calibration** feuilles=8
  constant / coût-feuille réduit 766 constant vs plein →93 878 (réduction A30 ×122 à 6-DOF), par-paire
  ×24,6 ; **G2' VERT** ; **`DECISION-G2.md` = GO** (revue supervision endossée sous amendements
  A35-A36). **189 passed, 0 skip, 0 warning** ; CLAUDE.md v1.11. (voir JOURNAL.md S9d + revue DECISION-G2.)
- ✅ **S9e** (coupe de S9) — **bench du mur en dimensions ACTIVES** (pilotage Stéphane :
  « apporter des mesures aux limitations ») : famille synthétique paramétrée par k = dims actives
  DÉTECTÉES (k=3,4,5(,6)), chaque point une VRAIE déconnexion (vérité-terrain dense AVANT certif),
  budget plafonné (10⁴ feuilles/30 min ⟹ UNDECIDED-budget = donnée) ; confronte l'hypothèse coût
  ×(d+1)^actif. **Sortie : DECISION-G2.md §3d « scaling wall »** (la version SIGNÉE par Stéphane).
  Application de la revue (D36-D38). **Revue S9e [A37] : GO confirmé et signé** (mur k=5 requalifié
  « pratique », claim Henrion ceinturé — D42).
- 🔄 **S9f** (coupe de S9, AUTONOME — pas de gate humain ; le GO signé est inchangé) — **re-sonde du
  mur en dimensions ACTIVES** : **L0** diagnostic de la cause de terminaison du run k=5 (instrumentation
  `termination` dans `EngineResult.stats`) + re-run à profondeur relevée et budget RÉEL ; **L0b**
  anomalie du LP quadratic ; **L1** Bernstein anisotrope (degré par axe ; chemin de DÉCISION seulement ;
  verify.py INTACT, format cert inchangé). **Sortie : addendum §3d-bis daté** dans DECISION-G2.md (le
  corps signé n'est pas réécrit au-delà de D42), verdict GO inchangé. Puis : **S9b** (en connaissance de
  la frontière re-mesurée). (D42-D44, v1.13 ; voir JOURNAL.md « Pilotage S9f ».)

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
- Sortie [critère perf REFORMULÉ par la revue S8, D18 — réserve levée] : **≥10× de
  coût de décision par feuille dès 2 dims passives détectées (mesuré 28×-733×) ET
  S3 ≥5× bout-en-bout (mesuré 6×)** ✅ (l'ancien « ≥10× sur S3 » était un mauvais
  proxy : S3 n'a qu'1 dim passive détectée ; refus du 10× cosmétique) ; mémoire
  bornée ; **le peigne 3-DOF certifie avec `axis=oracle` après mitigation (la
  profondeur n'est plus gaspillée dans la dim passive)** ✅ ; aucun changement de
  verdict sur la suite complète + adversarial (soundness re-validée) ; warnings
  traités ✅. **S8 verte (réserve levée).**

### S9 — Go/no-go technique pur (scène 5-6 DOF, G2' + G3'b) [RE-SCOPÉE, pilotage D22]
- Entrée : S8 vert. Pré-télécharger les modèles Drake (hors-ligne interdit ici :
  les tests iiwa sont REQUIS, règle 13). **Coupes autorisées (règle 8) si le contexte
  sature** : **S9a** (réductions A29/A30 + **G3'b**) / **S9c** (scène + G2' +
  `DECISION-G2.md`). État S9a : **COMPLÈTE** — G3'b LIVRÉE (verify spatial, S2b+S3 → PROOF) ;
  **réductions A29/A30 LIVRÉES** (roll S3 détecté passif, LP par-paire, ~19× S3, verify intact).
- Tâches d'ouverture [revue S8, D19/D20] :
  1. **[A29] passivité RATIONNELLE** : diviser N_k ET D par (1+s_i²) en exact ; si tout
     divise, simplifier et marquer le joint passif (le roll de S3 est géométriquement
     passif mais le dénominateur commun par link l'habille d'un (1+s2²) que le détecteur
     tensoriel garde). Test bonus (non-porte) : S3 ≥10× bout-en-bout.
  2. **[A30, LE levier G2'] réduction par-paire des LP de feuille** : la passivité est une
     propriété de la PAIRE — pour une paire sur le link k, tous les joints en aval de k
     sont passifs POUR CE LP. Réduire chaque LP de feuille aux dims actives de SA paire
     (le choix d'axe de partition reste sur l'union des actifs). **Même architecture de
     soundness que S8** : réduction au chemin de DÉCISION seulement, certificat re-résolu
     en pleine dim, `verify.py` (sacré) arbitre en pleine dim ⟹ une réduction buggée ne
     peut produire au pire qu'un ENGINE-PROOF. Tests (règle 1) : t_réduit==t_plein par
     paire, 0 changement de verdict, adversarial re-vert.
  3. **G3'b** [LIVRÉE S9a] : `spatial_revolute` dans verify.py (FK 3-D exacte re-dérivée
     des `joints`) ⟹ scènes spatiales q*=0 sans joint verrouillé = PROOF. **Reste pour
     l'iiwa** : support des joints VERROUILLÉS dans verify (Rot(angle) rationnelle exacte,
     format cos/sin §4) — sous le plafond 500 lignes (sinon point à arbitrer).
- Tâches scène : iiwa joints verrouillés (7→5 puis 6) ; **scène choisie pour la
  COMPARABILITÉ** — si les scènes 5/6-DOF des papiers scaling Li-Dantam (2406.04795 /
  RA-L 2023) sont descriptibles, en refléter une (reproduction approchée documentée,
  précédent S7) ; sinon bac technique (choix documenté) ; vérité-terrain par
  échantillonnage dense AVANT certification (intention seulement — leçon du micro-canal).
  NOTE [A10, TRANCHÉ (S6)] : `margin` = défaut. **Fit STRUCTURÉ [A19]** : pénaliser/zéroter
  les coeffs des dims passives détectées au fit φ (leçon S6 : lstsq surajuste un degré-2
  parasite ⟹ φ tordu ⟹ UNDECIDED).
- Micro-tâche calibration [A31/D20/**D31**] : mesurer **feuilles(n) ET coût/feuille** avec la
  réduction par-paire activée, à n = 3,4,5,6 (distinguer dims actives/passives, globales
  ET par-paire) ; **mesure PAR-PAIRE (proximale vs distale) sur la scène bac S4 — première
  validation réelle du levier A30** ; wall-clock S3 capturé à la régénération du benchmark
  canonique ; **livrer la table de calibration du modèle de coût** (feuilles × coût/feuille
  vs DOF actifs/passifs, globales ET par-paire) — réviser les estimations de temps de la
  supervision.
- Micro-tâche instrumentation [**A32/D31**] : **compteur/log moteur de re-résolution
  pleine-dim ÉCHOUÉE sur feuille décidée collision** (dissonance décision↔certificat : le
  chemin de décision tourne sur la géométrie A29-simplifiée, la re-résolution pleine dim sur
  la géométrie originale — deux LP sur des polynômes différents ; bénigne au pire — UNDECIDED,
  jamais un faux PROOF — mais coût silencieux possible à l'échelle). Exposé dans les stats du
  moteur et le harness ; **asserté/vérifié à ZÉRO sur les runs de la scène S4** (déjà zéro
  empiriquement sur S3, margin et oracle).
- **[V5] Validation visuelle — OBLIGATOIRE AVANT TOUT RUN LONG** [A20 RETIRÉ de V5,
  déplacé en S9b/V6 — pilotage D22] :
  **artefact PRINCIPAL = `cnp show <scene> --interactive` (HTML, A24)** + coupes 2D du
  C-space échantillonné (paires de joints les plus actives) en complément + **limites
  articulaires explicites (A25)**.
  Vérifier : (1) le bac/l'obstacle enferme réellement la cible et bloque l'accès — c'est
  bien le scénario d'infaisabilité qu'on veut PROUVER ; (2) start (home) et goal
  visuellement sans collision ; (3) sur les coupes C-space, la zone collision sépare
  plausiblement start de goal. (NB : « apparence faisable » A20 N'est PLUS un critère ici —
  S9 est un go/no-go technique, pas une vitrine ; A20 revient non négociable en S9b/V6.)
  Réponse « VALIDÉ S9-V5 » = autorisation de lancer les runs longs.
- **Discipline de tests [D34, A34]** : tout flake d'un test REQUIS est consigné au journal
  (cause + re-run isolé) — pas de re-run silencieux de la suite ; `test_parallel_speedup`
  (test de TIMING ≥3×, flaké S9a/S9c sous charge) est exécuté ISOLÉ si la suite vient de
  charger la machine (esprit règle 13).
- **Sortie formelle : `DECISION-G2.md`** [pilotage D22] — verdict **G2'** chiffré (S4
  certifiée < 1 h, < 10⁴ feuilles, verify OK, `n_reresolve_failed`=0), calibration du modèle
  de coût (globale ET par-paire), comparaison aux chiffres GPU EXACTS de Li-Dantam,
  **recommandation GO / NO-GO / RE-SCOPE** ; revue par la supervision puis **SIGNÉE par
  Stéphane AVANT toute ouverture de S10**. **V5 validée**. SI ROUGE : mitigations SPEC §9.1 —
  point de pivot, journalisé comme tel ; la décision de re-scope se prend avec Stéphane, pas
  dans Claude Code.

### S9b — Portefeuille de cas d'usage (session légère) [NOUVELLE, pilotage D23]
- Entrée : S9 (machinerie G2' acquise ou en vue). Session de CONCEPTION produit, pas de
  recherche technique. Validation **VUE par Stéphane** (sa matière commerciale Cambon AI).
- Tâches : pour chacun des trois cas COMPLÉMENTAIRES (trois propositions de valeur du même
  certificat) — **bin-picking logistique** (élagage prouvé TAMP) / **étagère pharma**
  (portée 5-7 DOF) / **capot de sûreté · fenêtre opérateur** (auditabilité dossier-de-
  sûreté) : one-pager (claim, persona, valeur) ; spec de scène YAML (géométrie, robot,
  limites) ; storyboard des artefacts (figures + interactif, **critères A20 non négociable
  / A24 / A25**) ; critères d'acceptation. **Choix du cas FLAGSHIP pour S10.**
- Sortie : trois one-pagers + trois specs de scène + storyboards ; flagship désigné ;
  validation VUE par Stéphane.

### S10 — Flagship 7-DOF (le cas choisi en S9b) [D24]
- **[A39, arbitrage 18/06] EN COURS, V6 ouvert** : flagship = banc **iiwa-LIKE** sanctionné (A21),
  G4' technique (sans signature). Le **flagship d'EN-TÊTE (papier, deck) = vrai KUKA iiwa, livré en
  S10-bis** (montée en gamme, pas correction d'un faux). Ne PAS re-scoper S10 (Option A recadrée).
- Entrée : G2' (`DECISION-G2.md` signée) + flagship désigné en S9b.
- Tâches : **implémenter le flagship choisi en S9b** (scène 7-DOF complète) ; **vue sweep
  de la scène (A20)** ; extrapolation de budget depuis S9 (feuilles, temps) présentée
  AVANT de lancer ; runs longs avec checkpoints ; si φ deg ≤2 insuffisant : φ par morceaux
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

### S10-bis — VRAI KUKA iiwa (flagship d'EN-TÊTE) [A39, arbitrage 18/06]
Faisabilité acquise (spike Drake 18/06 : FK iiwa7 rationnelle à q\*=0 ⟹ forme `verify.py` S9c, INTACT).
**Ordre IMPOSÉ — la convention d'abord, la scène ensuite :**
1. **CONVENTION DE COMPOSITION EXACTE, dé-risquée par PARITÉ DRAKE avant tout travail de scène** :
   reproduire la FK iiwa7 (offsets rationnels du spike : 63/400, 0,183, 23/125, 431/2000, 161/2000 ;
   rotations inter-liens = permutations signées décomposées en rotations élémentaires x/y/z du groupe
   octaédrique) et vérifier la PARITÉ avec Drake `RationalForwardKinematics` (wrapper `ratfk.py` déjà au
   repo) à **<1e-9 sur ≥1000 configs** (méthode S1). Régler l'encadrement X_PF/X_MC de la rotation variable
   (2 essais ratés au spike) ICI, contre Drake — pas en aval. Tant que la parité n'est pas <1e-9, NE PAS
   passer à la scène.
2. **Géométrie** : choisir le lien proximal certifié + le panneau d'étagère sur la VRAIE géométrie iiwa
   (corps proximal réel, dims actives RÉELLES via `pair_views` — re-mesurer, ne pas présumer {0,1,2}).
   Sculpter le piège proximal (apparence faisable A20, guidée par les figures iiwa-LIKE) ; obstacle H-rep
   EXACT (étanche par construction) ; vérité-terrain dense uniforme + biaisé-coins (S9f).
3. **verify.py INTACT** (joints à cos/sin rationnels = mécanisme S9c déjà livré ; si une rotation exige
   autre chose que la forme supportée, STOP et signale — ne devrait pas arriver d'après le spike). **G4'
   RÉAFFIRMÉE sur le vrai robot** (PROOF + verify exact + A32=0). Interactif A24 + figures du vrai iiwa pour
   le papier. **Gate V6-bis** (A20 non négociable) sur la scène réelle.
- Repli : si la convention résiste au-delà du raisonnable, l'iiwa-LIKE certifié en S10 reste le G4' acquis ;
  S10-bis devient une dette explicite, pas un bloquant.
- ✅ **S10-bis ACTÉE** (18/06) : convention RÉSOLUE + parité Drake 1,99e-6 + chaîne gelée `iiwa7_chain.json`
  (Tâche 1) ; **coupe Tâche 1 → S10-ter** (Tâches 2-4). Revue S10-bis : A41-A42, v1.17.

### S10-ter — VRAI iiwa7 : scène + corps convexe fidèle + V6-bis + certif G4' (Tâches 2-4 de S10-bis) [coupe S10-bis]
Entrée : chaîne gelée `scripts/iiwa7_chain.json` (parité Drake 1,99e-6, verify-compatible). `verify.py` SACRÉ.
- **Tâche 2** : scène flagship sur la VRAIE géométrie iiwa (lien proximal certifié + panneau étagère) ; **corps =
  coque convexe fidèle (niveau 1)** dérivée du mesh de visu Drake, **sommets rationalisés** (`limit_denominator 1e6`,
  re-vérifiable exact) ; **dims actives RE-MESURÉES via `pair_views` — NE PAS présumer {0,1,2}** ; obstacle H-rep
  EXACT (étanche) ; vérité-terrain dense AVANT certif (uniforme + biaisé-coins 2^k, S9f ; A25 limites en degrés).
  Niveau 2 (décomposition multi-pièces) HORS périmètre.
- **Tâche 3** : interactif A24 du vrai iiwa (7 curseurs ; corps = coque fidèle ; verrouillés en cinématique fixe ;
  **invariant A40 JS=oracle TESTÉ**) + figures C-space/sweep ; A20 non négociable ; A25 par vue ; Meshcat 3D `cnp show`.
- **Gate V6-bis** (STOP, humain, A20 non négociable, AVANT certif) : interactif + figures + BUDGET de certif prédit
  (dims re-mesurées, lignes/LP, feuilles, wall-clock — terme dominant = re-résolution pleine-dim à l'export). Attendre
  « VALIDÉ S10-V6bis ».
- **Tâche 4 (après V6-bis)** : `cnp certify` → PROOF ; `cnp verify` OK ; A32=0 ; vérité-terrain ré-assertée ; mesuré
  vs budget commenté ; benchmark daté (règle 7). **G4' RÉAFFIRMÉE sur le vrai robot.** Caveat A41 (fidélité plafonnée
  par la précision URDF, modèle interne exact).
- **Discipline [A42, esprit règle 13]** : `test_parallel_speedup` est un BENCHMARK wall-clock (machine quiète), SORTI
  du `make test` requis vers `make bench-parallel` (marqueur `bench`) — exécuté en S10-ter après 4e flake sous charge
  desktop ; le décompte requis devient **201 passed + 1 bench déselectionné** (la référence quiète ~3,6× est journalée).
- Repli : coupe naturelle autorisée — si la Tâche 2 sature, clôturer sur scène + vérité-terrain + corps convexe ;
  V6-bis/certif → S10-quater. iiwa-LIKE (G4' S10) reste le filet.
- 🔄 **S10-ter ACTÉE (26/06), COUPE Tâche 2** : livrés = **corps convexe fidèle GELÉ** (`scripts/iiwa7_body_link3.json`,
  40 sommets du mesh de visu Drake lien 3, rationalisés, parité body 1,67e-6 ; test `tests/test_iiwa7_body.py`) +
  intégration chaîne→scène + **dims actives RE-MESURÉES = (0,1,2)** (passives 3,4,5,6 ; budget (d+1)^3 identique
  iiwa-LIKE). A42 exécuté. `make test` = **204 passed, 1 deselected, 0 skip/warn**. Finding : piège base-yaw MARGINAL
  sur le vrai link3 (blob compact, pas le levier du segment iiwa-LIKE). **Reste → S10-quater** : oracle corps-convexe
  vs H-rep ; piège FRANC (séparateur/obstacle/lien à arbitrer) ; vérité-terrain 0-libre ; interactif A24 + figures ;
  V6-bis ; certif G4' vrai robot. (voir JOURNAL.md S10-ter.)

### S10-quater — VRAI iiwa7 : piège franc + vérité-terrain + V6-bis + certif G4' (reste de S10-ter) [coupe S10-ter]
Entrée : corps convexe fidèle gelé `scripts/iiwa7_body_link3.json` (parité 1,67e-6) + chaîne gelée. `verify.py` SACRÉ.
- **Oracle corps-convexe** : `collision_oracle` n'échantillonne que le segment `hull[0]→hull[-1]` (scenes.py:364) —
  étendre à un test corps-convexe (K sommets) vs H-rep (LP de faisabilité indépendant, hors verify.py) AVANT toute
  vérité-terrain.
- **Piège FRANC** sur le vrai robot (le base-yaw sur link3 est marginal, ~6 mm) : arbitrer séparateur (q2 pitch à grand
  levier ?), forme d'obstacle (H-rep wedge ?), ou lien plus distal (>3 dims actives, budget S9f OK). A20 non négociable.
- Puis : vérité-terrain dense 0-libre (uniforme + biaisé-coins) ; interactif A24 (invariant A40 JS=oracle) + figures ;
  **gate V6-bis** ; certif G4' (PROOF + verify exact + A32=0) sur le vrai robot. Repli iiwa-LIKE inchangé.
- 🔄 **S10-quater ACTÉE (26/06), COUPE Tâche 2-3** : livrés = **oracle CORPS-CONVEXE vs H-rep** (`scenes.convex_collision_oracle`,
  LP ; test `tests/test_convex_oracle.py`) + **PIÈGE FRANC figé** `scenes/S6_iiwa_real_shelf.yaml` (séparateur = **q2
  pitch d'épaule** à grand levier, A43 ; obstacle = **étagère en surplomb** H-rep ; marge **~90 mm** vs 6 mm base-yaw ;
  corps = coque fidèle 40 sommets ; dims actives (0,1,2)) + **vérité-terrain dense** (`scripts/flagship_iiwa_real_groundtruth.py` :
  0 libre/40k slab, 0 libre/448 coins, invariance redondance, 2 côtés libres ; test `tests/test_flagship_iiwa_real.py`).
  `make test` = **208 passed, 1 deselected, 0 skip/warn**. **Reste → S10-quinquies** (ci-dessous). (voir JOURNAL.md S10-quater.)

### S10-quinquies — VRAI iiwa7 : interactif A24 + figures + V6-bis + certif G4' (reste de S10-quater) [coupe S10-quater]
Entrée : piège FRANC figé `scenes/S6_iiwa_real_shelf.yaml` (φ=q2, étagère surplomb, marge ~90 mm, vérité-terrain
dense 0-libre) + oracle corps-convexe. `verify.py` SACRÉ.
- **Tâche 4** : interactif A24 sur le vrai iiwa (curseurs 7 joints ; **corps = coque 40 sommets**, PAS un segment ;
  verrouillés en cinématique fixe ; **invariant A40 JS=oracle TESTÉ** sous node, cohérent avec l'oracle corps-convexe
  A43) ; fantômes start/goal (A24-a) ; chaque vue déclare ce qu'elle montre (A24-b) ; A25 par vue **avec ÉTIQUETTES
  D'AXES PHYSIQUES corrigées** (finding S10-quater : `viz.joint_limits_deg` lit l'axe-chaîne brut « z » pour tous les
  variables — dériver le type du joint de l'axe EFFECTIF locked·axis : q2 = pitch d'épaule). Figures C-space + sweep
  (A20 apparence faisable). Meshcat 3D `cnp show`.
- **Gate V6-bis** (STOP, humain, A20) : interactif + figures + budget de certif prédit (dims (0,1,2), (d+1)^3, feuilles
  ≈ banc iiwa-LIKE, wall-clock) + **MARGE FRANCHE mesurée (~90 mm)**. Attendre « VALIDÉ S10-V6bis ».
- **Tâche 5 (après V6-bis)** : `cnp certify` → PROOF ; `cnp verify` OK ; A32=0 ; vérité-terrain ré-assertée ; benchmark
  daté (règle 7). **G4' RÉAFFIRMÉE sur le vrai robot** (cinématique ~2e-6 + silhouette ~1,7e-6 + déconnexion franche).
  Caveat A41 (fidélité plafonnée par précision URDF, interne exact).

### S11 — Visualisation complète et assets (viz.py) + pack démo cas d'usage [D24]
- Entrée : G4' (ou en parallèle après G2' si S10 traîne).
- Tâches : `cnp viz <cert>` complet (Meshcat : scène, configs, animation de la
  dalle projetée, feuilles en échec si UNDECIDED) ; figures C-space/partition
  généralisées (coupes pour n>2) ; tables/courbes de benchmark auto-générées ;
  **[D24] pack démo des DEUX autres cas d'usage de S9b** (certifiés à 5-6 DOF via la
  machinerie S9) — chacun avec son interactif (A24), ses limites (A25) et son one-pager.
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
mitigations : re-scope avec Stéphane plutôt que forcer. **[D27] Re-scope à 5-6 DOF =
frontière GPU de Li-Dantam (arXiv 2406.04795) atteinte sur laptop CPU avec un
certificat exactement revérifiable — résultat fort, différencié par la NATURE du
certificat (A26), pas par le DOF** (le récit « seuls au-delà de 4-DOF » est périmé,
cf. SPEC §7 B1).
