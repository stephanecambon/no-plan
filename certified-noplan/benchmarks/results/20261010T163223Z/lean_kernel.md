# Kernel evaluation of `check c` — 20261010T163223Z

- commit `157c671a7880114bf43695859f0c9f6d394d392c` (tree dirty at start: False)
- Lean (version 4.34.1, arm64-apple-darwin24.6.0, commit 5045d0056413266e57c625dcd7c365b10e377c52, Release); Mathlib `v4.34.1`
- Darwin 25.5.0 arm64, Apple M4; load average at start [6.24, 5.39, 5.42]
- limits per process: 1500 s, 9 GB resident

| certificate | n | leaves (collision / outside) | body vertices | `decide` | `decide +kernel`, one evaluation | staged kernel proof | `native_decide` (adds an axiom) |
|---|---|---|---|---|---|---|---|
| `scenes/wall/k3.cert.json` | 3 | 2 (2 / 0) | 2 | FAIL (reduction stuck at `match check wallK3, true with`; already on the first test `¬ (wallK3.delta ≤ 0)`: reduction stuck at `match Rat.blt 0 wallK3.delta, false with`) | FAIL (killed, memory > 9 GB, after 53 s) | 359 s (kernel 355 s), 5.6 GB, 34 stages | 2.6 s (evaluation 0.138 s), 1.1 GB |
| `scenes/S3_shoulder_elbow.cert.json` | 4 | 8 (4 / 4) | 2 | FAIL (reduction stuck at `match check s3ShoulderElbow, true with`; already on the first test `¬ (s3ShoulderElbow.delta ≤ 0)`: reduction stuck at `match Rat.blt 0 s3ShoulderElbow.delta, false with`) | FAIL (killed, memory > 9 GB, after 51 s) | FAIL at stage 5/64 `geometry_eq` (killed, memory > 9 GB, after 50 s); 4 stages passed in 0 s of kernel | 1.1 s (evaluation 0.19 s), 1.1 GB |
| `scenes/S6_iiwa_real_shelf.cert.json` | 7 | 2 (2 / 0) | 40 | FAIL (reduction stuck at `match check s6IiwaRealShelf, true with`; already on the first test `¬ (s6IiwaRealShelf.delta ≤ 0)`: reduction stuck at `match Rat.blt 0 s6IiwaRealShelf.delta, false with`) | FAIL (killed, memory > 9 GB, after 20 s) | FAIL at stage 1/34 `assumptions` (error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached); 0 stages passed in 0 s of kernel | 24.8 s (evaluation 22.4 s), 1.1 GB |

Wall-clock figures include loading the imports (2.1 s, 2.4 s, 0.9 s).

## Stages — `scenes/wall/k3.cert.json`

| stage | result | wall s | kernel s | peak GB |
|---|---|---|---|---|
| `assumptions` | ok | 2.6 | 0.0 | 1.1 |
| `conditionI` | ok | 2.6 | 0.0 | 1.1 |
| `partition` | ok | 2.6 | 0.0 | 1.1 |
| `kinematics` | ok | 2.6 | 0.0 | 1.1 |
| `geometry_eq` | ok | 40.0 | 37.4 | 5.6 |
| `slab_eq` | ok | 3.1 | 0.4 | 1.14 |
| `lamDeg_eq` | ok | 2.8 | 0.0 | 1.1 |
| `leaves_size` | ok | 2.6 | 0.0 | 1.1 |
| `L0_X` | ok | 13.6 | 10.9 | 2.57 |
| `L0_count` | ok | 2.8 | 0.0 | 1.1 |
| `L0_sum` | ok | 3.1 | 0.2 | 1.1 |
| `L0_lam` | ok | 3.1 | 0.3 | 1.14 |
| `L0_obs` | ok | 2.8 | 0.0 | 1.1 |
| `L0_mu` | ok | 2.8 | 0.0 | 1.1 |
| `O0_faces` | ok | 2.6 | 0.0 | 1.1 |
| `L0_face0` | ok | 27.8 | 24.8 | 3.8 |
| `L0_face1` | ok | 25.1 | 22.5 | 3.77 |
| `L0_face2` | ok | 21.6 | 18.4 | 3.27 |
| `L0_face3` | ok | 27.0 | 23.8 | 3.83 |
| `L0_face4` | ok | 26.5 | 23.6 | 3.79 |
| `L0_face5` | ok | 22.1 | 19.0 | 3.27 |
| `L1_X` | ok | 16.7 | 13.4 | 2.57 |
| `L1_count` | ok | 3.1 | 0.0 | 1.1 |
| `L1_sum` | ok | 3.1 | 0.2 | 1.12 |
| `L1_lam` | ok | 3.1 | 0.3 | 1.14 |
| `L1_obs` | ok | 2.9 | 0.0 | 1.1 |
| `L1_mu` | ok | 2.9 | 0.0 | 1.1 |
| `O1_faces` | ok | 2.8 | 0.0 | 1.1 |
| `L1_face0` | ok | 27.5 | 24.6 | 3.98 |
| `L1_face1` | ok | 26.4 | 23.4 | 3.86 |
| `L1_face2` | ok | 21.0 | 18.1 | 3.32 |
| `L1_face3` | ok | 31.2 | 27.8 | 4.0 |
| `L1_face4` | ok | 28.7 | 25.5 | 3.84 |
| `L1_face5` | ok | 23.1 | 19.7 | 3.32 |

