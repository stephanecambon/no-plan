# Kernel evaluation — 20261010T172639Z

- commit `278428007805c60b39c15dcf7ea4b47963c5b4c4` (tree dirty at start: False)
- Lean (version 4.34.1, arm64-apple-darwin24.6.0, commit 5045d0056413266e57c625dcd7c365b10e377c52, Release)
- Darwin 25.5.0 arm64, Apple M4; load average at start [5.31, 5.38, 5.48]

## What the kernel pays for the array operations of the checker

`by decide +kernel` on one operation over an array of N naturals; kernel seconds.

| operation | N = 125 | N = 625 | ratio |
|---|---|---|---|
| `for i in [0:N] (sum)` | 0.026 | 0.157 | ×6 |
| `List.range N |>.foldl` | 0.011 | 0.055 | ×5 |
| `Array.set! then getD` | 0.046 | 0.228 | ×5 |
| `Array.foldl` | 0.793 | 21.800 | ×27 |
| `Array.all` | 0.843 | 21.200 | ×25 |
| `Array.map` | 0.478 | 12.800 | ×27 |
| `Array.ofFn` | 0.482 | 12.200 | ×25 |
| `Array ==` | 1.560 | 44.600 | ×29 |
| `Array ++` | 1.300 | 38.500 | ×30 |

