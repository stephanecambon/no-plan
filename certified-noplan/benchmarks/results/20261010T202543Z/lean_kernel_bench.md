# Lean kernel bench on a quiet machine — 20261010T202543Z

- commit `1d9fa5eaaec0e3e93d638cf916397fc3b2cfab29` (tree dirty: False)
- Lean (version 4.34.1, arm64-apple-darwin24.6.0, commit 5045d0056413266e57c625dcd7c365b10e377c52, Release); Mathlib `v4.34.1`
- Darwin 25.5.0 arm64, Apple M4, 10 cores, 24 GiB, macOS 26.5.1
- `uptime` before: `22:29  up  5:07, 2 users, load averages: 1.43 2.17 2.78`
- `uptime` after:  `22:34  up  5:12, 2 users, load averages: 2.72 2.43 2.71`
- limits per process: 1800 s, 9 GiB resident (1 GiB = 2^30 bytes)
- failures documented in runs 20261010T163223Z and 20261010T171636Z, not re-run: `by decide` and `by decide +kernel` in one evaluation on the three certificates, the staged kernel proof on S3 and S6

| certificate | n | leaves (collision / outside) | staged kernel proof (`decide +kernel` per stage), whole file | `native_decide` (one axiom more) |
|---|---|---|---|---|
| `scenes/wall/k3.cert.json` | 3 | 2 (2 / 0) | 102.8 s (kernel 101.6 s), peak 5.63 GiB, 34 stages | 0.9 s (evaluation 0.045 s), peak 0.89 GiB |
| `scenes/S3_shoulder_elbow.cert.json` | 4 | 8 (4 / 4) | not re-run (FAIL in L4) | 0.9 s (evaluation 0.139 s), peak 1.04 GiB |
| `scenes/S6_iiwa_real_shelf.cert.json` | 7 | 2 (2 / 0) | not re-run (FAIL in L4) | 8.2 s (evaluation 7.37 s), peak 1.13 GiB |

Wall-clock figures include loading the imports (0.9 s, 0.9 s, 0.9 s).

## Stages — `scenes/wall/k3.cert.json`, one process each

| stage | result | wall s | kernel s | peak GiB |
|---|---|---|---|---|
| `assumptions` | ok | 0.9 | 0.002 | 1.09 |
| `conditionI` | ok | 0.9 | 0.009 | 1.07 |
| `partition` | ok | 0.9 | 0.005 | 1.08 |
| `kinematics` | ok | 0.9 | 0.004 | 1.09 |
| `geometry_eq` | ok | 13.3 | 12.5 | 5.61 |
| `slab_eq` | ok | 0.9 | 0.107 | 1.04 |
| `lamDeg_eq` | ok | 0.9 | 0 | 1.09 |
| `leaves_size` | ok | 0.9 | 0 | 1.06 |
| `L0_X` | ok | 4.5 | 3.65 | 2.56 |
| `L0_count` | ok | 0.9 | 0 | 1.04 |
| `L0_sum` | ok | 0.9 | 0.048 | 1.07 |
| `L0_lam` | ok | 0.9 | 0.082 | 1.06 |
| `L0_obs` | ok | 0.9 | 0.008 | 1.08 |
| `L0_mu` | ok | 0.9 | 0 | 1.06 |
| `O0_faces` | ok | 0.9 | 0 | 1.06 |
| `L0_face0` | ok | 7.9 | 7.01 | 3.8 |
| `L0_face1` | ok | 7.9 | 7.07 | 3.77 |
| `L0_face2` | ok | 6.2 | 5.36 | 3.26 |
| `L0_face3` | ok | 8.3 | 7.28 | 3.82 |
| `L0_face4` | ok | 8.1 | 7.1 | 3.79 |
| `L0_face5` | ok | 6.3 | 5.34 | 3.26 |
| `L1_X` | ok | 4.6 | 3.66 | 2.56 |
| `L1_count` | ok | 0.9 | 0 | 1.03 |
| `L1_sum` | ok | 0.9 | 0.046 | 1.06 |
| `L1_lam` | ok | 0.9 | 0.082 | 1.04 |
| `L1_obs` | ok | 0.9 | 0.008 | 0.83 |
| `L1_mu` | ok | 0.9 | 0 | 1.06 |
| `O1_faces` | ok | 0.9 | 0 | 1.07 |
| `L1_face0` | ok | 8.5 | 7.49 | 3.98 |
| `L1_face1` | ok | 8.3 | 7.25 | 3.85 |
| `L1_face2` | ok | 6.6 | 5.5 | 3.31 |
| `L1_face3` | ok | 8.5 | 7.53 | 4.0 |
| `L1_face4` | ok | 8.1 | 7.12 | 3.83 |
| `L1_face5` | ok | 6.5 | 5.53 | 3.31 |

Axioms of the staged proof: ['propext', 'Classical.choice', 'Quot.sound']

Axioms of `by native_decide` on `scenes/wall/k3.cert.json`: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

Axioms of `by native_decide` on `scenes/S3_shoulder_elbow.cert.json`: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

Axioms of `by native_decide` on `scenes/S6_iiwa_real_shelf.cert.json`: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

## What the kernel pays for the array operations of the checker

`by decide +kernel` on one operation over an array of N naturals; kernel seconds.

| operation | N = 125 | N = 625 | ratio |
|---|---|---|---|
| `for i in [0:N] (sum)` | 0.006 | 0.031 | ×5 |
| `List.range N |>.foldl` | 0.003 | 0.013 | ×4 |
| `Array.set! then getD` | 0.010 | 0.054 | ×5 |
| `Array.foldl` | 0.228 | 6.780 | ×30 |
| `Array.all` | 0.232 | 6.770 | ×29 |
| `Array.map` | 0.126 | 4.080 | ×32 |
| `Array.ofFn` | 0.118 | 4.030 | ×34 |
| `Array ==` | 0.465 | 14.100 | ×30 |
| `Array ++` | 0.410 | 13.000 | ×32 |

