# Cas d'usage — Étagère pharma : portée 7-DOF certifiée  *(FLAGSHIP candidat S10)*

> **Une preuve de portée, pas un échantillonnage de portée.** Un bras redondant 7 axes ne peut
> PAS atteindre un casier — et la redondance, qui « devrait » aider, n'y change rien. Prouvé en
> arithmétique exacte, recomptable par un tiers.

---

## 1. Secteur & persona (qui paie)

- **Secteur Cambon AI : santé / pharma-logistique** (automatisation d'officine, stockage
  réfrigéré, préparation de commandes hospitalières).
- **Qui paie** : l'intégrateur de cellule robotisée pharma (et son client exploitant) qui doit
  **garantir une enveloppe de portée** — quels casiers sont atteignables, lesquels ne le sont
  jamais depuis une position de base donnée — pour dimensionner la cellule (nombre de bases,
  placement des étagères) **sans sur-tester sur le terrain**.

## 2. Le récit (scène — apparence FAISABLE, A20)

Un bras de classe iiwa (7-DOF, **redondant**) range des boîtes dans une étagère de stockage.
La cible est un **casier haut**, séparé de la baie « home » par un **panneau plein** (séparateur
de baie / flanc d'étagère). La cible est **proche et visible** : l'œil — et l'intuition métier —
dit *« un bras à 7 axes finit toujours par trouver un chemin »*. C'est exactement l'apparence
faisable qu'on veut (A20) : le certificat n'a d'intérêt que s'il réfute une intuition forte.

## 3. Claim CALIBRÉ — ce que le certificat prouve, et ce qu'il ne prouve PAS

**PROUVE** (à la délivrance par `cnp certify` + recomptage `cnp verify`, S10) :
*dans les limites articulaires affichées* (boîte P : lacet/tangage/coude actifs **±70°**, distaux
**±143°** ⊂ limites usine), **il n'existe aucun chemin continu sans collision** reliant la config
home à la config cible : la barrière (dalle `|φ|≤δ`, φ = lacet de base) est **entièrement en
collision** pour le segment proximal épaule-coude, **et ce indépendamment des 4 joints distaux**.
Preuve **algébrique exacte** (Bernstein-LP, témoin de Putinar, vérifiée en rationnels par un
programme indépendant de <500 lignes).

**NE PROUVE PAS** (lecture honnête, lignée DECISION-G2 §4 « pas de ×400 ») :
- **pas** l'infaisabilité *hors* des limites affichées (wrap-around au-delà de ±180°, autre
  posture de base, déplacement de la base) — **UNDECIDED ≠ infaisable** (SPEC §6) ;
- **pas** un facteur de vitesse vs un concurrent (ni ×400 ni ×N : scènes/objets/matériels
  différents — DECISION-G2 §4) ;
- **pas** une montée en DOF « gratuite » ni un « +N dim » : le coût suit les **dims actives**,
  régime `(d+1)^k` mesuré (S9f) — ici k=3, donc bon marché, mais c'est une **portée bornée** ;
- **pas** la fidélité physique au-delà du modèle géométrique (bac technique iiwa-LIKE, frames
  inter-joints simplifiés — table A21 dans le YAML ; URDF exact à trancher en S11 si exigé).

## 4. Proposition de valeur PROPRE à ce cas

**Une enveloppe de portée *certifiée*, pas *échantillonnée*.** Les outils d'atteignabilité du
marché échantillonnent l'espace de config (nuage de poses IK) : ils disent « je n'ai pas trouvé
de chemin », jamais « il n'en existe pas ». Notre certificat dit **« il n'en existe pas, dans ces
limites, prouvé »** — et l'argument est **robuste à la redondance** : c'est précisément le segment
**proximal** qui est piégé, qu'aucun jeu distal ne libère (leçon S5/S6/S7 : une barrière distale
serait défaite par la redondance ; une barrière proximale, non). Pour un dimensionnement de
cellule, savoir qu'un casier est **prouvé hors-portée** depuis une base évite une base de plus.

