# BIBLIO-VERIFIED.md — A28 verification pass (supervision, 2026-09-09)

Every entry below was checked against a primary source (publisher page,
arXiv abstract, author page, or proceedings BibTeX) on 2026-09-09. Status:
VERIFIED = as previously cited; CORRECTED = a field was wrong in our notes;
NEW = added by this pass; STANDARD = classical reference, no online check
needed. Supersedes the [VERIFY] tags in PAPER-SKELETON.md and
docs/BIBLIO-ANTERIORITE.md.

## A. The Li–Dantam lineage (Colorado School of Mines) — the closest robotics work

A1. VERIFIED — S. Li, N. T. Dantam, "Towards general infeasibility proofs in
    motion planning," IROS 2020, pp. 6704–6710.
A2. VERIFIED — S. Li, N. T. Dantam, "Learning Proofs of Motion Planning
    Infeasibility," Robotics: Science and Systems XVII, paper 64, 2021,
    DOI 10.15607/RSS.2021.XVII.064. 3-DOF and 4-DOF manipulators (shoulder-
    elbow, SCARA); "proofs for this four DoF arm take less than 4 minutes on
    average" (Table II). Learned SVM manifold + triangulation, floating-point
    collision validation.
A3. VERIFIED — S. Li, N. T. Dantam, "Exponential Convergence of Infeasibility
    Proofs for Kinematic Motion Planning," WAFR 2022 (Algorithmic Foundations
    of Robotics XV), DOI 10.1007/978-3-031-21090-7_18.
A4. CORRECTED (title) — S. Li, N. T. Dantam, "A sampling and learning
    framework to prove motion planning infeasibility," Int. J. Robotics
    Research 42(10): 938–956, 2023, DOI 10.1177/02783649231154674.
    Our notes called this the IJRR version of "Learning Proofs..."; the
    journal TITLE differs. Cite with the journal title.
A5. VERIFIED — S. Li, N. T. Dantam, "Scaling infeasibility proofs via
    concurrent, codimension-one, locally-updated Coxeter triangulation,"
    IEEE Robotics and Automation Letters 8(12): 8303–8310, 2023.
    (This confirms A36: IJRR 2023 and RA-L 2023 are two DIFFERENT papers.)
A6. VERIFIED — S. Li, N. T. Dantam, "Scaling Motion Planning Infeasibility
    Proofs," arXiv:2406.04795, June 2024. GPU manifold tracing with Coxeter
    triangulation, batch triangulation; "two orders of magnitude speed-up".
    5–6-DoF scenes; RTX 4070 + i9-13900K; 6-DoF "< 1 min on average" (read in
    the PDF, S9d). No journal/conference version found as of 2026-09-09 —
    cite as arXiv preprint.
    NOTE FOR STÉPHANE: their ref. [9] is S. Cambon, R. Alami, F. Gravot,
    "A hybrid approach to intricate motion, manipulation and task planning,"
    IJRR 28(1): 104–126, 2009 — they cite your aSyMov work as TAMP motivation.
    Worth a sentence in the intro (the TAMP-pruning use case closes a loop).

## B. Algebraic / exact / certified neighbours

B1. VERIFIED (title corrected to exact) — D. Henrion, J. Miller, M. Safey El
    Din, "Algebraic Proofs of Path Disconnectedness using Time-Dependent
    Barrier Functions," arXiv:2404.06985, April 2024, 17 pp. Code:
    github.com/jarmill/set_connected. Moment-SOS hierarchy, necessary-and-
    sufficient on abstract basic semialgebraic sets, examples n ≤ 3, SDP
    (floating point). Still listed as arXiv on Henrion's publication page
    (2026) — cite as preprint. Fence (A37): "different settings".
B2. VERIFIED (exact reference) — H. Dai*, A. Amice*, P. Werner, A. Zhang,
    R. Tedrake, "Certified Polyhedral Decompositions of Collision-Free
    Configuration Space," Int. J. Robotics Research, 2024,
    DOI 10.1177/02783649231201437 (arXiv:2302.12219). Earlier: A. Amice,
    H. Dai, P. Werner, A. Zhang, R. Tedrake, "Finding and Optimizing
    Certified, Collision-Free Regions in Configuration Space for Robot
    Manipulators," WAFR 2022.
    IMPORTANT FOR RELATED WORK: C-IRIS works in the SAME rational
    parametrization of C-space (tan half-angle) that we use — it is the
    origin of Drake's RationalForwardKinematics that our generator calls.
    Complementary question (certify collision-FREE polytopes vs our
    disconnection), SOS/SDP floating-point certificates vs our exact LP
    verification. Demonstrated on a 7-DOF KUKA iiwa, UR3e, 12-DOF bimanual.
    We must acknowledge the shared parametrization explicitly.
