# BIBLIO-ANTERIORITE.md — Revue d'antériorité et bibliographie du papier

Statut : revue de littérature (risque n°6 SPEC §9) — tâche humaine + supervision,
réalisée le 12 juin 2026 (claude.ai, ~10 recherches + lectures ciblées).
Convention : chaque entrée BibTeX porte un champ `note` (rôle dans le papier).
Les champs marqués **[à vérifier]** doivent être confirmés avant soumission.

---

## 0. SYNTHÈSE D'ANTÉRIORITÉ (le résultat de la revue)

**Question posée** : quelqu'un a-t-il déjà produit des certificats ALGÉBRIQUES
d'infaisabilité de motion planning, EXACTEMENT vérifiables par un programme
indépendant ?

**Réponse : non — mais quatre voisins imposent une formulation précise du claim.**

| Voisin | Ce qu'ils certifient | Vérification a posteriori | Portée démontrée | Notre delta |
|---|---|---|---|---|
| **Henrion, Miller & Safey El Din 2024** (le plus proche, découvert par cette revue) | Déconnexion par chemins de X0/X1 dans X, barrière dépendante du temps, nécessaire ET suffisante (compacité) | Polynôme v à coefficients FLOTTANTS issu d'un SDP Mosek ; re-vérifier = re-résoudre un SDP (pas exact) | Ensembles semi-algébriques abstraits, n ≤ 3, intégrateur simple, horizon T à borner (D'Acunto-Kurdyka) | Cinématique de bras articulés (FK rationnelle, paires de collision) ; certificat 100 % rationnel ; vérif = signes de coefficients de Bernstein en Fraction, <500 lignes stdlib ; LP pur ; pas d'horizon temporel ; 4-DOF PROOF exact déjà acquis, 5-6 DOF visés |
| **Li & Dantam 2020-2024** (lignée complète) | Manifold séparateur appris (SVM RBF) + triangulation, validé par collision-checker numérique | Aucune vérification exacte ; confiance dans le pipeline flottant | 4-DOF CPU (RSS21/IJRR23), 5-6 DOF GPU (RA-L23, arXiv 2406.04795) | Nature du certificat : algébrique, exact, revérifiable ; CPU/LP ; murs réutilisables (requêtes µs) |
| **Jaulin 2001 ; Delanoue, Jaulin & Cottenceau 2006** | Conclusion « No path » GARANTIE par sous-pavages d'intervalles (arrondi extérieur) ; connexité prouvée par intervalles | La preuve EST l'exécution de l'algorithme — aucun certificat exportable contrôlable par un tiers (limite reconnue par Henrion et al. eux-mêmes) | C-spaces 2D, ensembles pleine dimension | Certificat autonome exportable ; bras articulés ; n ≥ 4 |
| **Canny 1988 ; Safey El Din & Schost 2017 ; Prébet et al. 2024** | Décision EXACTE de connexité (roadmaps d'algèbre réelle) — complets | Aucun certificat a posteriori dans le cas déconnecté (« the user is expected to trust the algorithm ») ; complexité simplement/doublement exponentielle, impraticable | Théorique | Certificat indépendamment contrôlable ; praticable (LP) ; restriction honnête à un schéma suffisant (dalle) |

**Formulation de claim recommandée (survit à un reviewer)** :

> FR — « Premiers certificats d'infaisabilité de motion planning pour bras
> articulés qui soient *exactement vérifiables a posteriori* par un programme
> indépendant en arithmétique rationnelle. Les certificats algébriques de
> déconnexion existants (Henrion et al. 2024) traitent des ensembles
> semi-algébriques abstraits de petite dimension via une hiérarchie moment-SOS
> numérique ; les preuves d'infaisabilité existantes pour manipulateurs
> (Li & Dantam 2020-2024) reposent sur un manifold appris validé par
> collision-checker flottant ; les méthodes d'intervalles (Jaulin 2001) et
> d'algèbre réelle exacte (Canny 1988) décident sans produire de certificat
> contrôlable par un tiers. »

> EN — "We present the first motion-planning infeasibility certificates for
> articulated robots that are *exactly verifiable a posteriori* by an
> independent program in rational arithmetic. Existing algebraic
> disconnectedness certificates (Henrion et al., 2024) address low-dimensional
> abstract semialgebraic sets via a numerical moment-SOS hierarchy; existing
> manipulator infeasibility proofs (Li & Dantam, 2020-2024) rely on a learned
> manifold validated by floating-point collision checking; interval methods
> (Jaulin, 2001) and exact real algebra (Canny, 1988) decide connectivity
> without producing a third-party-checkable certificate."

**Interdits de claim** (formules qui seraient FAUSSES) :
- « premiers certificats algébriques de déconnexion » → faux (Henrion et al. 2024) ;
- « premières preuves rigoureuses d'infaisabilité » → faux (Jaulin 2001, Zhang 2008
  resolution-complete, Canny 1988) ;
