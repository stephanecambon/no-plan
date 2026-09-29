# Audit de publication — S15 (29/09/2026)

Repo audité : `github.com/stephanecambon/no-plan` (privé au 29/09), racine `no-plan/`, branche unique
`main` (+ `origin/main`), 83 commits au premier scan, 87 au re-scan de clôture (§5). Audit en **lecture seule** : aucun fichier
supprimé, aucun historique réécrit (règle 9, D77).

## 0. En tête — secrets

**Aucun secret trouvé, ni dans HEAD ni dans l'historique.**

- `gitleaks 8.30.1`, `gitleaks git --log-opts="--all"` : 83 commits (tous ceux présents au moment du
  scan, toutes branches), ~2,7 Mo de diffs : **0 trouvaille**. Les deux commits S15 postérieurs
  (dépôt papier, ouverture DOC) ne touchent que du LaTeX et du Markdown ; re-scan de clôture : voir §5.
- L'archive `certified-noplan-S0.zip` (non décompressée par gitleaks en mode git) a été extraite et
  scannée à part (`gitleaks dir`) : **0 trouvaille**.
- Contrôle manuel : aucun `.env`, clé, jeton, mot de passe, fichier de configuration de service.

⟹ **Rien à révoquer. Aucune purge n'est nécessaire pour cause de secret.**

## 1. Inventaire

### 1a. Racine `no-plan/` (fichiers suivis : 219 à l'ouverture, 258 en fin de S15 — ajouts S15 : 3 runs de reproduce, fichiers de publication, PDF, archive arXiv)

| chemin | nb | nature |
|---|---|---|
| `certified-noplan-S0.zip` | 1 | archive d'entrée de S0 (16 fichiers : SPEC, CLAUDE, PROMPT-DEMARRAGE, sandbox, note de reprise) — doublon de l'historique |
| `certified-noplan/` (racine) | 8 | `CLAUDE.md`, `JOURNAL.md`, `SPEC.md`, `DECISION-G2.md`, `PROMPT-DEMARRAGE.md`, `Makefile`, `pyproject.toml`, `.gitignore` |
| `certified-noplan/src/cnp/` | 12 | code (dont `verify.py`, 499 lignes) |
| `certified-noplan/tests/` | 34 | suite de tests (dont adversariale) |
| `certified-noplan/scenes/` (+ `wall/`) | 20 + 11 | scènes YAML + certificats |
| `certified-noplan/scripts/` | 27 | scripts de construction, bancs, figures ; chaîne et coque iiwa7 gelées (JSON) |
| `certified-noplan/benchmarks/` | 4 + 42 + 35 | harnais, 2 notes de comparaison, figures (dont `paper/`, `share/`), résultats datés (16 runs) |
| `certified-noplan/docs/` | 3 + 7 + 5 + 4 | notes de départ, fact-checks et brouillons du papier, LaTeX, `usecases/` |
| `certified-noplan/sandbox_reference/` | 6 | scripts d'expérience d'origine (portés en tests de régression) + une figure |

Non suivis mais présents sur disque : `no-plan/.DS_Store` et `.claude/` (vide) — ignorés
(`~/.gitignore_global`, `.gitignore:6`), **jamais commités** (vérifié sur tout l'historique).

Fichiers ayant existé seulement dans l'historique (supprimés ou renommés) : `docs/papers/*` (5 fichiers,
renommés en `docs/paper/`, identiques octet pour octet), `scenes/usecase_etagere_pharma.yaml`,
`benchmarks/figures/S9b_usecases/usecase_etagere_pharma_cspace.png` — techniques, sans enjeu.

### 1b. 20 plus gros objets de l'historique

`.git` = 15 Mo au total (981 objets). Aucun binaire volumineux : le plus gros objet fait 0,9 Mo.

| taille | chemin |
|---|---|
| 919 409 | `benchmarks/figures/paper/fig1.png` (version S14) |
| 873 037 | `benchmarks/figures/paper/fig1.png` (version antérieure) |
| 849 713 | `benchmarks/figures/paper/fig1.png` (version antérieure) |
| 304 668 … 212 344 | `JOURNAL.md` (16 versions successives) |
| 279 143 | `benchmarks/figures/paper/partition_E3.png` |

### 1c. Données personnelles

