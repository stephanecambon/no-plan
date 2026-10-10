/-
CertTermCheck — control script (L4), NOT a build target and not part of a library.

  lake env lean --run CertTermCheck.lean <repository root>

For every certificate written as a Lean term by `scripts/cert_to_lean.py` (`Certs/*.lean`),
reads the JSON file it was generated from, parses it with `Certificate.ofJson` — the parser of
the `cnp-verify` binary — and checks that the object obtained is EQUAL to the term (decidable
equality on every field, tensors compared as stored: degree and coefficient array), then that
`checkE` gives the same outcome on both. Exit code 0 iff every pair agrees.

Why: the per-scene theorems of `Certs/` are about the TERMS. This script says that a term is
the object the binary checks when given the JSON file. It is a run-time check (interpreted
code), not a proof: `Lean.Json.parse` is a `partial` function, which the kernel cannot unfold.
The generator and the Lean parser are two independent readers of the same file.
-/
import Certs.WallK3
import Certs.S3ShoulderElbow
import Certs.S6IiwaRealShelf

open CnpVerify

deriving instance DecidableEq for Tensor, Joint, Face, Obstacle, LeafKind, Leaf, Certificate

/-- (JSON file, relative to the repository root; the generated term). Keep in step with
`TARGETS` of `scripts/cert_to_lean.py`. -/
def pairs : List (String × Certificate) := [
  ("scenes/wall/k3.cert.json", Certs.wallK3),
  ("scenes/S3_shoulder_elbow.cert.json", Certs.s3ShoulderElbow),
  ("scenes/S6_iiwa_real_shelf.cert.json", Certs.s6IiwaRealShelf)]

def verdict (r : Except Reject Unit) : String :=
  match r with
  | .ok _ => "PROOF"
  | .error e => s!"REJECT [{e.code}]"

def main (args : List String) : IO UInt32 := do
  let [root] := args
    | do IO.eprintln "usage: lake env lean --run CertTermCheck.lean <repository root>"; return 2
  let mut bad := 0
  for (rel, term) in pairs do
    let text ← IO.FS.readFile (System.FilePath.mk root / rel)
    match Lean.Json.parse text >>= fun j => (Certificate.ofJson j).mapError (·.msg) with
    | .error e =>
      IO.println s!"{rel}: NOT PARSED ({e})"
      bad := bad + 1
    | .ok c =>
      let same := decide (c = term)
      let vJson := verdict (checkE c)
      let vTerm := verdict (checkE term)
      IO.println s!"{rel}: parsed object = term: {same}; checkE on the parsed object: {vJson}; on the term: {vTerm}"
      if !same || vJson != vTerm then bad := bad + 1
  if bad == 0 then
    IO.println s!"OK: {pairs.length} certificates, parsed object = generated term on every one"
    return 0
  else
    IO.println s!"MISMATCH on {bad} certificate(s)"
    return 1