- « les méthodes rigoureuses plafonnent à 4-DOF » → périmé (A26, déjà corrigé).

**Argument technique à expliciter dans le papier** (pourquoi Bernstein-LP rend la
vérification exacte *bon marché*, là où SOS ne le permet pas) : un certificat
Bernstein est une liste de coefficients rationnels dont la non-négativité se
contrôle par INSPECTION DE SIGNES en arithmétique exacte (verify.py, <500 lignes,
Fraction) ; un certificat SOS est une matrice de Gram dont la PSD-ité flottante ne
se re-vérifie exactement qu'au prix d'une rationalisation + factorisation LDL^T
exacte — possible en principe, jamais fait dans les travaux cités. Le choix
LP/Bernstein n'est donc pas (seulement) un choix de coût : c'est ce qui rend le
certificat auditables par un comptable.

---

## 1. INFAISABILITÉ EN MOTION PLANNING (les concurrents directs)

```bibtex
@inproceedings{li2020towards,
  author    = {Li, Sihui and Dantam, Neil T.},
  title     = {Towards General Infeasibility Proofs in Motion Planning},
  booktitle = {IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)},
  year      = {2020},
  note      = {Première formulation du programme de recherche « preuves d'infaisabilité ». Citer en ouverture du related work.}
}

@inproceedings{li2021learning,
  author    = {Li, Sihui and Dantam, Neil T.},
  title     = {Learning Proofs of Motion Planning Infeasibility},
  booktitle = {Robotics: Science and Systems (RSS)},
  year      = {2021},
  doi       = {10.15607/RSS.2021.XVII.064},
  note      = {LA référence 4-DOF (épaule-coude ~231 s CPU, SCARA ~433 s) — notre ancrage S7/S3. Manifold SVM + triangulation, validation par collision-checker.}
}

@inproceedings{li2022exponential,
  author    = {Li, Sihui and Dantam, Neil T.},
  title     = {Exponential Convergence of Infeasibility Proofs for Kinematic Motion Planning},
  booktitle = {Workshop on the Algorithmic Foundations of Robotics (WAFR)},
  year      = {2022},
  doi       = {10.1007/978-3-031-21090-7_18},
  note      = {Leur résultat de convergence. Même volume Springer que C-IRIS (chapitre 18 vs 20) — coïncidence éditoriale utile au récit.}
}

@article{li2023sampling,
  author    = {Li, Sihui and Dantam, Neil T.},
  title     = {A Sampling and Learning Framework to Prove Motion Planning Infeasibility},
  journal   = {The International Journal of Robotics Research},
  volume    = {42},
  number    = {10},
  pages     = {938--956},
  year      = {2023},
  doi       = {10.1177/02783649231154674},
  note      = {Version journal consolidée — la référence canonique à citer pour leur méthode.}
}

@article{li2023scaling_ral,
  author    = {Li, Sihui and Dantam, Neil T.},
  title     = {Scaling Infeasibility Proofs via Concurrent, Codimension-One, Locally-Updated Coxeter Triangulation},
  journal   = {IEEE Robotics and Automation Letters},
  volume    = {8},
  number    = {12},
  pages     = {8303--8310},
  year      = {2023},
  note      = {[à vérifier : titre exact] Triangulation de Coxeter, première extension au-delà de 4-DOF. Chiffres exacts dans benchmarks/COMPARISON-Li-Dantam.md (lus en S8).}
}

@misc{li2024gpu,
  author    = {Li, Sihui and Dantam, Neil T.},
  title     = {Scaling Motion Planning Infeasibility Proofs},
  howpublished = {arXiv:2406.04795},
  year      = {2024},
  note      = {Scaling GPU 5-6 DOF, ~2 ordres de grandeur vs leur méthode antérieure (vérifié S8/D13). LA cible de comparaison de G2' / DECISION-G2.md.}
}

@misc{thomas2025incremental,
  author    = {Thomas, Antony and others},
  title     = {An Incremental Sampling and Segmentation-Based Approach for Motion Planning Infeasibility},
  howpublished = {arXiv:2501.11434},
  year      = {2025},
  note      = {[à vérifier : liste d'auteurs complète, Gênes] Approche bitmap/segmentation, autre groupe — montre que le créneau s'anime. Une phrase au related work.}
}

@misc{roadmapcut2023,
  author    = {[à vérifier]},
  title     = {Motion Planning (In)feasibility Detection using a Prior Roadmap via Path and Cut Search},
  howpublished = {arXiv:2305.10395},
  year      = {2023},
  note      = {[à vérifier : auteurs] Détection d'infaisabilité par recherche de coupe dans un roadmap — heuristique, sans certificat. Une phrase.}
}
```

