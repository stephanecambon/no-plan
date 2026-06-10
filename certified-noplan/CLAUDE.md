# CLAUDE.md — certified-noplan

Règles binding pour Claude Code (modèle : Opus) + plan de développement par
sessions. Lire SPEC.md avant toute session. Tenir JOURNAL.md à jour.

---

## Règles non négociables

1. **Soundness avant tout.** On ne « fait jamais passer un test » en affaiblissant
   un certificat. Tout changement dans witness.py / engine.py / verify.py exige de
   relancer la suite adversariale (`pytest tests/test_adversarial.py`). Si un
   certificat passe sur une prémisse fausse : STOP, bug bloquant, rien d'autre
   n'avance.
2. **Le signe de Putinar est g − μT ≥ t** (g + μT est unsound — bug historique
   documenté, voir CAMPAGNE-E1-E4-RESULTATS.md §Leçons). Un test unitaire fige ce
   signe ; interdiction de le modifier.
3. **Aucun SDP, aucun Mosek dans le chemin critique.** Bernstein-LP uniquement
   (HiGHS/Clarabel). Les variantes SOS vivent dans `experimental/`, jamais
   importées par le cœur.
4. **verify.py est sacré** : < 500 lignes, `fractions.Fraction` seulement,
   recalcul indépendant de la FK symbolique, aucune importation depuis le
   générateur (sauf rien). Toute feature du générateur doit être vérifiable par
   verify.py AVANT d'être mergée.
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
   verts. Fin de session : mise à jour de JOURNAL.md (fait / décisions / pièges /
   prochaine étape), commit.
9. **Pièges connus à ne pas redécouvrir** (issus des campagnes E1-E4) :
   les coupes dyadiques n'atteignent jamais une frontière de dalle non dyadique
   (d'où le multiplicateur slab-aware, obligatoire) ; valider une scène par grille
   d'échantillonnage peut rater des micro-canaux (le certificateur fait foi, pas
   la grille) ; profondeur de branch-and-bound = paramètre de coût, pas de
   faisabilité (marges −0.002 ⟹ une bissection de plus).
10. **macOS arm64** : Python Homebrew 3.12 (PAS le Python système, PAS Anaconda),
    venv dédié, `pip install drake` (wheel officiel).

## Definition of Done (rappel global)

Démonstrateur : `cnp certify scenes/S5_iiwa_shelf.yaml` produit un certificat
7-DOF vérifié en arithmétique exacte + visualisation Meshcat + tables de
benchmark vs Li-Dantam (4-DOF) — voir portes G0'-G4' dans SPEC.md §8.

---

## Plan de développement (sessions Opus)

Chaque session : **Entrée** (préconditions), **Tâches**, **Sortie** (critères
vérifiables). Budget indicatif : une session = un contexte Opus focalisé ;
si une session déborde, on coupe au critère de sortie partiel le plus proche et
on journalise.

### S0 — Environnement, squelette, portage régression
- Entrée : repo vide, ce fichier + SPEC.md + les 4 scripts du bac à sable
  (polylin.py, exp12_ladder.py, exp34_multipair.py, make_figure.py).
- Tâches : venv + deps ; arborescence SPEC §3 ; porter polylin dans src/cnp/ ;
  transformer E1-E4 en tests pytest (les scènes planaires deviennent des
  fixtures) ; CI locale (make test).
- Sortie : **G0'** — pytest vert, t* identiques au bac à sable à 1e-6 près ;
  JOURNAL.md initialisé.

### S1 — FK rationnelle 3D (ratfk.py)
- Entrée : S0 vert. Drake importable.
- Tâches : wrapper RationalForwardKinematics → tenseurs numérateurs (X,Y,Z) par
  sommet d'enveloppe convexe de chaque link, dénominateur commun ; gestion des
  joints verrouillés ; REPLI si friction Drake : FK symbolique sympy (chaîne
  révolute générique), même interface.
- Sortie : test « FK numérique vs tenseurs » : 1000 configurations aléatoires
  iiwa, erreur < 1e-9 ; test joints verrouillés ; test degré ≤2/var par joint.

### S2 — Témoin 3D (witness.py)
- Entrée : S1 vert.
- Tâches : LP témoin slab-aware générique n-dim, corps convexe mobile vs polytope
  statique (H-rep) ; degré de λ paramétrable (constant/affine/quadratique) ;
  back-end cvxpy d'abord, interface back-end isolée.
- Sortie : sur S1-planaire embarquée en 3D : mêmes certificats qu'E3 ; sur un
  3-DOF spatial minimal : accord témoin vs vérité-terrain échantillonnée
  (certifie ⟹ aucun point libre trouvé sur 10⁵ échantillons de la cellule).

### S3 — Moteur branch-and-bound n-dim (engine.py)
- Entrée : S2 vert.
- Tâches : généraliser le moteur E3 à n dims ; heuristique d'axe (frontière de
  dalle d'abord, puis marge LP la pire) ; checkpoint/resume sur disque ;
  parallélisme multiprocessing sur les feuilles ; budget (temps, profondeur,
  feuilles) avec verdict UNDECIDED propre.
- Sortie : S1 et S2-planaire certifiées via le nouveau moteur ; test resume
  (kill -9 en cours de run, reprise, même certificat) ; speedup parallèle ≥ 3×
  sur 8 cœurs.

