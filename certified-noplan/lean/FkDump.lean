/-
FkDump — control script (L3), NOT a build target and not part of the library.

  lake env lean --run FkDump.lean <cert.json>...

For each certificate, prints the exact rational value of the common denominator `D` and of the
world position `N_k / D` of every body vertex, at three fixed rational configurations (all
variables nonzero and distinct). `scripts/lean_fk_parity.py` compares this output, value for
value, with the same quantities computed by `verify.py`'s own forward kinematics.

Why: K2 (`body_position`) proves that the reference kinematics `linkPose` equals this `N/D`.
Exact equality of `N/D` with `verify.py` therefore says that the Lean REFERENCE and the Python
forward kinematics (itself matched to Drake in S10-bis) are the same function at these points.
-/
import CnpVerify.Check

open CnpVerify

/-- Configuration number `p`: `s_i = ± (i+1)/(p+3+2i)`, signs alternating. -/
def fkPoint (n p : Nat) : Fin n → Rat := fun i =>
  let v : Rat := ((i.val + 1 : Nat) : Rat) / ((p + 3 + 2 * i.val : Nat) : Rat)
  if (i.val + p) % 2 == 0 then v else -v

def main (args : List String) : IO UInt32 := do
  for path in args do
    let text ← IO.FS.readFile path
    match Lean.Json.parse text with
    | .error e => IO.println s!"{path} JSONERR {e}"
    | .ok j =>
      match Certificate.ofJson j with
      | .error r => IO.println s!"{path} PARSEERR {r.code}"
      | .ok c =>
        let geo := c.geometry
        for p in [0, 1, 2] do
          let x := fkPoint c.n p
          let d := geo.den.evalQ x
          IO.println s!"{path} p{p} D {ratToString d}"
          for k in [0:geo.verts.size] do
            let v := geo.verts.getD k (Vector.replicate 3 Tensor.zero)
            for r in List.finRange 3 do
              IO.println s!"{path} p{p} v{k} {r.val} {ratToString (v[r].evalQ x / d)}"
  return 0