## 2. NON-EXISTENCE DE CHEMIN « CLASSIQUE » (décomposition cellulaire, complétude)

```bibtex
@inproceedings{zhang2007hybrid,
  author    = {Zhang, Liangjun and Kim, Young J. and Manocha, Dinesh},
  title     = {A Hybrid Approach for Complete Motion Planning},
  booktitle = {IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)},
  pages     = {7--14},
  year      = {2007},
  note      = {ACD + PRM, resolution-complete, non-existence détectée par recherche de graphe. Démo 3-4 DOF.}
}

@incollection{zhang2008simple,
  author    = {Zhang, Liangjun and Kim, Young J. and Manocha, Dinesh},
  title     = {A Simple Path Non-Existence Algorithm Using C-Obstacle Query},
  booktitle = {Algorithmic Foundation of Robotics VII (WAFR 2006)},
  series    = {Springer Tracts in Advanced Robotics},
  volume    = {47},
  pages     = {269--284},
  publisher = {Springer},
  year      = {2008},
  doi       = {10.1007/978-3-540-68405-3_17},
  note      = {Requête C-obstacle pour étiqueter des cellules entièrement en collision — ancêtre conceptuel de notre étiquetage de feuilles, mais numérique et basse dimension.}
}

@article{zhang2008efficient,
  author    = {Zhang, Liangjun and Kim, Young J. and Manocha, Dinesh},
  title     = {Efficient Cell Labelling and Path Non-Existence Computation using C-Obstacle Query},
  journal   = {The International Journal of Robotics Research},
  volume    = {27},
  number    = {11-12},
  pages     = {1246--1257},
  year      = {2008},
  note      = {Version journal de la lignée. La référence à citer.}
}

@inproceedings{mccarthy2012proving,
  author    = {McCarthy, Zoe and Bretl, Timothy and Hutchinson, Seth},
  title     = {Proving Path Non-Existence Using Sampling and Alpha Shapes},
  booktitle = {IEEE International Conference on Robotics and Automation (ICRA)},
  pages     = {2563--2569},
  year      = {2012},
  note      = {Alpha-shapes dans C_obs — l'extension >3D bute sur le calcul des alpha-shapes en haute dimension (limite reconnue par Li-Dantam).}
}

@article{varava2021free,
  author    = {Varava, Anastasiia and Carvalho, J. Frederico and Kragic, Danica and Pokorny, Florian T.},
  title     = {Free Space of Rigid Objects: Caging, Path Non-Existence, and Narrow Passage Detection},
  journal   = {The International Journal of Robotics Research},
  volume    = {40},
  number    = {10-11},
  pages     = {1049--1067},
  year      = {2021},
  note      = {Non-existence pour objets rigides (caging) — pas de bras articulés.}
}

@inproceedings{varadhan2005star,
  author    = {Varadhan, Gokul and Manocha, Dinesh},
  title     = {Star-Shaped Roadmaps — A Deterministic Sampling Approach for Complete Motion Planning},
  booktitle = {Robotics: Science and Systems (RSS)},
  year      = {2005},
  note      = {Échantillonnage déterministe complet — contexte complétude.}
}

@inproceedings{basch2001disconnection,
  author    = {Basch, Julien and Guibas, Leonidas J. and Hsu, David and Nguyen, An Thai},
  title     = {Disconnection Proofs for Motion Planning},
  booktitle = {IEEE International Conference on Robotics and Automation (ICRA)},
  year      = {2001},
  note      = {[à vérifier : pages, et lire — probablement le premier usage du terme « disconnection proof », cas 2D/3D géométriques] Antériorité terminologique à créditer.}
}
```

