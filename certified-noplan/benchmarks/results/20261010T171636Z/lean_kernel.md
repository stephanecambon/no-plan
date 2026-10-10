# Kernel evaluation of `check c` — 20261010T171636Z

- commit `ca2123a07938e612ce51c8c588db697069c92904` (tree dirty at start: False)
- Lean (version 4.34.1, arm64-apple-darwin24.6.0, commit 5045d0056413266e57c625dcd7c365b10e377c52, Release); Mathlib `v4.34.1`
- Darwin 25.5.0 arm64, Apple M4; load average at start [4.11, 4.97, 5.59]
- limits per process: 900 s, 9 GiB resident (1 GiB = 2^30 bytes)

| certificate | n | leaves (collision / outside) | body vertices | `decide` | `decide +kernel`, one evaluation | staged kernel proof | `native_decide` (adds an axiom) |
|---|---|---|---|---|---|---|---|
| `scenes/S6_iiwa_real_shelf.cert.json` | 7 | 2 (2 / 0) | 40 | FAIL (reduction stuck at `match check s6IiwaRealShelf, true with`; already on the first test `¬ (s6IiwaRealShelf.delta ≤ 0)`: reduction stuck at `match Rat.blt 0 s6IiwaRealShelf.delta, false with`) | FAIL (killed, memory > 9 GiB, after 48 s) | FAIL at stage 5/34 `geometry_eq` (elaboration error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached); 4 stages passed in 1 s of kernel | 26.3 s (evaluation 24 s), 1.1 GiB |

Wall-clock figures include loading the imports (2.4 s).

## Stages — `scenes/S6_iiwa_real_shelf.cert.json`

| stage | result | wall s | kernel s | peak GiB |
|---|---|---|---|---|
| `assumptions` | ok | 2.4 | 0.0 | 1.09 |
| `conditionI` | ok | 3.3 | 1.0 | 1.23 |
| `partition` | ok | 2.1 | 0.0 | 1.05 |
| `kinematics` | ok | 2.4 | 0.1 | 1.11 |
| `geometry_eq` | elaboration error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 28.0 | 0 | 1.76 |
| … 29 later stage(s) | not needed: the proof already fails; one stage of each other kind probed below | | | |
| (information) `slab_eq` | killed: memory > 9 GiB | 47.5 | 0 | 9.02 |
| (information) `lamDeg_eq` | ok | 2.1 | 0 | 1.06 |
| (information) `leaves_size` | ok | 2.1 | 0 | 1.03 |
| (information) `L0_X` | elaboration error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 46.1 | 0 | 2.19 |
| (information) `L0_count` | elaboration error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 25.6 | 0.0 | 1.76 |
| (information) `L0_sum` | killed: memory > 9 GiB | 48.5 | 0 | 9.04 |
| (information) `L0_lam` | killed: memory > 9 GiB | 50.3 | 0 | 9.01 |
| (information) `L0_obs` | ok | 2.4 | 0.0 | 1.09 |
| (information) `L0_mu` | ok | 2.1 | 0.0 | 1.04 |
| (information) `O0_faces` | ok | 2.4 | 0 | 1.04 |
| (information) `L0_face0` | elaboration error: (deterministic) timeout at `isDefEq`, maximum number of heartbeats (200000) has been reached | 55.2 | 0.0 | 2.23 |

No proof obtained.
Axioms of the `native_decide` proof: ['propext', 'Classical.choice', 'Quot.sound', 't._native.native_decide.ax_1']

## What the kernel pays for the array operations of the checker

`by decide +kernel` on one operation over an array of N naturals; kernel seconds.

| operation | N = 125 | N = 625 | ratio |
|---|---|---|---|
| `for i in [0:N] (sum)` | 0.000 | 0.100 |  |
| `List.range N |>.foldl` | 0.000 | 0.100 |  |
| `Array.set! then getD` | 0.000 | 0.200 |  |
| `Array.foldl` | 0.700 | 20.600 | ×29 |
| `Array.all` | 0.800 | 20.100 | ×25 |
| `Array.map` | 0.400 | 8.400 | ×21 |
| `Array.ofFn` | 0.200 | 5.900 | ×30 |
| `Array ==` | 0.700 | 21.100 | ×30 |
| `Array ++` | 1.500 | 40.900 | ×27 |