| trouvaille | où | gravité |
|---|---|---|
| Email `scambon@gmail.com` en auteur/committer de tous les commits (87) | métadonnées git | BASSE — inévitable sans réécriture ; absent du **contenu** des fichiers (vérifié sur tout l'historique) |
| Détails de la machine personnelle (applications de bureau nommées) | `JOURNAL.md` (entrée S14, « Ouverture [A33] ») | **HAUTE** — vie privée, sans valeur scientifique |
| Liste des processus les plus actifs, avec chemins locaux (nom d'utilisateur) et applications de bureau ouvertes | `busiest_processes_at_start` des trois `reproduce.json` (`20260910T152348Z`, `20260929T160611Z`, `20260929T163849Z`) ; produite par `benchmarks/run_benchmark.py` (`_busiest_processes`) | MOYENNE — révèle nom d'utilisateur et applications ouvertes ; la charge (`load_avg`) suffit à l'argument « machine quiète » |
| « MacBook (Apple Silicon) », « Apple M4, 24 Go » | papier §7, `reproduce.json` | BASSE — utile à la reproductibilité |
| Téléphone, adresse postale, nom d'hôte | — | aucun trouvé |

### 1d. Tiers nommés hors références bibliographiques

| trouvaille | où | gravité |
|---|---|---|
| Parcours personnel d'un chercheur tiers ; passage sur la compétition entre groupes | `docs/infaisabilite-certifiee-barrieres-SOS-NOTE-DE-REPRISE.md` l.23, l.103-106 | **HAUTE** |
| Passage présentant un groupe de recherche nommé comme concurrent | `JOURNAL.md` (revue P2, complément biblio) | **HAUTE** — présente un groupe de recherche nommé comme concurrent à devancer |
| Plans de prise de contact avec des chercheurs nommés | `CLAUDE.md` section S14, `JOURNAL.md` (S14, revue S14) | MOYENNE |
| Spéculation sur l'identité d'un relecteur | `DECISION-G2.md` l.135-136 | MOYENNE |

### 1e. Contenu interne, brouillons, bac à sable

| fichier | nature | gravité |
|---|---|---|
| `certified-noplan-S0.zip` | archive d'entrée S0, doublon de l'historique | MOYENNE |
| `PROMPT-DEMARRAGE.md` | consignes d'installation + prompt de démarrage de S0 | BASSE (fait partie du récit de provenance) |
| `docs/infaisabilite-certifiee-barrieres-SOS-NOTE-DE-REPRISE.md` | note de reprise antérieure au projet (état de l'art, plan, risques de compétition, « recruter un collaborateur ») ; contient une affirmation d'état de l'art déclarée périmée par le projet lui-même (A26) | **HAUTE** (voir 1d) |
| `docs/paper/PAPER-SKELETON.md`, `PAPER-DRAFT.md`, `FACTCHECK-*.md`, `BIB-VERIFY-S14.md` | brouillons et fact-checks du papier | BASSE — c'est la preuve du « every statement was confirmed against the source code » du §9 |
| `JOURNAL.md`, `CLAUDE.md` (22 revues de supervision IA, ton interne) | journal et règles de l'agent | BASSE sur le fond (c'est l'argument de transparence), sauf les points HAUTE/MOYENNE listés |
| `sandbox_reference/`, `docs/CAMPAGNE-E1-E4-RESULTATS.md` | expériences d'origine | BASSE |

Placeholders visibles : **aucun** dans `paper.tex`, `paper.bbl`, `refs.bib` (pas de TODO, [VERIFY],
[email], draft hors la phrase légitime du §9, commentaire). `JOURNAL.md` contient « [auteurs à vérifier] »
(revue P2, résolu depuis dans la bib) — interne, BASSE.

## 2. Candidats au retrait — décision G1

Deux modes : **HEAD seul** (commit de retrait ; le contenu reste lisible dans l'historique public) ou
**purge** (`git filter-repo` ⟹ nouveaux hashes de TOUS les commits ⟹ force-push ; les hashes cités
dans `JOURNAL.md`, les `reproduce.json` et les certificats (`commit`) deviennent orphelins — coût réel
pour l'argument de provenance).

| # | candidat | recommandation Code | alternative |
|---|---|---|---|
| R1 | `docs/usecases/` (4 one-pagers : « Secteur & persona (qui paie) », « Secteur Cambon AI » ; `PORTFOLIO.md` : « monétisable », « se vend en une phrase à un intégrateur », « matière commerciale Cambon AI ») — aucun client, prospect ni tarif nommé | HEAD seul, ou garder (le contenu technique « PROUVE / NE PROUVE PAS » est honnête) | purge |
| R2 | Détails machine perso dans `JOURNAL.md` (S14) | **purge** si l'on purge quoi que ce soit ; sinon rédaction en HEAD (« applications de bureau fermées ») | HEAD seul |
| R3 | `busiest_processes*` dans les `reproduce.json` + `_busiest_processes` du harnais | ne garder que `load_avg` : retirer la clé du harnais et des deux JSON (les **valeurs mesurées** ne changent pas ; règle 7 : on annote, on n'écrase pas une mesure) | garder |
| R4 | `NOTE-DE-REPRISE.md` (tiers nommés, compétition) | HEAD seul ou purge | garder |
| R5 | groupe nommé comme concurrent (JOURNAL, revue P2) + plans de contact (CLAUDE/JOURNAL) + spéculation sur un relecteur (DECISION-G2, JOURNAL revue DECISION-G2) | rédaction en HEAD (on annote, on ne réécrit pas le journal : « [passage retiré avant publication, S15] ») | purge |
| R6 | `certified-noplan-S0.zip` | HEAD seul (doublon) | garder |
| R7 | « prospect » dans deux docstrings (`scripts/export_flagship_3d_html.py:3`, `tests/test_share_3d_html.py:3`) | remplacer par « lecteur » en HEAD | garder |

Tous ces passages sont **dans l'historique** : un retrait HEAD seul ne les rend pas illisibles. Le
contenu R2/R4/R5 est le seul qui plaide pour une purge ; aucun n'est un secret.

## 2 bis. Décisions G1 (Stéphane, 29/09/2026) — appliquées en HEAD, **aucune purge**

« ok reco, applique tout » : licence **MIT** ; **aucune purge d'historique** (les passages restent lisibles dans
l'historique git) ; repo rendu public par Stéphane, **sans soumission arXiv pour l'instant** (release, Zenodo et
ORCID optionnels).
- R1 **gardé** (contenu technique honnête, aucun client ni tarif).
- R2, R5 **annotés en HEAD** : passage remplacé par « [retiré avant publication — S15, décision G1 de Stéphane] »
  dans `JOURNAL.md` (4 passages), `CLAUDE.md` (1), `DECISION-G2.md` (1, corps signé annoté, pas réécrit au-delà).
  Les descriptions de ce rapport sont elles-mêmes caviardées (plus de citation).
- R3 **retiré** : `_busiest_processes` supprimé du harnais ; clé remplacée dans les trois `reproduce.json` par
  `busiest_processes_at_start_redacted` (note) — aucune valeur mesurée modifiée, diff de 7 lignes par fichier.
- R4, R6 **retirés de HEAD** (`git rm`).
- R7 : « prospect » → « lecteur ».
- Corrections du papier P1-P9 **appliquées** ; **versions figées** (`requirements-lock.txt`, `make setup LOCK=1`).

## 3. Ce que l'historique prouve (§9 du papier)

`JOURNAL.md` et l'historique git documentent, datés, du 10/06 au 29/09/2026 : 19 entrées de session de
l'agent de code, 22 revues de supervision IA transcrites (circuit A16), 4 décisions de pilotage, les
validations visuelles humaines au format de la règle 11 (« VALIDÉ S3-V1 », S5-V2, S7-V4, S9-V5, S10-V6,
V6-bis et la validation VUE de S11), la signature de Stéphane sur `DECISION-G2.md` (13/06, §6), et
87 commits d'auteur Stéphane Cambon dont 81 portent la ligne `Co-Authored-By: Claude`.

Cohérence avec le §9 :
- « implementation by an autonomous coding agent working in sessions from a written specification,
  supervised and reviewed by a second AI system » : **cohérent** (SPEC.md, CLAUDE.md, 19 sessions, 22 revues).
- « every gate, every scene validation … and the go/no-go decision signed by the human author » :
  **cohérent** (gates V1-V6-bis, G1-G4', DECISION-G2 signée).
- « every design decision … signed by the human author » : **plus fort que ce que l'historique
  montre.** Beaucoup de décisions techniques sont prises par l'agent « dans le mandat » (rubrique
  « Décisions (Code) » de chaque session) puis endossées par la revue IA, sans signature humaine
  individuelle ; les décisions de pilotage et de portée sont, elles, de Stéphane. Proposition (non
  appliquée, hors périmètre 3a-3f) : « every gate, every scene validation, every scoping decision and
  the go/no-go decision signed by the human author; technical decisions were taken within a written
  mandate and reviewed ». Même remarque pour l'introduction (« every gate, scene validation and design
  decision carries a human signature »).
- Un trou de circuit est visible et dit : la revue S12 (09/09) n'a été transcrite que le 29/09.

## 4. Corrections du papier PROPOSÉES (non appliquées — hors périmètre 3a-3f)

| # | où | constat | proposition |
|---|---|---|---|
| P1 | §1 l.« A note on provenance », §9 « Provenance » | « every … design decision … signed by the human author » plus fort que l'historique (voir §3) | « every gate, scene validation, scoping decision and the go/no-go decision signed by the human author; technical decisions taken within a written mandate and reviewed » |
| P2 | §9, objection « Why not rationalize an SOS certificate? » | « on all seven scenes here » : la table a 7 scènes + la famille du mur (12 certificats). Vérifié sur les artefacts : dans les 13 certificats du dépôt, seul le λ du dernier sommet (fixé par soustraction) dépasse le dénominateur 10⁶, μ ≤ 10⁶ partout ⟹ le premier palier a suffi partout | « on all twelve certificates of Table 2 » |
| P3 | §9, même objection | « (\S2) » codé en dur | \label sur Related Work + \S\ref |
| P4 | éq. (LP), l.~129 | Overfull hbox 11,7 pt (déborde de la colonne) | couper la contrainte sur deux lignes |
| P5 | titre §6.2 « … cost $(d+1)^k$ » | 3 avertissements hyperref (maths dans les signets PDF) | \texorpdfstring |
| P6 | préambule | PDF sans métadonnées titre/auteur | \hypersetup{pdftitle=…, pdfauthor=Stéphane Cambon} |
| P7 | §8 « Time » | « a second, cache-warm pass at export costs about 1 s » : chrono absent de reproduce.json (source S12) | le sourcer comme historique ou le retirer |
| P8 | §7 intro | « MacBook (Apple Silicon) » | préciser « Apple M4, 10 cores, 24 GB » (lu dans reproduce.json) |
| P9 | Fig. 3 (coût) | le segment pointillé k=7→k=8 n'est pas décrit | « dotted: the k=8 row count, from the LP-size formula checked on every certified row » |

Le papier ne contient aucun placeholder ni commentaire ; abstract = 1 673 caractères en texte brut
(`docs/paper/arxiv-abstract.txt`, < 1 920).

## 5. Re-scan de clôture (29/09, avant G1)

`gitleaks git --log-opts="--all"` : 87 commits, ~2,9 Mo : **0 trouvaille**. `gitleaks dir .` (arbre de
travail, fichiers non suivis compris) : **0 trouvaille**.

## 6. Test depuis un clone frais (tâche 2)

`git clone /Users/scambon/Code/no-plan /tmp/noplan-clone` (commit `bec5a83`) :
1. `verify_file` sous `python -S -I` sur les **13** certificats de `scenes/` et `scenes/wall/` (dont l'iiwa-LIKE
   `S5_iiwa_shelf`) : **13/13 PROOF**, sous Python 3.9.6 (système macOS) et 3.12.13 ; modules hors stdlib
   chargés : `cnp` seul (`sys.stdlib_module_names`). Flagship : 1,9 s (3.12), 10,7 s (3.9).
2. Commandes du README telles qu'écrites : le one-liner donne exactement la sortie annoncée ; `make setup` OK ;
   `make test` **240 passed, 1 deselected** ; `cnp verify <cert> <scene>` PROOF + recoupement de scène, rc 0 ;
   `make reproduce` sur arbre propre (27 min 13 s) **12 PROOF + k=8 UNDECIDED**, **certificats identiques octet pour
   octet** ; `make paper-figures` OK.
3. Constat : `pyproject.toml` ne fixe que des bornes inférieures ⟹ le clone a installé matplotlib 3.11.2, numpy 2.5.3,
   scipy 1.18.1, highspy 1.15.1 (dépôt : 3.10.9 / 2.4.6 / 1.17.1 / 1.14.0). **Les certificats n'ont pas bougé** ; les
   figures diffèrent au pixel (rendu matplotlib, contenu identique à l'œil). Le README le dit. Gel des versions (reste
   de l'ex-S14, non re-planifié) : question G1.
   Correction du README après le test : `cnp` → `.venv/bin/cnp` (pas d'activation du venv dans les instructions).