B3. NEW — J. Capco, M. Safey El Din, J. Schicho, "Robots, computer algebra
    and eight connected components," ISSAC 2020, pp. 62–69; and "Positive
    dimensional parametric polynomial systems, connectivity queries and
    applications in robotics," J. Symbolic Computation 115: 320–345, 2023.
    Exact symbolic connectivity queries for robot kinematics (cuspidal
    robots, singularity-free paths) — exact, but a DIFFERENT question
    (connectivity of the kinematic map's domain, no workspace obstacles).
    One sentence: exact connectivity has been done symbolically for
    kinematic singularities; not for obstacle-induced disconnection of arms.
B4. VERIFIED — L. Jaulin, "Path Planning Using Intervals and Graphs,"
    Reliable Computing 7(1): 1–15, 2001, DOI 10.1023/A:1011400431065.
    Interval analysis computes the NUMBER of path-connected components of a
    set defined by nonlinear inequalities (so it can prove disconnection),
    guaranteed by outward rounding; 2-D robotics example; the "proof" is the
    paving itself, no compact re-checkable object. Also: L. Jaulin,
    M. Kieffer, O. Didrit, E. Walter, Applied Interval Analysis, Springer
    2001 (STANDARD).
B5. STANDARD — J. F. Canny, The Complexity of Robot Motion Planning, MIT
    Press, 1988 (roadmap algorithm, exact, singly-exponential).
B6. STANDARD — M. Putinar, "Positive polynomials on compact semi-algebraic
    sets," Indiana Univ. Math. J. 42(3): 969–984, 1993 (the g − μT form).
B7. STANDARD — Bernstein enclosure bounds: J. Garloff, "Convergent bounds
    for the range of multivariate polynomials," Interval Mathematics 1985,
    LNCS 212, pp. 37–56 (or Garloff & Smith survey). To pick one at drafting.

## C. Path non-existence in robotics (older, floating-point) — for completeness

C1. NEW — L. Zhang, Y. J. Kim, D. Manocha, "Efficient cell labelling and
    path non-existence computation using C-obstacle query," IJRR 27(11-12):
    1246–1257, 2008.
C2. NEW — Z. McCarthy, T. Bretl, S. Hutchinson, "Proving path non-existence
    using sampling and alpha shapes," ICRA 2012, pp. 2563–2569.
C3. NEW — A. Varava, J. F. Carvalho, D. Kragic, F. T. Pokorny, "Free space
    of rigid objects: Caging, path non-existence, and narrow passage
    detection," IJRR 40(10-11), 2021.
C4. VERIFIED — A. Thomas, F. Mastrogiovanni, M. Baglietto, "An Incremental
    Sampling and Segmentation-Based Approach for Motion Planning
    Infeasibility," arXiv:2501.11434, Jan. 2025; accepted in Robotics and
    Autonomous Systems (per arXiv comment). Discretized bitmap C-space,
    up to 5 DOF; detection, not a certificate (discretization + sampling).
    (The "Genoa group" of our notes.)
C5. NEW (recent, shows the field is active) — "Learning Motion Feasibility
    from Point Clouds in Cluttered Environments," arXiv:2606.26700, June
    2026 (authors to be read from the PDF before citing). States that
    "existing approaches for infeasibility certification are limited to
    low-dimensional configuration spaces and often assume simplified
    geometric environments" — a claim our 7-DOF exact certificate directly
    addresses. Learning-based feasibility prediction, complementary.

## D. Tools

D1. STANDARD — Q. Huangfu, J. A. J. Hall, "Parallelizing the dual revised
    simplex method," Math. Prog. Computation 10(1): 119–142, 2018 (HiGHS).
D2. STANDARD — R. Tedrake and the Drake Development Team, Drake: Model-based
    design and verification for robotics, 2019, https://drake.mit.edu.
D3. (future-work refs) — H. Waki, S. Kim, M. Kojima, M. Muramatsu, "Sums of
    squares and semidefinite program relaxations for polynomial optimization
    problems with structured sparsity," SIAM J. Optim. 17(1): 218–242, 2006
    (correlative sparsity, for §8).

## Corrections to propagate

1. IJRR 2023 title → "A sampling and learning framework to prove motion
   planning infeasibility" (PAPER-SKELETON §2, DECISION-G2 §4 note A36,
   docs/BIBLIO-ANTERIORITE.md).
2. Henrion et al. title → exact ("Algebraic Proofs of Path Disconnectedness
   using Time-Dependent Barrier Functions").
3. C-IRIS: add the shared rational parametrization sentence (B2) — this is a
   fairness point a reviewer from the Tedrake group would raise immediately.
4. Add C1–C3 as the classical path-non-existence line (one sentence).
5. Add B3 (Safey El Din robotics connectivity) — Henrion's co-author has
   robotics-exact prior work; not citing it would look like an omission.
6. Intro: one sentence noting Li–Dantam cite Cambon–Alami–Gravot 2009 as
   TAMP motivation (author's prior work; discloses the connection honestly).

## Not verified / to do at drafting

- Exact author list of arXiv:2606.26700 (C5) — read the PDF.
- Pick the Bernstein-bounds reference (B7).
- RSS 2027 submission deadline — check the call when it is published.