### S4 — Certificat + vérificateur exact (certificate.py, verify.py)
- Entrée : S3 vert.
- Tâches : format JSON SPEC §4 (rationnels exacts, arrondi vers l'intérieur avec
  re-résolution si la marge ne couvre pas) ; verify.py from scratch en Fraction,
  FK symbolique indépendante ; CLI `cnp verify`.
- Sortie : round-trip generate→verify OK sur toutes les scènes existantes ;
  test de mutation : 20 certificats corrompus aléatoirement (coeff, coupe,
  paire) ⟹ 20 rejets ; règle 4 respectée (audit imports).

### S5 — Pipeline φ (phifit.py)
- Entrée : S4 vert.
- Tâches : échantillonnage C_free/C_obs (collision checker Drake, seedé) ; fit
  SVM (sklearn) + approximation polynomiale deg ≤2/var ; sélection δ
  automatique (quantiles de marge + condition (i)) ; boucle de retry (si
  UNDECIDED : re-fit avec pénalité sur les cellules en échec).
- Sortie : E4-planaire reproduit via le pipeline complet ; sur S2 (3-DOF) :
  φ trouvé automatiquement et certifié sans hint manuel.

### S6 — Scènes et CLI (scenes.py + S1/S2 YAML)
- Entrée : S5 vert.
- Tâches : parser YAML SPEC §6 ; scènes S1 (régression) et S2 (peigne 3-DOF)
  finalisées ; CLI `cnp certify <scene>` bout-en-bout ; suite adversariale
  initiale (obstacles rétrécis, micro-canal inséré).
- Sortie : **G1'** — S2 certifiée end-to-end + zéro faux certificat sur
  l'adversarial ; demo console propre (verdict, stats, chemin du certificat).

### S7 — Ancrage Li-Dantam (scène S3, 4-DOF)
- Entrée : G1'.
- Tâches : retrouver scènes/code Li-Dantam (web autorisé) ; reproduire la scène
  bookshelf 4-DOF (sinon ré-implémentation documentée depuis les papiers) ;
  harness benchmarks/ ; premier tableau comparatif (leurs temps publiés vs
  nôtres).
- Sortie : **G3'** (peut arriver avant G2', ordre assumé) — S3 certifiée,
  tableau écrit dans benchmarks/results/, écarts commentés honnêtement dans
  JOURNAL.md (y compris si on est plus lents à 4-DOF : le titre se joue à 5+).

### S8 — Performance (back-end HiGHS, profiling)
- Entrée : S7 vert.
- Tâches : back-end LP direct highspy (sans cvxpy) ; exploitation sparsité des
  tenseurs ; dimensions passives par intervalles (lignes (d+1)^k) ; profiling
  (py-spy) ; degré de témoin adaptatif par feuille.
- Sortie : sur S3 : ≥ 10× plus rapide que le back-end cvxpy ; mémoire bornée ;
  aucun changement de verdict sur la suite complète (soundness re-validée).

### S9 — Scène S4 (bac profond, 5-6 DOF)
- Entrée : S8 vert.
- Tâches : iiwa joints verrouillés (7→5 puis 6) ; conception géométrique de la
  scène bac (vérité-terrain par échantillonnage dense AVANT certification —
  leçon du micro-canal) ; tuning heuristiques.
- Sortie : **G2'** — S4 certifiée < 1 h, < 10⁴ feuilles, verify OK. SI ROUGE :
  session(s) supplémentaire(s) sur les mitigations SPEC §9.1 avant S10 — c'est
  le point de pivot du projet, le journaliser comme tel.

### S10 — Flagship 7-DOF (scène S5)
- Entrée : G2'.
- Tâches : scène étagère iiwa complète ; runs longs avec checkpoints ; si φ
  deg ≤2 insuffisant : φ par morceaux (théorème composé, documenter dans SPEC).
- Sortie : **G4'** — certificat 7-DOF vérifié exact. C'est le résultat-titre ;
  archiver certificat + scène + commit en l'état.

### S11 — Visualisation et assets (viz.py)
- Entrée : G4' (ou en parallèle après G2' si S10 traîne).
- Tâches : Meshcat (scène 3D, configs start/goal, animation de la dalle
  projetée) ; figures C-space/partition style make_figure.py généralisé ;
  tables/courbes de benchmark auto-générées.
- Sortie : `cnp viz <cert>` fonctionne ; pack de figures prêt-papier dans
  benchmarks/figures/.

### S12 — Durcissement
- Entrée : S11.
- Tâches : élargir la suite adversariale (fuzzing de scènes à prémisse fausse,
  micro-canaux générés aléatoirement, limites articulaires frôlant ±π →
  doit refuser proprement) ; messages d'erreur ; README honnête (verdicts,
  hypothèses, limites).
- Sortie : CI complète verte ; zéro faux certificat sur ≥ 200 scènes
  adversariales générées.

### S13 — Reproductibilité et buffer
- Entrée : S12.
- Tâches : script de reproduction one-shot (toutes scènes + benchmarks +
  figures) ; gel des versions ; rattrapage du retard éventuel ; revue finale
  JOURNAL → matière à papier (liste des claims soutenus par les artefacts).
- Sortie : `make reproduce` regénère tout sur machine vierge ; tag v1.0.

---

## Estimation honnête

13 sessions nominales + 2-4 de contingence (S9/S10 sont les plus risquées —
explosion de feuilles ou degré de φ). Le calendrier réel est gouverné par le
risque de recherche résiduel (SPEC §9.1), pas par l'effort : si G2' est rouge
après mitigations, on re-scope (résultat-titre à 5-6 DOF, toujours > état de
l'art rigoureux à 4) plutôt que de forcer.