Axioms of the staged proof: ['propext', 'Classical.choice', 'Quot.sound']
Axioms of the `native_decide` proof: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

## Stages — `scenes/S3_shoulder_elbow.cert.json`

| stage | result | wall s | kernel s | peak GB |
|---|---|---|---|---|
| `assumptions` | ok | 4.7 | 0.0 | 1.14 |
| `conditionI` | ok | 4.7 | 0.1 | 1.14 |
| `partition` | ok | 4.7 | 0.1 | 1.15 |
| `kinematics` | ok | 4.7 | 0.1 | 1.14 |
| `geometry_eq` | killed: memory > 9 GB | 49.9 | 0 | 9.04 |
| … 59 later stage(s) | not needed: the proof already fails; one stage of each other kind probed below | | | |
| (information) `slab_eq` | ok | 7.3 | 2.3 | 1.49 |
| (information) `lamDeg_eq` | ok | 4.7 | 0.0 | 1.14 |
| (information) `leaves_size` | ok | 5.2 | 0.0 | 1.14 |
| (information) `L0_outside` | ok | 13.8 | 9.0 | 2.19 |
| (information) `L2_X` | killed: memory > 9 GB | 53.2 | 0.0 | 9.03 |
| (information) `L2_count` | ok | 5.2 | 0.0 | 1.14 |
| (information) `L2_sum` | ok | 6.2 | 0.5 | 1.18 |
| (information) `L2_lam` | ok | 6.7 | 1.1 | 1.24 |
| (information) `L2_obs` | ok | 5.0 | 0.1 | 1.14 |
| (information) `L2_mu` | ok | 6.0 | 0.1 | 1.14 |
| (information) `O2_faces` | ok | 5.3 | 0.0 | 1.14 |
| (information) `L2_face0` | killed: memory > 9 GB | 41.2 | 0 | 9.02 |

No proof obtained.
Axioms of the `native_decide` proof: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

## Stages — `scenes/S6_iiwa_real_shelf.cert.json`

| stage | result | wall s | kernel s | peak GB |
|---|---|---|---|---|
| `assumptions` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 49.4 | 0.0 | 2.7 |
| … 33 later stage(s) | not needed: the proof already fails; one stage of each other kind probed below | | | |
| (information) `conditionI` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 49.5 | 1.3 | 2.79 |
| (information) `partition` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 83.2 | 0.0 | 2.7 |
| (information) `kinematics` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 83.4 | 0.3 | 2.7 |
| (information) `geometry_eq` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 83.5 | 0.0 | 2.7 |
| (information) `slab_eq` | killed: memory > 9 GB | 120.1 | 0.0 | 9.03 |
| (information) `lamDeg_eq` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 86.3 | 0.0 | 2.7 |
| (information) `leaves_size` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 85.1 | 0.0 | 2.7 |
| (information) `L0_X` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 84.3 | 0.0 | 2.7 |
| (information) `L0_count` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 82.9 | 0.0 | 2.7 |
| (information) `L0_sum` | killed: memory > 9 GB | 122.2 | 0.0 | 9.02 |
| (information) `L0_lam` | killed: memory > 9 GB | 117.6 | 0.0 | 9.02 |
| (information) `L0_obs` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 78.2 | 0.1 | 2.7 |
| (information) `L0_mu` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 81.4 | 0.0 | 2.7 |
| (information) `O0_faces` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 76.6 | 0.0 | 2.7 |
| (information) `L0_face0` | error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 78.1 | 0.0 | 2.7 |

No proof obtained.
Axioms of the `native_decide` proof: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

