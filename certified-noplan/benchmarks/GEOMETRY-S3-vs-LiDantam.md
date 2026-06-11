# S3 geometry: paper (Li-Dantam RSS 2021 Fig. 7b) ↔ our YAML  [A21]

Honest correspondence table requested by the V4 review (A21). **Li & Dantam publish no
numeric geometry** for their 4-DOF shoulder-elbow scene — RSS 2021 §V-B gives only the
kinematic structure and the task in prose, and Fig. 7b shows it graphically (no link
lengths, no box dimensions, no joint-limit values, no numeric start/goal). So this table
separates what is **FAITHFUL** (the robot topology and the infeasible-reach narrative,
which the paper does state) from what is **CHOSEN by us** (every dimension and limit,
which the paper does not give). This is the documented approximate reproduction the S6
review anticipated — not an import.

Paper source quote (RSS 2021 §V-B): *"The robot has a shoulder joint (three DoF
spherical) and an elbow joint (one DoF revolute). The goal is to reach inside the red
box."* — that is the full extent of the published geometry.

| Aspect | Li-Dantam RSS 2021 Fig. 7b | Our `scenes/S3_shoulder_elbow.yaml` | Status |
|---|---|---|---|
| Robot topology | spherical shoulder (3-DOF) + revolute elbow (1-DOF) | j0 yaw (z), j1 pitch (y), j2 roll (x) concurrent at base = spherical shoulder; j3 elbow (y) | **FAITHFUL** |
| DOF | 4 | 4 (`spatial_revolute`, n = 4) | **FAITHFUL** |
| Joint type | all revolute (no prismatic) | all revolute | **FAITHFUL** |
| Infeasible task | "reach inside the box" — unreachable | reach the target bay past a shelf panel — unreachable | **FAITHFUL (narrative)** |
| Why infeasible | arm cannot fit into the box | the upper-arm link is trapped by a panel for the whole yaw band, every pitch | **ADAPTED** (proximal trap, so a low-degree algebraic barrier applies — the S5/S6 lesson; a distal-joint barrier is defeated by redundancy) |
| Upper-arm length | not published | **2/5 m** (= 0.40) | chosen (plausible) |
| Forearm length | not published | **3/10 m** (= 0.30) — *visual only*, NOT in the certificate (the certified body is the upper arm) | chosen |
| Obstacle ("box"/panel) | not published | front panel, box `x∈[3/20,1/5], y∈[-3/50,3/50], z∈[-3/5,3/5]` m (= x∈[0.15,0.20], y∈[±0.06], z∈[±0.60]) | chosen |
| Joint limits | not published (factory limits ⊂ (−π,π) assumed) | s-box `s0∈[±7/10]`, `s1∈[±2/5]`, `s2∈[±1]`, `s3∈[0,7/5]`; q = 2·arctan(s) ⟹ **lacet ±70°, tangage ±44°, roll ±90°, coude 0–109°** — all ⊂ (−π,π). Roll/elbow are passive, given physically realistic ranges (no elbow hyperextension) | chosen (⊂ (−π,π), SPEC §2; explicit on every figure/slider/verdict — A25) |
| start / goal | shown graphically only | `s0 = −3/5` (yaw left, free) → `s0 = +3/5` (yaw right, free); other joints 0 | chosen (both free) |
| Barrier φ | (their method learns a manifold) | φ = s0 (base yaw), δ = 1/10 | our method (baked rational barrier) |

## The natural-objection answers (V4)

The figures are built to pre-empt a viewer's objections (the benchmark-scene bar set by
the V4 review, A23):

- **"Why not go OVER the panel?"** — `scene_S3_shoulder_elbow_side.png` (side view, x–z):
  the panel TOP (z = 0.6) is higher than the upper arm's entire reach (0.4 m), so no
  configuration places any upper-arm point above z = 0.4. The pitch fan (9/9 in
  collision) shows that even at maximum pitch the upper arm crosses the panel depth at
  z ≤ 0.19 m, deep inside the panel. **The block is the WALL HEIGHT, not the pitch joint
  limit** (at the pitch limit the arm still rams the panel; the limit only keeps the arm
  long enough to reach the panel depth — beyond ≈68° pitch it would fall *short*, which
  is not an "over the top" escape and is outside the operating box anyway).
- **"Why not go AROUND in yaw?"** — `scene_S3_shoulder_elbow_cspace.png` (C-space, yaw
  s0 × pitch s1): the grey collision wall spans *every* pitch, the gold slab |φ|≤δ sits
  entirely inside it, and start (★) / goal (✚) are on opposite sides — there is no free
  detour in (s0, s1), and the body is independent of the passive s2, s3, so no detour in
  those either.
- **"Does the direct motion really collide?"** — `scene_S3_shoulder_elbow_sweep.png`
  (top-down, x–y): the straight start→goal yaw swing, middle poses red (ramming the
  panel), endpoints green (free).

## Soundness note

These figures show *intention* — the engine (Bernstein-LP branch-and-bound) is the
arbiter, and a dense 300k seeded sample finds 0 free configs in the slab (CLAUDE.md
rule 9: the grid/eye does not prove anything; the certificate does). At spatial robots
the verdict is ENGINE-PROOF until the exact verifier gains `spatial_revolute` (S9).
