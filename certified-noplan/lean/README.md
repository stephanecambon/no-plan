# CnpVerify — a Lean 4 checker for certified-noplan certificates

`lake exe cnp-verify <cert.json>` re-checks a disconnection certificate (SPEC §4) in exact
rational arithmetic and prints `PROOF …` (exit code 0) or `REJECT [code] reason` (exit code 1).
It is a port of `src/cnp/verify.py`, which remains the specification and is untouched.

**Status (L3): executable and proved.** The checker runs and agrees with `verify.py`, and the
19 theorems stated in L1 are proved ([PROOF-OBLIGATIONS.md](PROOF-OBLIGATIONS.md)); `lake build`
reports no `sorry`. The main statement, `soundness_ref` (`CnpVerify/Soundness.lean`):

```lean
theorem soundness_ref (c : Certificate) :
    check c = true →
      ¬ ∃ γ : C(unitInterval, Fin c.n → ℝ),
          (∀ t, γ t ∈ c.box.toSet) ∧ γ 0 = vecR c.sStart ∧ γ 1 = vecR c.sGoal
            ∧ ∀ t, CollisionFreeRef c (γ t)
```

If the checker accepts a certificate, no continuous path inside the joint box joins the start to
the goal while the certified body, moved by real rigid motions along the declared chain, stays
out of every obstacle. The proofs are about the executable code as it was delivered in L1: it
has not been modified. **What this does and does not establish is spelled out in
[Trust base](#trust-base) below — read it before quoting the theorem.**

## Layout

| file | content | imports |
|---|---|---|
| `CnpVerify/Tensor.lean` | dense rational coefficient tensors, `add` / `mul` / `scale` / `padTo?` / `evalQ` | core Lean |
| `CnpVerify/Bernstein.lean` | exact Bernstein transform over a box, `bernsteinCoeffs`, `allNonneg` | core Lean |
| `CnpVerify/Kinematics.lean` | serial revolute chain, `Joint.homog`, `bodyNumerators`, `bodyDenominator` | core Lean |
| `CnpVerify/Certificate.lean` | `Certificate`, JSON parser, `describe` | core Lean |
| `CnpVerify/Check.lean` | the checks, in the order of `verify.py`; `check : Certificate → Bool` | core Lean |
| `Main.lean` | the `cnp-verify` executable | core Lean |
| `CnpVerify/Spec/Index.lean` | the flat layout: `flatIndex`, `encode` / `decode`, loops as folds | Mathlib |
| `CnpVerify/Spec/Tensor.lean` | `Tensor.eval` over `ℝ` (noncomputable) and its algebra, T1–T7 | Mathlib |
| `CnpVerify/Spec/Bernstein.lean` | `Box.toSet`, `binom_eq_choose`, `bernstein_nonneg` (B0, B1) | Mathlib |
| `CnpVerify/Spec/Kinematics.lean` | reference kinematics over `ℝ` (`linkPose`), K1–K4 | Mathlib |
| `CnpVerify/Soundness.lean` | `CollisionFree`, `CollisionFreeRef`; C1–C4; `soundness`, `soundness_ref` | Mathlib |

The executable core imports nothing but core Lean, so the binary does not link Mathlib; the
specification layer imports the core and Mathlib. This is why the real-valued `eval` and the
statements sit in `Spec/` files next to the modules they are about, rather than inside them.

## Build and run

Lean and Mathlib are pinned (`lean-toolchain`, `lake-manifest.json`). With
[elan](https://github.com/leanprover/elan) installed:

```
cd lean
lake exe cache get        # prebuilt Mathlib (several GB); only needed for the Spec layer
lake build                # executable + library with all the proofs (no `sorry`, no warning)
lake exe cnp-verify ../scenes/S6_iiwa_real_shelf.cert.json
```

`lake build cnp-verify` alone builds the executable in a few seconds and needs no Mathlib cache.
Options: `--json` (one JSON object: verdict, reason code, leaf and face index, time) and
`--dump` (print the certificate as parsed).

## Trust base

What one relies on when taking a `PROOF` printed by `cnp-verify` as a proof.

### Proved — checked by the Lean kernel

* **S2 `soundness_ref`** (above) and **S1 `soundness`** (the same statement on the polynomial
  pair `(N, D)` the checker computes), from: the tensor arithmetic computes the polynomial
  operations it claims (T1–T7); non-negative Bernstein coefficients imply non-negativity on the
  box (B0, B1); an accepted tiling covers the box (C1); an accepted `outside` leaf has
  `|φ| ≥ δ` on its cell (C2); an accepted `collision` leaf is in collision wherever `|φ| ≤ δ` on
  its cell (C3); the common denominator is positive (K1); the polynomial kinematics `N/D` IS the
  reference kinematics (K2, C4); the rational parametrisation `s = tan (q/2)` gives the rotation
  of angle `q` (K3), and Rodrigues' matrix is a rotation for a unit axis (K4).
* `#print axioms soundness` and `#print axioms soundness_ref`: `propext`, `Classical.choice`,
  `Quot.sound` — the three standard axioms, nothing else.
* Not among the 19, also proved: `check_eq_true_iff` (`check c = true` iff the sequence of
  checks `checkE c` succeeds, which is what the executable reports);
  `linkPose_rot_mem_specialOrthogonal` (under the kinematic check, the rotation part of the
  reference pose is in `SO(3)`); `skewR_mulVec`, `rodrigues_mulVec` (the reference rotation is
  `v ↦ v + sin · a × v + (1 - cos) · a × (a × v)`, with Mathlib's cross product).

### Defined — to be read

A proof shows that the checker agrees with the definitions the statement is written with; it
does not show that these definitions say what a roboticist means. They are short, contain no
polynomial and do not mention the checker. For `soundness_ref`:

| definition | file | what it says |
|---|---|---|
| `Certificate`, `Joint`, `Face`, `Obstacle`, `Vec3`, `Box` | `Certificate.lean`, `Kinematics.lean`, `Bernstein.lean` | the data. The statement reads `n`, `chain`, `bodyLink`, `hull`, `obstacles`, `box`, `sStart`, `sGoal` only: `φ`, `δ`, the leaves and their multipliers are the material of the proof, not part of the claim |
| `Box.toSet` | `Spec/Bernstein.lean` | `{x \| ∀ i, loᵢ ≤ xᵢ ≤ hiᵢ}` |
| `vecR` | `Spec/Kinematics.lean` | a rational vector seen in `ℝᵐ` |
| `Obstacle.toSet` | `Soundness.lean` | `{y ∈ ℝ³ \| ∀ faces, aᵀ y ≤ b}` (closed) |
| `CollisionFreeRef` | `Soundness.lean` | for every obstacle, the convex hull of the moved body vertices is disjoint from it |
| `Rigid`, `Rigid.apply`, `Rigid.comp` | `Spec/Kinematics.lean` | `y ↦ R y + t` and composition |
| `skew`, `skewR`, `rodrigues` | `Kinematics.lean`, `Spec/Kinematics.lean` | `K = [a]×` and `I + sin · K + (1 - cos) · K²` |
| `Joint.rotation` | `Spec/Kinematics.lean` | unlocked joint: `rodrigues` at `cos = (1-s²)/(1+s²)`, `sin = 2s/(1+s²)`; locked joint: at its rational `(cos, sin)` |
| `RefState`, `refStep`, `linkPose` | `Spec/Kinematics.lean` | `pose ← pose ∘ translate(offset) ∘ rotate`, along joints `0..link`; the `k`-th unlocked joint reads `s_k` |

plus Mathlib's `convexHull`, `Disjoint`, `C(unitInterval, ·)`, `Matrix` and `ℝ`. `soundness`
(S1) reads, instead of `linkPose`, the checker's own `bodyNumerators` / `bodyDenominator`
through `Tensor.eval` — which is why S2 is the statement to quote.

Things the statement says, and things it does not:

* It is a statement in **`s`-space** (`s = tan (q/2)`, as in the certificate): the path, the box,
  the start and the goal are in `s`. The translation of a path in joint angles (inside
  `(-π, π)`) into a path in `s` is not formalised. The field `q_star` does not occur in the
  statement; the checker requires it to be zero, which is what makes `s = tan (q/2)` the right
  reading of the certificate.
* It is about **one body and the listed obstacles**, exact polytopes, static. A path that is
  collision-free for the whole robot is collision-free for that body, so the conclusion
  extends to the robot; the converse is not claimed.
* **Touching is a collision** (obstacles are closed sets).
* If the start or the goal is outside the box, the statement is vacuously true.
* It is **soundness only**. Nothing says the checker accepts every true disconnection, nor
  anything about the program that produced the certificate.

### Outside the statement — trusted, not proved

* **Parsing.** The theorem is about a value of type `Certificate`. `Certificate.ofJson` (JSON
  file → `Certificate`) is ordinary unverified code; `cnp-verify --dump` prints the object that
  was actually checked. That the certificate describes the intended scene and robot (YAML
  scene, URDF) is not a matter for this checker at all.
* **Compilation and run time.** The theorem is about `check` as a Lean term. The binary is what
  the Lean compiler and the C toolchain make of it: the compiler, the run-time arithmetic
  (`Nat`, `Int`, `Rat` on GMP), `Array` and the `@[extern]` / `@[implemented_by]` replacements
  of core library functions are trusted. (Planned, L4: evaluate `check` inside the kernel on a
  small certificate.)
* **`Main.lean`**: file reading and printing. It prints `PROOF` exactly when `checkE c`
  succeeds.
* **The proof checker itself**: the Lean 4.34.1 kernel, and Mathlib `v4.34.1` for the
  definitions of `ℝ`, continuity, convex hulls, matrices.

Agreement with `verify.py` is **measured**, not proved (next section).

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