## 3. CERTIFICATION DU LIBRE (le « dual » de notre problème — C-IRIS)

```bibtex
@incollection{amice2023finding,
  author    = {Amice, Alexandre and Dai, Hongkai and Werner, Peter and Zhang, Annan and Tedrake, Russ},
  title     = {Finding and Optimizing Certified, Collision-Free Regions in Configuration Space for Robot Manipulators},
  booktitle = {Algorithmic Foundations of Robotics XV (WAFR 2022)},
  pages     = {328--348},
  publisher = {Springer},
  year      = {2023},
  doi       = {10.1007/978-3-031-21090-7_20},
  note      = {C-IRIS conférence (arXiv:2205.03690). Certifient le LIBRE par SOS sur la même paramétrisation rationnelle — nous certifions l'OBSTRUCTION par LP. Le miroir exact de notre positionnement.}
}

@article{dai2024certified,
  author    = {Dai, Hongkai and Amice, Alexandre and Werner, Peter and Zhang, Annan and Tedrake, Russ},
  title     = {Certified Polyhedral Decompositions of Collision-Free Configuration Space},
  journal   = {The International Journal of Robotics Research},
  year      = {2024},
  doi       = {10.1177/02783649231201437},
  note      = {Version journal C-IRIS (arXiv:2302.12219). Contient (§3.2) le rappel Positivstellensatz/certificats d'infaisabilité d'ENSEMBLES (Parrilo) — utile pour situer notre théorème. C'est aussi la source de la paramétrisation s=tan(θ/2) pour la FK (avec Drake RationalForwardKinematics).}
}

@misc{petersen2023growing,
  author    = {Petersen, Mark E. and Tedrake, Russ},
  title     = {Growing Convex Collision-Free Regions in Configuration Space using Nonlinear Programming},
  howpublished = {arXiv:2303.14737},
  year      = {2023},
  note      = {IRIS-NP : abandonne la certification rigoureuse pour la vitesse (probabiliste) — illustre le coût du rigoureux côté libre.}
}

@incollection{deits2015computing,
  author    = {Deits, Robin and Tedrake, Russ},
  title     = {Computing Large Convex Regions of Obstacle-Free Space Through Semidefinite Programming},
  booktitle = {Algorithmic Foundations of Robotics XI (WAFR 2014)},
  publisher = {Springer},
  year      = {2015},
  note      = {[à vérifier : pages] IRIS original (espace de travail). Une ligne de contexte.}
}
```

