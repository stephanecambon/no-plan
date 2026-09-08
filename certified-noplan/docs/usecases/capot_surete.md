# Cas d'usage — Capot de sûreté · fenêtre opérateur : certificat EXACT recomptable

> **L'auditeur RECOMPTE, il ne fait pas confiance au pipeline.** Une pièce algébrique versable au
> dossier de sûreté, re-vérifiable en arithmétique exacte par un tiers — pas un « croyez notre
> collision-checker flottant ».

> **✅ CERTIFIÉ (S11, 8 septembre 2026) sur le VRAI KUKA iiwa7.** `PROOF` + `cnp verify` **OK en
> arithmétique exacte** + cross-check de scène, **A32 = 0**. Scène
> [`scenes/usecase_capot_surete_iiwa7.yaml`](../../scenes/usecase_capot_surete_iiwa7.yaml),
> certificat [`scenes/usecase_capot_surete_iiwa7.cert.json`](../../scenes/usecase_capot_surete_iiwa7.cert.json).
> **Montée en gamme** par rapport à la spec S9b : robot générique à corps-SEGMENT → **vrai iiwa7**,
> cinématique fidèle à l'URDF ~2e-6 et **silhouette convexe fidèle du lien 3** (40 sommets, ~1,7e-6).
>
> ⚠️ **Ce document décrit une PIÈCE GÉOMÉTRIQUE re-vérifiable, PAS une certification ISO.** Voir
> §3 pour le claim calibré : ce que le certificat prouve, et — au moins aussi important dans un
> contexte réglementaire — ce qu'il ne prouve pas.

---

## 1. Secteur & persona (qui paie)

- **Secteur Cambon AI : sûreté / réglementaire** (sûreté fonctionnelle des cellules robotisées,
  ISO 10218 / ISO/TS 15066 / EN ISO 13849, analyses de risque, marquage CE).
- **Qui paie** : le **responsable sûreté** de l'intégrateur (et l'**organisme notifié** qui audite
  le dossier). Leur problème : justifier qu'une zone est **inatteignable par le bras** sans
  s'en remettre à la parole d'un pipeline de simulation non re-vérifiable.

## 2. Le récit (scène — apparence FAISABLE, A20)

Une cellule 7 axes (KUKA iiwa7) travaille sous un **capot de sûreté horizontal** (guard panel).
La **zone opérateur** est de l'autre côté du capot, **visible et proche** ; l'espace latéral a
l'air dégagé — l'intuition dit *« il passera par-dessus, ou il contournera »* (apparence faisable,
A20). Question d'analyse de risque : *« le bras peut-il, depuis sa zone home, basculer vers la zone
opérateur ? »*

Le certificat prouve que **non**, et dit **pourquoi** : pour basculer d'un côté à l'autre, le
tangage d'épaule `q2` doit **changer de signe**, donc passer par `q2 ≈ 0` — le bras se **redresse**,
et c'est là que le **segment proximal** (lien 3) percute le plan du capot. Contourner par le lacet
de base ne change rien (le corps proximal tourne sur lui-même sans se déplacer — **mesuré**, cf.
§5), et les **4 joints distaux sont prouvés passifs** : ils sont en aval du corps piégé.

## 3. Claim CALIBRÉ — ce que le certificat prouve, et ce qu'il ne prouve PAS

**PROUVE**, et rien de plus : *dans les limites articulaires affichées* (actifs **±66°**, distaux
**±143°**, toutes ⊂ limites usine iiwa7 et ⊂ (−180°, 180°) donc **sans wrap-around**), et pour la
**géométrie statique modélisée** (obstacle en H-rep exacte, corps = **polytope convexe**, géométrie
en **rationnels exacts**), **aucun chemin continu sans collision** ne relie la pose home à la pose
côté opérateur : la dalle `|φ| ≤ 9/50` est **entièrement en collision** entre le corps proximal
certifié (lien 3, silhouette convexe fidèle) et le capot, **indépendamment des 4 joints distaux**.
Les deux poses sont dans **deux composantes libres distinctes** de l'espace des configurations.

Preuve **algébrique exacte**, **re-vérifiée en arithmétique rationnelle par un programme
indépendant** (`cnp verify`, < 500 lignes, `fractions.Fraction` seulement, stdlib seule, **aucun
import du générateur** — il ré-implémente la cinématique et les bornes de Bernstein depuis zéro).
C'est ce programme, pas le nôtre, que l'organisme notifié peut relancer.