## 5. Scène & plausibilité (PAS une certification)

- **Spec chargeable** : [`scenes/S5_iiwa_shelf.yaml`](../../scenes/S5_iiwa_shelf.yaml) *(promu
  FLAGSHIP en S10, depuis `usecase_etagere_pharma.yaml`)* — 7-DOF (`spatial_revolute`), **tous
  joints débloqués**, corps certifié = **link 2** (épaule-coude), obstacle `SHELF_PANEL` en H-rep
  exacte. `python -m cnp show … --interactive` OK (interactif A24 7 curseurs).
- **Piégeage proximal explicite** : link 2 dépend des seuls joints **{0,1,2}** (3 **dims actives**
  détectées par `pair_views`) ; j3,j4,j5,j6 **prouvés passifs** pour la paire (en aval du link 2).
- **Vérité-terrain dense** (S10, `python scripts/flagship_groundtruth.py`, seedé, densité de
  certification) : start/goal **libres** ; **0 libre dans la dalle** sur 120 000 **uniformes** ET
  **0 sur les 448 coins** (2^6 extrêmes des joints non-barrière × niveaux de s0 dans la bande,
  leçon S9f) ; **invariance à la redondance** (les 2^4=16 extrêmes distaux ⟹ tous en collision) ;
  **libre des deux côtés**. ⟹ **déconnexion candidate plausible**. *La preuve est `cnp verify`.*

## 6. Storyboard des artefacts (construits en S10)

- **[A24, artefact PRINCIPAL] interactif HTML auto-suffisant** `cnp show … --interactive` :
  curseurs des 7 joints (butées = limites, **degrés affichés**, A25) ; collision visuelle en
  temps réel ; **fantômes home/cible étiquetés sur toutes les vues** ; **boutons d'évasion**
  rejouant les tentatives naturelles (monter le coude, rouler le poignet, plier l'avant-bras) —
  chacune se solde par un verdict « bloqué », **y compris en exploitant la redondance**.
- **[A20, NON NÉGOCIABLE] vue sweep** : éventail de poses home→cible montrant le bras *semblant
  presque passer* (cible proche/visible), les poses en collision en rouge — pourquoi on croirait
  que ça passe.
- **Figures V6 (S10)** :
  [`benchmarks/figures/S10_flagship/S5_iiwa_shelf_cspace.png`](../../benchmarks/figures/S10_flagship/S5_iiwa_shelf_cspace.png)
  (coupe lacet base × tangage épaule, dalle en or, mur séparant home/cible, évasion plongeant,
  **encadré limites en degrés** A25) et
  [`…_sweep.png`](../../benchmarks/figures/S10_flagship/S5_iiwa_shelf_sweep.png) (A20 : le bras
  atteint tout autour, les poses vers la cible traversent le panneau en ROUGE).
- **[A25] limites partout** : encadré figure, cadre C-space = boîte P, butées curseurs = limites,
  verdict CLI rappelant ses hypothèses (degrés, pas de wrap-around, géométrie exacte).

## 7. Critères d'acceptation (ce que S10 doit livrer pour « démontrer » le cas)

1. `cnp certify scenes/S5_iiwa_shelf.yaml` → **PROOF** ; `cnp verify` → **OK** (exact).
2. Budget **présenté AVANT le run** (feuilles, temps, RAM) ; ici attendu ~8 feuilles / secondes
   (3 dims actives, `(d+1)^3`) — sous la frontière LP S9f, à confirmer par la mesure.
3. Compteur de dissonance **A32 = 0** ; vérité-terrain dense seedée ré-assertée (règle 9).
4. **[V6]** Validation visuelle Stéphane sur l'interactif A24 : (0) **apparence faisable** (A20) ;
   (1) étagère + panneau conformes au scénario « casier haut inatteignable » ; (2) home/cible sans
   collision visuelle ; (3) budget acceptable. « VALIDÉ S10-V6 » = autorisation du run flagship.
5. Si φ deg ≤ 2 insuffisant : φ par morceaux (théorème composé, amender SPEC) — non attendu ici.