## 4. CERTIFICATS ALGÉBRIQUES DE DÉCONNEXION ET BARRIÈRES (les voisins mathématiques)

```bibtex
@misc{henrion2024algebraic,
  author    = {Henrion, Didier and Miller, Jared and Safey El Din, Mohab},
  title     = {Algebraic Proofs of Path Disconnectedness using Time-Dependent Barrier Functions},
  howpublished = {arXiv:2404.06985},
  year      = {2024},
  note      = {★ LE VOISIN LE PLUS PROCHE (découvert par cette revue). Déconnexion = infaisabilité d'un OCP intégrateur simple ; barrière v(t,x) nécessaire ET suffisante (compacité, lemme de Farkas en dimension infinie) ; hiérarchie moment-SOS (Yalmip+Mosek). Exemples n ≤ 3 abstraits. PAS de cinématique robot, PAS de vérification exacte (Gram flottante), horizon T à borner (D'Acunto-Kurdyka, borne exponentielle en n). À citer ET différencier soigneusement — voir §0. [à vérifier avant soumission : publication journal/à jour ?]}
}

@misc{korda2022urysohn,
  author    = {Korda, Milan and Lasserre, Jean-Bernard and Lazarev, Alexey and Magron, Victor and Naldi, Simone},
  title     = {Urysohn in Action: Separating Semi-Algebraic Sets by Polynomials},
  howpublished = {arXiv:2207.00570},
  year      = {2022},
  note      = {Certificat polynomial de NON-INTERSECTION de deux ensembles semi-algébriques (moment-SOS) — ne prouve pas la déconnexion-dans-X (distinction faite par Henrion et al. eux-mêmes).}
}

@inproceedings{prajna2004safety,
  author    = {Prajna, Stephen and Jadbabaie, Ali},
  title     = {Safety Verification of Hybrid Systems Using Barrier Certificates},
  booktitle = {Hybrid Systems: Computation and Control (HSCC)},
  series    = {LNCS},
  volume    = {2993},
  pages     = {477--492},
  publisher = {Springer},
  year      = {2004},
  note      = {Le certificat-barrière originel. Notre dalle {|φ|≤δ} ⊆ C_obs est une barrière STATIQUE d'un problème sans dynamique — filiation à dire en une phrase.}
}

@inproceedings{prajna2005necessity,
  author    = {Prajna, Stephen and Rantzer, Anders},
  title     = {On the Necessity of Barrier Certificates},
  booktitle = {IFAC World Congress},
  volume    = {38},
  number    = {1},
  pages     = {526--531},
  year      = {2005},
  note      = {Nécessité sous condition de Slater — c'est son ÉCHEC qui force la dépendance temporelle chez Henrion et al. ; notre schéma statique l'évite en n'étant que suffisant. Argument de design à assumer.}
}
```

## 5. DÉCISION EXACTE PAR ALGÈBRE RÉELLE (complets mais sans certificat)