**NE PROUVE PAS** — à lire avant tout usage dans un dossier :
- **pas une certification ISO, ni une garantie de sûreté SYSTÈME.** C'est une **pièce géométrique**
  versable, à intégrer dans une analyse de risque **par une personne compétente**. Elle ne se
  substitue à aucune exigence de l'ISO 10218 / ISO 12100 / ISO/TS 15066 / EN ISO 13849 ;
- **rien de DYNAMIQUE** : ni vitesses, ni distances d'arrêt, ni temps de réaction, ni défaillance
  de capteur ou d'actionneur, ni comportement en mode dégradé, ni intrusion humaine ;
- **rien HORS des limites articulaires affichées** ni hors de la géométrie modélisée : un autre
  outil en bout de bras, un déplacement de la base, un desserrage de butée logicielle, un jeu
  mécanique ou une déformation **invalident le claim**. Le certificat est indexé sur SES prémisses,
  qui sont écrites dans le fichier ;
- **rien sur les obstacles MOBILES** : les obstacles sont supposés **statiques** ;
- **UNDECIDED ≠ inatteignable** (SPEC §6) : l'absence de certificat n'est pas une preuve
  d'atteignabilité, et réciproquement ;
- **pas** un facteur de performance vs un autre outil (pas de ×N) ;
- **pas** une montée en dims actives gratuite (régime `(d+1)^k`, S9f ; ici k=3) ;
- **pas « le iiwa exact »** : la fidélité au robot PHYSIQUE est plafonnée par la précision de
  l'URDF publié (~2e-6 mesuré, A41). Le **modèle interne** est exact — `verify` recompte en
  `Fraction` — mais il certifie *le modèle*, et la correspondance modèle↔réalité reste une
  hypothèse d'ingénierie à assumer explicitement dans le dossier.

## 4. Proposition de valeur PROPRE à ce cas

