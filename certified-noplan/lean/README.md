# CnpVerify — a Lean 4 checker for certified-noplan certificates

`lake exe cnp-verify <cert.json>` re-checks a disconnection certificate (SPEC §4) in exact
rational arithmetic and prints `PROOF …` (exit code 0) or `REJECT [code] reason` (exit code 1).
It is a port of `src/cnp/verify.py`, which remains the specification and is untouched.

**Status (L2): executable, partly proved — soundness is NOT proved yet.** The checker runs and
agrees with `verify.py`. The 19 theorems it is meant to satisfy are stated in Lean and listed in
[PROOF-OBLIGATIONS.md](PROOF-OBLIGATIONS.md). Ten are proved: the tensor arithmetic computes
the polynomial operations it claims (T1–T7), the Bernstein test implies non-negativity on the
box (B0, B1), the tiling test implies that the leaves cover the box (C1). Nine are still
`sorry`: the kinematics (K1–K4), the two leaf checks (C2, C3), the bridge to the reference
kinematics (C4) and the main statements (S1 `soundness`, S2 `soundness_ref`). The proofs are
about the executable code as it was delivered in L1: it has not been modified.

## Layout

| file | content | imports |
|---|---|---|
| `CnpVerify/Tensor.lean` | dense rational coefficient tensors, `add` / `mul` / `scale` / `padTo?` / `evalQ` | core Lean |
| `CnpVerify/Bernstein.lean` | exact Bernstein transform over a box, `bernsteinCoeffs`, `allNonneg` | core Lean |
| `CnpVerify/Kinematics.lean` | serial revolute chain, `Joint.homog`, `bodyNumerators`, `bodyDenominator` | core Lean |
| `CnpVerify/Certificate.lean` | `Certificate`, JSON parser, `describe` | core Lean |
| `CnpVerify/Check.lean` | the checks, in the order of `verify.py`; `check : Certificate → Bool` | core Lean |
| `Main.lean` | the `cnp-verify` executable | core Lean |
| `CnpVerify/Spec/Index.lean` | the flat layout: `flatIndex`, `encode` / `decode`, loops as folds — proved | Mathlib |
| `CnpVerify/Spec/Tensor.lean` | `Tensor.eval` over `ℝ` (noncomputable) and its algebra, T1–T7 — proved | Mathlib |
| `CnpVerify/Spec/Bernstein.lean` | `Box.toSet`, `binom_eq_choose`, `bernstein_nonneg` — proved | Mathlib |
| `CnpVerify/Spec/Kinematics.lean` | reference kinematics over `ℝ`, `body_position` — statements (`sorry`) | Mathlib |
| `CnpVerify/Soundness.lean` | `CollisionFree`; `verifyCover_covers` proved; `soundness` — statement (`sorry`) | Mathlib |

The executable core imports nothing but core Lean, so the binary does not link Mathlib; the
specification layer imports the core and Mathlib. This is why the real-valued `eval` and the
statements sit in `Spec/` files next to the modules they are about, rather than inside them.

## Build and run

Lean and Mathlib are pinned (`lean-toolchain`, `lake-manifest.json`). With
[elan](https://github.com/leanprover/elan) installed:

```
cd lean
lake exe cache get        # prebuilt Mathlib (several GB); only needed for the Spec layer
lake build                # executable + library (9 `declaration uses sorry` warnings)
lake exe cnp-verify ../scenes/S6_iiwa_real_shelf.cert.json
```

`lake build cnp-verify` alone builds the executable in a few seconds and needs no Mathlib cache.
Options: `--json` (one JSON object: verdict, reason code, leaf and face index, time) and
`--dump` (print the certificate as parsed).

## Parity with `verify.py`

`make lean-parity` (from `certified-noplan/`) builds everything, exports the adversarial corpus
from the Python test-suite mutations (`scripts/export_mutations.py`) and compares both verifiers
(`scripts/lean_parity.py`) on every shipped certificate, on the corpus (verdict and reason), and
on a seeded differential fuzz (verdict).

## Where the Lean checker is stricter than `verify.py`

`verify.py` reads the JSON lazily while checking; the Lean checker parses the whole document
into a typed `Certificate` first. On well-formed certificates the two agree. On ill-formed
ones the Lean checker rejects (`malformed`) inputs that `verify.py` accepts or aborts on:

* a number written as a non-integer JSON number, a JSON boolean, or with non-ASCII digits
  (the schema says numbers are strings; `Fraction` happens to accept those);
* an unparsable value in a field `verify.py` never reads (an obstacle no leaf refers to, the
  `cos`/`sin` of a locked joint downstream of the body);
* `start_s` / `goal_s` shorter than `n`, a box or a cell with more than `n` intervals;
* a negative `body.link`, a lock on a joint that does not exist, a duplicated exponent key.

For a certificate with several defects the *reason* reported can differ (the parser runs
before the checks). None of these makes the Lean checker accept something `verify.py` rejects.