```bibtex
@book{canny1988complexity,
  author    = {Canny, John},
  title     = {The Complexity of Robot Motion Planning},
  publisher = {MIT Press},
  year      = {1988},
  note      = {Roadmap algorithm : décide la connexité de C_free semi-algébrique, simplement exponentiel en n². Complet, exact — mais ne rend AUCUN artefact contrôlable dans le cas déconnecté.}
}

@article{safey2017nearly,
  author    = {Safey El Din, Mohab and Schost, {\'E}ric},
  title     = {A Nearly Optimal Algorithm for Deciding Connectivity Queries in Smooth and Bounded Real Algebraic Sets},
  journal   = {Journal of the ACM},
  volume    = {63},
  number    = {6},
  pages     = {1--37},
  year      = {2017},
  note      = {État de l'art des roadmaps exacts. Co-auteur de henrion2024algebraic — la communauté algèbre réelle arrive sur notre terrain par l'autre versant.}
}

@article{prebet2024roadmaps,
  author    = {Pr{\'e}bet, R{\'e}mi and Safey El Din, Mohab and Schost, {\'E}ric},
  title     = {Computing Roadmaps in Unbounded Smooth Real Algebraic Sets I: Connectivity Results},
  journal   = {Journal of Symbolic Computation},
  volume    = {120},
  pages     = {102234},
  year      = {2024},
  note      = {Lignée active — une ligne de contexte (partie II en preprint).}
}

@article{schwartz1983piano,
  author    = {Schwartz, Jacob T. and Sharir, Micha},
  title     = {On the ``Piano Movers''~Problem. II. General Techniques for Computing Topological Properties of Real Algebraic Manifolds},
  journal   = {Advances in Applied Mathematics},
  volume    = {4},
  number    = {3},
  pages     = {298--351},
  year      = {1983},
  note      = {[à vérifier : pages] Décomposition cylindrique algébrique appliquée au motion planning — l'ancêtre théorique de toute décision exacte. Une phrase historique.}
}
```

## 6. MÉTHODES PAR INTERVALLES GARANTIES (rigoureuses, sans certificat exportable)

```bibtex
@article{jaulin2001path,
  author    = {Jaulin, Luc},
  title     = {Path Planning Using Intervals and Graphs},
  journal   = {Reliable Computing},
  volume    = {7},
  number    = {1},
  year      = {2001},
  note      = {[à vérifier : pages] Conclut « No path » de manière GARANTIE (sous-pavages + arrondi extérieur, composantes de graphe disjointes). La vraie antériorité « non-existence rigoureuse » — basse dimension, et la garantie vit dans l'exécution, pas dans un certificat.}
}

@article{delanoue2006interval,
  author    = {Delanoue, Nicolas and Jaulin, Luc and Cottenceau, Bertrand},
  title     = {Using Interval Arithmetic to Prove that a Set is Path-Connected},
  journal   = {Theoretical Computer Science},
  volume    = {351},
  number    = {1},
  pages     = {119--128},
  year      = {2006},
  note      = {Connexité PROUVÉE par intervalles (étoilé + nerf). Cité par Henrion et al. avec la critique exacte qui nous sert : « do not provide certificates verifiable independently by a third party ».}
}

@incollection{delanoue2006counting,
  author    = {Delanoue, Nicolas and Jaulin, Luc and Cottenceau, Bertrand},
  title     = {Counting the Number of Connected Components of a Set and Its Application to Robotics},
  booktitle = {Applied Parallel Computing (PARA 2004)},
  series    = {LNCS},
  volume    = {3732},
  pages     = {93--101},
  publisher = {Springer},
  year      = {2006},
  doi       = {10.1007/11558958_11},
  note      = {Composantes connexes par intervalles, application robotique.}
}

@book{jaulin2001applied,
  author    = {Jaulin, Luc and Kieffer, Michel and Didrit, Olivier and Walter, {\'E}ric},
  title     = {Applied Interval Analysis},
  publisher = {Springer},
  year      = {2001},
  note      = {Référence générale intervalles (si besoin d'une seule citation d'ancrage).}
}
```

## 7. POSITIVITÉ POLYNOMIALE : BERNSTEIN / HANDELMAN / PUTINAR (nos fondations)

