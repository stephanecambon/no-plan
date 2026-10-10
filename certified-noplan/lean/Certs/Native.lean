/-
Certs.Native — `check c = true` by `native_decide` (L4). Core Lean only (no Mathlib).

THE COUNTERPART of `Certs/WallK3Kernel.lean`, kept for comparison. `native_decide` does not ask
the kernel to evaluate `check c`: it compiles the term, runs the compiled code, and — when the
answer is `true` — ADDS AN AXIOM stating `decide (check c = true) = true`. In Lean 4.34 this is
one fresh axiom per use, named `<theorem>._native.native_decide.ax_…` (`Lean/Meta/Native.lean`;
earlier versions used the single axiom `Lean.ofReduceBool`). `#print axioms` shows it.

So a statement proved here holds PROVIDED the compiler, the interpreter and the run-time
library (`Nat`, `Int`, `Array`, `String` primitives in C) compute what the definitions say:
the same trust as running the `cnp-verify` binary, minus the JSON parser. That is exactly the
gap the kernel evaluation closes for `wallK3`. Nothing in `CnpVerify/` and no statement cited
as a theorem of Lean/Mathlib depends on this file.
-/
import Certs.WallK3
import Certs.S3ShoulderElbow
import Certs.S6IiwaRealShelf

namespace CnpVerify.Certs

/-- `check wallK3 = true`, by compiled evaluation (one extra axiom). Compare `wallK3_proof`. -/
theorem wallK3_proof_native : check wallK3 = true := by native_decide

/-- `check s3ShoulderElbow = true`, by compiled evaluation (one extra axiom). -/
theorem s3ShoulderElbow_proof_native : check s3ShoulderElbow = true := by native_decide

/-- `check s6IiwaRealShelf = true`, by compiled evaluation (one extra axiom). -/
theorem s6IiwaRealShelf_proof_native : check s6IiwaRealShelf = true := by native_decide

end CnpVerify.Certs