**La NATURE du certificat, pas sa vitesse** (différenciateur A26/DECISION-G2 §4). Les pipelines de
vérification d'atteignabilité du marché s'appuient sur un **collision-checker flottant** : non
recomptable, l'auditeur doit **faire confiance** au pipeline. Notre certificat est **algébrique et
exactement re-vérifiable** : l'organisme notifié relance `cnp verify` (arithmétique rationnelle,
indépendant du générateur) et **recompte la preuve lui-même**. Pour un dossier de sûreté, c'est la
différence entre *« le fournisseur affirme »* et *« j'ai re-vérifié »*. C'est aussi le seul des
trois cas où la **recomptabilité** est la valeur centrale (vs un argument de portée ou d'élagage).

## 5. Scène, mesures et certificat

- **Scène** : [`scenes/usecase_capot_surete_iiwa7.yaml`](../../scenes/usecase_capot_surete_iiwa7.yaml)
  — vrai iiwa7 7 axes (chaîne gelée), corps certifié = **lien 3** (coque convexe fidèle 40
  sommets), obstacle `GUARD_PANEL` : capot **horizontal mince** (50 mm) et **large** (±0,60 m),
  dessous à **z = 0,695 m**, en **H-rep exacte** (étanche par construction). L'espace latéral et
  le dessous du capot sont **libres** — c'est ce qui rend la scène feasible-looking (A20).
- **Piégeage proximal RE-MESURÉ** (`engine.pair_views`, jamais présumé) : dims actives
  **{0,1,2}** ; **j4…j7 prouvés passifs** pour la paire.
- **Pourquoi ce séparateur, et pourquoi contourner ne marche pas** :
  `scripts/measure_iiwa7_lever.py` a mesuré le levier **avant** d'écrire la scène — 3 axes actifs
  × 6 directions × 2 motifs d'obstacle. Sur le vrai lien 3, **seul** « tangage `q2` + obstacle en
  surplomb » est franc (**+174,8 mm**) ; le **lacet de base est négatif dans les 6 directions**
  (le corps proximal tourne sur lui-même sans se déplacer) et le roulis `q3` aussi. Autrement
  dit : la mesure elle-même établit que les manœuvres de contournement « naturelles » n'ont pas
  de levier sur ce corps. (Finding A43, quantifié.)
- **Marge FRANCHE mesurée** (obstacle posé au MILIEU de la fenêtre franche) : **+83,1 mm** de
  pénétration dans la dalle / **+85,3 mm** de dégagement aux poses. On refuse le marginal : une
  séparation de ~6 mm avait été rejetée en S10-ter.
- **Vérité-terrain dense** (oracle **corps-convexe**, seedée, INDÉPENDANTE du certificat — elle
  ne lit ni λ ni μ) : start/goal **libres** ; **0 libre dans la dalle** sur 40 000 uniformes ET
  **0 sur 448 coins** ; **invariance de redondance** (les 2⁴ extrêmes distaux : tous en
  collision) ; **libre des deux côtés**.
- **Certificat** : **PROOF**, **4 feuilles** (2 collision + 2 hors-dalle), **A32 = 0** ;
  `cnp verify` **OK exact** en **2,54 s** ; `certify` **498 s** (budget prédit A44 avant le run :
  ~620 s ⟹ écart **−20 %**). LP de feuille **1 070 lignes** (réduit) contre **473 870** en pleine
  dimension : **×442,9**. Bench daté : `benchmarks/results/20260908T151019Z/`.

### Comment un tiers RECOMPTE (la valeur de ce cas, rendue opérationnelle)

```bash
python -m cnp verify scenes/usecase_capot_surete_iiwa7.cert.json scenes/usecase_capot_surete_iiwa7.yaml
```

Le second argument **croise le certificat avec le fichier de scène** : il ne suffit pas que la
preuve soit correcte, il faut qu'elle porte sur **le problème que le dossier décrit**. La commande
imprime le verdict **et rappelle ses hypothèses** (limites en degrés, absence de wrap-around,
obstacles statiques, corps = polytopes, géométrie rationnelle exacte). `verify.py` fait moins de
500 lignes, n'utilise que la bibliothèque standard, et **n'importe rien du générateur** :
l'auditeur peut le lire en entier.

## 6. Artefacts livrés (pack démo S11)

- **[A24] interactif HTML auto-suffisant** :
  [`usecase_capot_surete_iiwa7_interactive.html`](../../benchmarks/figures/S11_usecases/usecase_capot_surete_iiwa7_interactive.html)
  — 7 curseurs (butées = limites, en degrés, A25), corps = **coque 40 sommets** avec collision
  **GJK** reproduisant l'oracle, fantômes home / zone-opérateur, boutons d'évasion → « bloqué ».
- **3D partageable** (un fichier, sans Python, sans serveur) :
  [`usecase_capot_surete_iiwa7_3d.html`](../../benchmarks/figures/share/usecase_capot_surete_iiwa7_3d.html)
  — 7 curseurs articulaires, collision recalculée en direct, fantômes de bras entier, tentatives
  d'évasion, corps certifié surligné + légende A40 (« seule la coque surlignée est dans la paire
  certifiée »). Cinématique et collision = le **noyau JS partagé** testé sous node contre l'oracle
  Python (`tests/test_share_3d_html.py`, 0 écart).
- **[A20] sweep** + **C-space** + **partition slab-aware** :
  `benchmarks/figures/S11_usecases/usecase_capot_surete_iiwa7_{sweep,cspace,partition}.png`.
  La **partition** est celle qui parle à un auditeur : le plein rouge est **ce que le théorème
  prouve** (feuille ∩ dalle), le hachuré est la zone **où il ne dit rien** (A11).
- **[A25] limites partout** + rappel des hypothèses par le verdict CLI.

## 7. Critères d'acceptation — état

| # | Critère | État |
|---|---|---|
| 1 | `cnp certify` → PROOF ; `cnp verify` → OK exact, **relançable par un tiers** | ✅ + cross-check de scène (commande ci-dessus) |
| 2 | Budget présenté AVANT le run | ✅ prédit ~620 s (A44), mesuré 498 s |
| 3 | A32 = 0 ; vérité-terrain dense seedée ré-assertée | ✅ |
| 4 | Encadré « hypothèses du certificat » explicite | ✅ verdict CLI + encadré A25 sur chaque figure |
| 5 | Cadrage honnête : pièce géométrique, **PAS** une certification ISO | ✅ bandeau d'en-tête + §3 « NE PROUVE PAS » développé |
| 6 | Marge FRANCHE (≥ ~40 mm) | ✅ +83,1 / +85,3 mm |