```bibtex
@article{handelman1988representing,
  author    = {Handelman, David},
  title     = {Representing Polynomials by Positive Linear Functions on Compact Convex Polyhedra},
  journal   = {Pacific Journal of Mathematics},
  volume    = {132},
  number    = {1},
  pages     = {35--62},
  year      = {1988},
  note      = {[à vérifier : vol/pages] LE théorème de représentation LP-représentable sur polytopes. Notre certificat Bernstein sur boîte en est l'instance pratique — à citer au théorème.}
}

@article{putinar1993positive,
  author    = {Putinar, Mihai},
  title     = {Positive Polynomials on Compact Semi-Algebraic Sets},
  journal   = {Indiana University Mathematics Journal},
  volume    = {42},
  number    = {3},
  pages     = {969--984},
  year      = {1993},
  note      = {Le Positivstellensatz dont notre forme g − μT est le tronqué de degré bas (et dont le SIGNE est notre règle 2). Citer pour la filiation du schéma slab-aware.}
}

@misc{sankaranarayanan2014lyapunov,
  author    = {Ben Sassi, Mohamed Amin and Sankaranarayanan, Sriram and Chen, Xin and {\'A}brah{\'a}m, Erika},
  title     = {Linear Relaxations of Polynomial Positivity for Polynomial Lyapunov Function Synthesis},
  howpublished = {arXiv:1407.2952 (IMA J. Math. Control Inf., 2016)},
  year      = {2014},
  note      = {[à vérifier : auteurs exacts et venue finale] Bernstein/Handelman en LP pour la synthèse de Lyapunov — le précédent « LP au lieu de SOS pour des certificats de contrôle », et la preuve que Bernstein domine Handelman sur la boîte unité. Très utile pour justifier notre choix LP.}
}

@article{garloff1993bernstein,
  author    = {Garloff, J{\"u}rgen},
  title     = {The Bernstein Algorithm},
  journal   = {Interval Computations},
  volume    = {2},
  pages     = {154--168},
  year      = {1993},
  note      = {[à vérifier] Bornes de Bernstein + branch-and-bound sur boîtes — la mécanique exacte de notre moteur (étiquetage outside) ; citer aussi un survol récent Garloff/Smith si trouvé.}
}

@book{lasserre2009moments,
  author    = {Lasserre, Jean-Bernard},
  title     = {Moments, Positive Polynomials and Their Applications},
  publisher = {Imperial College Press},
  year      = {2009},
  note      = {Référence hiérarchie moment-SOS (le cadre de C-IRIS et de Henrion et al., que nous N'utilisons PAS — citer pour le contraste).}
}

@phdthesis{parrilo2000structured,
  author    = {Parrilo, Pablo A.},
  title     = {Structured Semidefinite Programs and Semialgebraic Geometry Methods in Robustness and Optimization},
  school    = {California Institute of Technology},
  year      = {2000},
  note      = {SOS programming fondateur — une citation de contexte.}
}
```

## 8. FONDATIONS MOTION PLANNING (introduction / notations)

