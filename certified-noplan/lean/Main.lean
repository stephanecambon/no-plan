/-
cnp-verify — executable checker of disconnection certificates (L1).

  cnp-verify [--json] [--dump] <cert.json>

Prints `PROOF …` (exit code 0) or `REJECT [code] reason` (exit code 1), then the time spent
parsing and checking. `--json` prints one JSON object instead (for the parity harness);
`--dump` first prints the certificate as parsed.
-/
import CnpVerify.Check

open CnpVerify

/-- Outcome of a run: the parsed certificate when parsing succeeded, and the verdict. -/
def runFile (path : System.FilePath) : IO (Option Certificate × Except Reject Unit) := do
  let text ← IO.FS.readFile path
  match Lean.Json.parse text with
  | .error e =>
    return (none, .error { code := "malformed", msg := s!"malformed certificate (invalid JSON: {e})" })
  | .ok j =>
    match Certificate.ofJson j with
    | .error r => return (none, .error r)
    | .ok c => return (some c, checkE c)

def proofMessage (c : Certificate) : String :=
  let nCol := (c.leaves.filter fun lf => match lf.kind with | .collision .. => true | _ => false).size
  let nOut := (c.leaves.filter fun lf => match lf.kind with | .outside => true | _ => false).size
  s!"PROOF verified exactly: {c.leaves.size} leaves ({nCol} collision, {nOut} outside); "
    ++ s!"start/goal separated by the slab |phi| <= {ratToString c.delta}."

def optNat : Option Nat → Lean.Json
  | some k => (k : Lean.Json)
  | none => Lean.Json.null

def main (args : List String) : IO UInt32 := do
  let (flags, files) := args.partition (·.startsWith "--")
  let [path] := files
    | do IO.eprintln "usage: cnp-verify [--json] [--dump] <cert.json>"; return 2
  let t0 ← IO.monoNanosNow
  let (cert?, res) ← runFile path
  let ms := ((← IO.monoNanosNow) - t0) / 1000000
  if flags.contains "--dump" then
    match cert? with
    | some c => IO.print c.describe
    | none => IO.println "(certificate not parsed)"
  let json := flags.contains "--json"
  match res, cert? with
  | .ok _, some c =>
    if json then
      IO.println (Lean.Json.mkObj [("ok", true), ("code", Lean.Json.null), ("leaf", Lean.Json.null),
        ("index", Lean.Json.null), ("message", proofMessage c), ("ms", ms)]).compress
    else
      IO.println (proofMessage c)
      IO.println s!"time: {ms} ms"
    return 0
  | .ok _, none => IO.eprintln "internal error: verdict without certificate"; return 2
  | .error r, _ =>
    let whereStr := match r.leaf with
      | some i => s!" [leaf {i}]"
      | none => ""
    if json then
      IO.println (Lean.Json.mkObj [("ok", false), ("code", r.code), ("leaf", optNat r.leaf),
        ("index", optNat r.index), ("message", s!"verify: {r.msg}"), ("ms", ms)]).compress
    else
      IO.println s!"REJECT [{r.code}] verify: {r.msg}{whereStr}"
      IO.println s!"time: {ms} ms"
    return 1