```bibtex
@article{lozano1983spatial,
  author    = {Lozano-P{\'e}rez, Tom{\'a}s},
  title     = {Spatial Planning: A Configuration Space Approach},
  journal   = {IEEE Transactions on Computers},
  volume    = {C-32},
  number    = {2},
  pages     = {108--120},
  year      = {1983},
  note      = {C-space.}
}

@book{latombe1991robot,
  author    = {Latombe, Jean-Claude},
  title     = {Robot Motion Planning},
  publisher = {Kluwer Academic Publishers},
  year      = {1991}
}

@book{lavalle2006planning,
  author    = {LaValle, Steven M.},
  title     = {Planning Algorithms},
  publisher = {Cambridge University Press},
  year      = {2006}
}

@article{kavraki1996probabilistic,
  author    = {Kavraki, Lydia E. and {\v S}vestka, Petr and Latombe, Jean-Claude and Overmars, Mark H.},
  title     = {Probabilistic Roadmaps for Path Planning in High-Dimensional Configuration Spaces},
  journal   = {IEEE Transactions on Robotics and Automation},
  volume    = {12},
  number    = {4},
  pages     = {566--580},
  year      = {1996},
  note      = {[à vérifier : pages] PRM — complétude probabiliste seulement : ne termine pas si infaisable. Le problème que nous résolvons.}
}

@techreport{lavalle1998rrt,
  author    = {LaValle, Steven M.},
  title     = {Rapidly-Exploring Random Trees: A New Tool for Path Planning},
  institution = {Computer Science Dept., Iowa State University},
  number    = {TR 98-11},
  year      = {1998}
}

@inproceedings{kuffner2000rrtconnect,
  author    = {Kuffner, James J. and LaValle, Steven M.},
  title     = {RRT-Connect: An Efficient Approach to Single-Query Path Planning},
  booktitle = {IEEE International Conference on Robotics and Automation (ICRA)},
  year      = {2000}
}

@inproceedings{branicky2001quasi,
  author    = {Branicky, Michael S. and LaValle, Steven M. and Olson, Kari and Yang, Libo},
  title     = {Quasi-Randomized Path Planning},
  booktitle = {IEEE International Conference on Robotics and Automation (ICRA)},
  year      = {2001},
  note      = {[à vérifier : auteurs/titre exact] Échantillonnage déterministe low-dispersion : garanties faibles de non-existence (couverture) — contraste avec un certificat.}
}

@article{janson2018deterministic,
  author    = {Janson, Lucas and Ichter, Brian and Pavone, Marco},
  title     = {Deterministic Sampling-Based Motion Planning: Optimality, Complexity, and Performance},
  journal   = {The International Journal of Robotics Research},
  volume    = {37},
  number    = {1},
  pages     = {46--61},
  year      = {2018},
  note      = {[à vérifier : vol/pages]}
}
```

## 9. APPLICATION TAMP + OUTILS

```bibtex
@article{garrett2021integrated,
  author    = {Garrett, Caelan Reed and Chitnis, Rohan and Holladay, Rachel and Kim, Beomjoon and Silver, Tom and Kaelbling, Leslie Pack and Lozano-P{\'e}rez, Tom{\'a}s},
  title     = {Integrated Task and Motion Planning},
  journal   = {Annual Review of Control, Robotics, and Autonomous Systems},
  volume    = {4},
  pages     = {265--293},
  year      = {2021},
  note      = {[à vérifier : pages] Le survey TAMP — motive l'élagage prouvé (cas d'usage bin-picking S9b).}
}

@misc{drake,
  author    = {Tedrake, Russ and the Drake Development Team},
  title     = {Drake: Model-Based Design and Verification for Robotics},
  howpublished = {\url{https://drake.mit.edu}},
  year      = {2019},
  note      = {RationalForwardKinematics (générateur uniquement — verify.py n'en dépend pas, à dire dans le papier).}
}

@article{huangfu2018parallelizing,
  author    = {Huangfu, Qi and Hall, J. A. Julian},
  title     = {Parallelizing the Dual Revised Simplex Method},
  journal   = {Mathematical Programming Computation},
  volume    = {10},
  number    = {1},
  pages     = {119--142},
  year      = {2018},
  note      = {HiGHS — notre solveur LP.}
}
```

---

## 10. RESTE À FAIRE AVANT SOUMISSION (checklist)

1. Confirmer tous les champs **[à vérifier]** (≈ 12 entrées, ~1 h sur DBLP/éditeurs).
2. Vérifier si henrion2024algebraic a été publié en journal depuis (citer la
   version finale) ; relire leurs §3-4 au moment de rédiger notre théorème pour
   créditer proprement le lien barrière↔déconnexion.
3. Basch et al. 2001 : lire (antériorité du terme « disconnection proof »).
4. Balayage ciblé de dernière minute (mois précédant la soumission) :
   « infeasibility certificate motion planning », « disconnectedness certificate »,
   « Bernstein certificate robot » — le créneau bouge (trois groupes actifs :
   Mines/Colorado, LAAS/Sorbonne/ETH, Gênes).
5. Optionnel : D'Acunto & Kurdyka 2006 (borne de diamètre géodésique) si on
   discute la comparaison des horizons avec Henrion et al.
