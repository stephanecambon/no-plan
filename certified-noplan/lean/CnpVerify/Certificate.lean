/-
CnpVerify.Certificate — the certificate as a typed object, and its JSON parser (L1, executable).

The JSON schema is SPEC §4. `verify.py` reads the JSON lazily, field by field, while it checks;
here the document is first parsed into a typed `Certificate` (the object the soundness theorem
talks about), then checked (`CnpVerify/Check.lean`). Only the fields `verify.py` reads are
parsed (`checks`, `stats`, `pairs`, `assumptions`, `margin`, `phi.n`, `spec_version` are
ignored, as there). Numbers follow the grammar of Python's `fractions.Fraction(str)`:
`"num/den"`, integers, and decimal strings such as `"-0.8"` (the cells of the shipped
certificates are decimal strings).
-/
import Lean.Data.Json
import CnpVerify.Bernstein
import CnpVerify.Kinematics

namespace CnpVerify

open Lean (Json)

/-- A rejection: a stable machine-readable `code`, the leaf and the face/vertex index it is
about when there is one, and a human-readable message. -/
structure Reject where
  code : String
  leaf : Option Nat := none
  index : Option Nat := none
  msg : String
  deriving Repr

/-- One face `aᵀ y ≤ b` of an obstacle. -/
structure Face where
  a : Vec3
  b : Rat

/-- A static obstacle in H-representation: `{y ∈ ℝ³ | ∀ faces, aᵀ y ≤ b}`. -/
structure Obstacle where
  name : String
  faces : Array Face

/-- What a leaf claims. `collision` names ONE obstacle and carries the witness multipliers:
one polynomial `λ_k` per body vertex and one constant `μ_j ≥ 0` per obstacle face. Any other
status is kept as `undecided` and is rejected by the checker. -/
inductive LeafKind (n : Nat) where
  | outside
  | collision (obstacle : String) (lam : Array (Tensor n)) (mu : Array Rat)
  | undecided (status : String)

/-- A leaf of the partition: a sub-box of the box and its claim. -/
structure Leaf (n : Nat) where
  cell : Box n
  kind : LeafKind n

/-- A disconnection certificate (SPEC §4), in exact rationals. -/
structure Certificate where
  /-- Number of unlocked joints = number of variables `s₀..s_{n-1}`. -/
  n : Nat
  /-- The serial chain, all joints in order (locked ones included). -/
  chain : Array Joint
  /-- Reference configuration of the unlocked joints; the checker requires it to be zero. -/
  qStar : Array Rat
  /-- Index (in `chain`) of the link carrying the certified body. -/
  bodyLink : Nat
  /-- Vertices of the certified body (a convex polytope), in the frame of `bodyLink`. -/
  hull : Array Vec3
  /-- The obstacles, by name. -/
  obstacles : Array Obstacle
  /-- The barrier polynomial `φ`. -/
  phi : Tensor n
  /-- DECLARED per-variable degree of `φ` (fixes the Bernstein degrees). -/
  phiDeg : Nat
  /-- Half-width `δ` of the slab `{|φ| ≤ δ}`. -/
  delta : Rat
  /-- The joint box `P` in `s`-space. -/
  box : Box n
  /-- Start and goal configurations in `s`-space. -/
  sStart : Vector Rat n
  sGoal : Vector Rat n
  /-- Per-variable degree of the multipliers `λ_k` (`const` 0, `affine` 1, `quadratic` 2);
  `none` when the field is absent or unknown. -/
  lamDeg : Option Nat
  /-- The leaves, in file order. -/
  leaves : Array (Leaf n)

/-! ### Printing -/

/-- `num/den` (or `num` for an integer). -/
def ratToString (q : Rat) : String :=
  if q.den == 1 then toString q.num else s!"{q.num}/{q.den}"

def vecToString {m : Nat} (v : Vector Rat m) : String :=
  "(" ++ ", ".intercalate (v.toList.map ratToString) ++ ")"

def boxToString {n : Nat} (b : Box n) : String :=
  " x ".intercalate (b.toList.map fun (lo, hi) => s!"[{ratToString lo}, {ratToString hi}]")

/-- A polynomial as a sum of monomials `c*s^(e₀,…)`. -/
def Tensor.toStr {n : Nat} (t : Tensor n) : String :=
  let terms := t.support.toList.map fun (e, c) =>
    s!"{ratToString c}*s^({", ".intercalate (e.toList.map toString)})"
  if terms.isEmpty then "0" else " + ".intercalate terms

/-- What was parsed, in readable form (to re-read the typed object against the JSON). -/
def Certificate.describe (c : Certificate) : String := Id.run do
  let mut out := s!"certificate: n = {c.n}, {c.chain.size} joints, body on link {c.bodyLink} "
    ++ s!"({c.hull.size} vertices), {c.obstacles.size} obstacle(s), {c.leaves.size} leaves\n"
  for h : j in [0:c.chain.size] do
    let jt := c.chain[j]
    let lock := match jt.locked with
      | none => "free"
      | some (co, si) => s!"LOCKED cos={ratToString co} sin={ratToString si}"
    out := out ++ s!"  joint {j}: offset {vecToString jt.offset} axis {vecToString jt.axis} {lock}\n"
  out := out ++ s!"  q_star = [{", ".intercalate (c.qStar.toList.map ratToString)}]\n"
  for v in c.hull do
    out := out ++ s!"  body vertex {vecToString v}\n"
  for o in c.obstacles do
    out := out ++ s!"  obstacle {o.name}: {o.faces.size} faces\n"
    for f in o.faces do
      out := out ++ s!"    {vecToString f.a} . y <= {ratToString f.b}\n"
  out := out ++ s!"  phi = {c.phi.toStr}   (declared degree {c.phiDeg})\n"
  out := out ++ s!"  delta = {ratToString c.delta}\n"
  out := out ++ s!"  box = {boxToString c.box}\n"
  out := out ++ s!"  s_start = {vecToString c.sStart}   s_goal = {vecToString c.sGoal}\n"
  out := out ++ s!"  lambda degree = {c.lamDeg}\n"
  for h : i in [0:c.leaves.size] do
    let lf := c.leaves[i]
    let kind := match lf.kind with
      | .outside => "outside"
      | .collision o lam mu =>
        s!"collision vs {o}: lambda = [{"; ".intercalate (lam.toList.map Tensor.toStr)}], "
          ++ s!"mu = [{", ".intercalate (mu.toList.map ratToString)}]"
      | .undecided s => s!"UNDECIDED status {s}"
    out := out ++ s!"  leaf {i}: {boxToString lf.cell} {kind}\n"
  return out

instance : ToString Certificate := ⟨Certificate.describe⟩

/-! ### Parsing -/

/-- Parser monad: a typed value or a rejection. -/
abbrev ParseM := Except Reject

def malformed {α : Type} (msg : String) : ParseM α :=
  throw { code := "malformed", msg := s!"malformed certificate ({msg})" }

private def natOfDigits (ds : List Char) : Nat :=
  ds.foldl (fun acc ch => acc * 10 + (ch.toNat - '0'.toNat)) 0

private def dropSpaces (cs : List Char) : List Char := cs.dropWhile Char.isWhitespace

/-- Longest prefix matching Python's `\d+(_\d+)*` (digits, single `_` allowed BETWEEN digits),
returned without the separators, and the rest. -/
private def spanDigits (cs : List Char) : List Char × List Char :=
  let rec go (fuel : Nat) (acc rest : List Char) : List Char × List Char :=
    match fuel, rest with
    | fuel + 1, '_' :: d :: tail =>
      if d.isDigit && !acc.isEmpty then
        let (ds, tail') := (d :: tail).span Char.isDigit
        go fuel (acc ++ ds) tail'
      else (acc, rest)
    | _, _ => (acc, rest)
  let (ds, rest) := cs.span Char.isDigit
  go cs.length ds rest

/-- Rational from a string, following the grammar of Python's `Fraction(str)`: optional sign,
then `digits [/ digits]` or `digits [. digits] [e[±]digits]` (a leading `.digits` is allowed),
surrounding whitespace ignored, `_` allowed between digits. `none` on anything else, and on a
zero denominator. -/
def parsePyFraction (s : String) : Option Rat :=
  let cs := dropSpaces s.toList
  let (neg, cs) := match cs with
    | '-' :: r => (true, r)
    | '+' :: r => (false, r)
    | _ => (false, cs)
  let sign : Rat := if neg then -1 else 1
  let (intDs, rest) := spanDigits cs
  let slash := dropSpaces rest
  match slash with
  | '/' :: r =>
    let (denDs, tail) := spanDigits (dropSpaces r)
    if intDs.isEmpty || denDs.isEmpty || !(dropSpaces tail).isEmpty then none
    else if natOfDigits denDs == 0 then none
    else some (sign * mkRat (natOfDigits intDs) (natOfDigits denDs))
  | _ =>
    let (fracDs, rest1) := match rest with
      | '.' :: r => spanDigits r
      | _ => ([], rest)
    if intDs.isEmpty && fracDs.isEmpty then none else
    let mant : Rat := mkRat (natOfDigits (intDs ++ fracDs)) (10 ^ fracDs.length)
    match rest1 with
    | 'e' :: r | 'E' :: r =>
      let (eneg, r) := match r with
        | '-' :: t => (true, t)
        | '+' :: t => (false, t)
        | _ => (false, r)
      let (expDs, tail) := spanDigits r
      if expDs.isEmpty || !(dropSpaces tail).isEmpty then none
      else
        let p : Rat := (10 : Rat) ^ natOfDigits expDs
        some (sign * (if eneg then mant / p else mant * p))
    | _ => if (dropSpaces rest1).isEmpty then some (sign * mant) else none

/-- Integer from a string: optional sign and digits, surrounding whitespace ignored. -/
def parsePyInt (s : String) : Option Int :=
  let cs := dropSpaces s.toList
  let (neg, cs) := match cs with
    | '-' :: r => (true, r)
    | '+' :: r => (false, r)
    | _ => (false, cs)
  let (ds, tail) := spanDigits cs
  if ds.isEmpty || !(dropSpaces tail).isEmpty then none
  else some (if neg then -(natOfDigits ds : Int) else (natOfDigits ds : Int))

/-- A rational field: a `Fraction`-string, or a JSON integer literal. -/
def ratOfJson (what : String) (j : Json) : ParseM Rat :=
  match j with
  | .str s => match parsePyFraction s with
    | some q => pure q
    | none => malformed s!"{what}: invalid rational {s.quote}"
  | .num ⟨m, 0⟩ => pure (m : Rat)
  | _ => malformed s!"{what}: expected a rational string or an integer"

/-- A natural-number field: a JSON integer literal or an integer string, `≥ 0`. -/
def natOfJson (what : String) (j : Json) : ParseM Nat := do
  let i : Int ← match j with
    | .num ⟨m, 0⟩ => pure m
    | .str s => match parsePyInt s with
      | some i => pure i
      | none => malformed s!"{what}: invalid integer {s.quote}"
    | _ => malformed s!"{what}: expected an integer"
  if i < 0 then malformed s!"{what}: negative integer" else pure i.toNat

def field (j : Json) (key : String) : ParseM Json :=
  match j.getObjVal? key with
  | .ok v => pure v
  | .error _ => malformed s!"missing field {key.quote}"

def arrOfJson (what : String) (j : Json) : ParseM (Array Json) :=
  match j with
  | .arr a => pure a
  | _ => malformed s!"{what}: expected a list"

def strOfJson (what : String) (j : Json) : ParseM String :=
  match j with
  | .str s => pure s
  | _ => malformed s!"{what}: expected a string"

def objEntries (what : String) (j : Json) : ParseM (List (String × Json)) :=
  match j with
  | .obj kvs => pure kvs.toList
  | _ => malformed s!"{what}: expected an object"

def ratArray (what : String) (j : Json) : ParseM (Array Rat) := do
  (← arrOfJson what j).mapM (ratOfJson what)

def vectorOfArray {α : Type} (what : String) (m : Nat) (a : Array α) : ParseM (Vector α m) :=
  if h : a.size = m then pure ⟨a, h⟩
  else malformed s!"{what}: expected {m} entries, got {a.size}"

def vec3OfJson (what : String) (j : Json) : ParseM Vec3 := do
  vectorOfArray what 3 (← ratArray what j)

/-- A box: a list of `n` pairs `[lo, hi]`. -/
def boxOfJson (what : String) (n : Nat) (j : Json) : ParseM (Box n) := do
  let pairs ← (← arrOfJson what j).mapM fun p => do
    let lohi ← ratArray what p
    if h : lohi.size = 2 then pure (lohi[0], lohi[1])
    else malformed s!"{what}: an interval must be [lo, hi]"
  vectorOfArray what n pairs

/-- A sparse tensor `{"e0,e1,…": "coeff"}` (the empty key is the constant term). The storage
degree is the largest exponent LISTED, zero coefficients included — `verify.py` tests the
degree of a multiplier `λ_k` on its listed keys. -/
def tensorOfJson (what : String) (n : Nat) (j : Json) : ParseM (Tensor n) := do
  let mut terms : Array (Array Nat × Rat) := #[]
  for (key, val) in ← objEntries what j do
    let e : Array Nat ←
      if key.isEmpty then pure (Array.replicate n 0)
      else (key.splitOn ",").toArray.mapM fun x =>
        match parsePyInt x with
        | some i =>
          if i < 0 then malformed s!"{what}: negative exponent in {key.quote}" else pure i.toNat
        | none => malformed s!"{what}: invalid exponent key {key.quote}"
    if e.size ≠ n then
      throw { code := "arity_mismatch", msg := "phi/lambda exponent arity mismatch" }
    if terms.any (fun (e', _) => e' == e) then
      malformed s!"{what}: exponent {key.quote} listed twice"
    terms := terms.push (e, ← ratOfJson what val)
  return Tensor.ofTerms (Tensor.maxDeg (Tensor.varDegsOf n terms)) terms

/-- The chain of `robot`: `planar_revolute` (axes `+z`, joint `i` offset by the previous link
length along `x`) or `spatial_revolute` (explicit offsets and axes), with the locks attached. -/
def chainOfJson (robot : Json) : ParseM (Array Joint) := do
  let kind ← strOfJson "robot.kind" (← field robot "kind")
  let free : Array (Vec3 × Vec3) ←
    if kind == "planar_revolute" then do
      let lens ← ratArray "robot.link_lengths" (← field robot "link_lengths")
      let mut out := #[]
      let mut prev : Rat := 0
      for ln in lens do
        out := out.push ((#v[prev, 0, 0] : Vec3), (#v[0, 0, 1] : Vec3))
        prev := ln
      pure out
    else if kind == "spatial_revolute" then do
      (← arrOfJson "robot.joints" (← field robot "joints")).mapM fun jt => do
        let axis ← vec3OfJson "joint axis" (← field jt "axis")
        let offset ← vec3OfJson "joint offset" (← field jt "offset")
        pure (offset, axis)
    else
      throw { code := "unsupported_kind", msg := s!"unsupported robot kind {kind.quote}" }
  let lockJson := match robot.getObjVal? "locked_joints" with
    | .ok .null => Json.mkObj []
    | .ok v => v
    | .error _ => Json.mkObj []
  let mut locks : Array (Nat × (Rat × Rat)) := #[]
  for (key, val) in ← objEntries "robot.locked_joints" lockJson do
    let idx ← natOfJson "locked joint index" (.str key)
    if idx ≥ free.size then malformed s!"locked joint index {idx} out of range"
    if locks.any (fun (i, _) => i == idx) then malformed s!"joint {idx} locked twice"
    let c ← ratOfJson "locked cos" (← field val "cos")
    let s ← ratOfJson "locked sin" (← field val "sin")
    locks := locks.push (idx, (c, s))
  return free.mapIdx fun i (offset, axis) =>
    { offset, axis, locked := (locks.find? (fun (k, _) => k == i)).map (·.2) }

def obstacleOfJson (name : String) (j : Json) : ParseM Obstacle := do
  let bad : ParseM Obstacle :=
    throw { code := "malformed_obstacle", msg := s!"malformed obstacle {name.quote}" }
  let rows ← arrOfJson "obstacle A" (← field j "A")
  let bs ← arrOfJson "obstacle b" (← field j "b")
  if rows.size ≠ bs.size then bad else
  let mut faces := #[]
  for h : i in [0:rows.size] do
    let row ← arrOfJson "obstacle row" rows[i]
    if row.size ≠ 3 then return ← bad
    let a ← vectorOfArray "obstacle row" 3 (← row.mapM (ratOfJson "obstacle A"))
    faces := faces.push { a, b := ← ratOfJson "obstacle b" (bs.getD i .null) : Face }
  return { name, faces }

def leafOfJson (n : Nat) (j : Json) : ParseM (Leaf n) := do
  let cell ← boxOfJson "leaf cell" n (← field j "cell")
  let status ← strOfJson "leaf status" (← field j "status")
  if status == "outside" then return { cell, kind := .outside }
  if status == "collision" then
    let lam ← (← arrOfJson "leaf lambda" (← field j "lambda")).mapM (tensorOfJson "lambda" n)
    let obstacle ← strOfJson "leaf obstacle" (← field j "obstacle")
    let mu ← ratArray "leaf mu" (← field j "mu")
    return { cell, kind := .collision obstacle lam mu }
  return { cell, kind := .undecided status }

/-- Parse a certificate. The two format gates of `verify.py` come first (`theorem` must be
`"disconnection"`, the kinematic substitution must be the one re-implemented here), then the
typed content. -/
def Certificate.ofJson (j : Json) : ParseM Certificate := do
  match j.getObjVal? "theorem" with
  | .ok (.str "disconnection") => pure ()
  | _ => throw { code := "not_disconnection", msg := "not a disconnection certificate" }
  match (← field (← field j "kinematics") "substitution") with
  | .str "half_angle_homemade_v1" => pure ()
  | _ => throw { code := "unknown_substitution", msg := "unknown kinematic substitution" }
  let delta ← ratOfJson "delta" (← field j "delta")
  let robot ← field j "robot"
  let n ← natOfJson "robot.n" (← field robot "n")
  let obstacles ← (← objEntries "obstacles" (← field j "obstacles")).toArray.mapM
    fun (name, o) => obstacleOfJson name o
  let phiJ ← field j "phi"
  let phiDeg ← natOfJson "phi.degree_per_var" (← field phiJ "degree_per_var")
  let phi ← tensorOfJson "phi" n (← field phiJ "coeffs")
  let box ← boxOfJson "box" n (← field j "box")
  let start ← ratArray "start_s" (← field j "start_s")
  let goal ← ratArray "goal_s" (← field j "goal_s")
  let sStart ← vectorOfArray "start_s" n (start.extract 0 n)
  let sGoal ← vectorOfArray "goal_s" n (goal.extract 0 n)
  let leafJsons ← arrOfJson "leaves" (← field j "leaves")
  let qStar ← ratArray "robot.q_star" (← field robot "q_star")
  let chain ← chainOfJson robot
  let body ← field j "body"
  let bodyLink ← natOfJson "body.link" (← field body "link")
  let hull ← (← arrOfJson "body.hull_vertices" (← field body "hull_vertices")).mapM
    (vec3OfJson "hull vertex")
  let lamDeg : Option Nat := match j.getObjVal? "lam_degree" with
    | .ok (.str "const") => some 0
    | .ok (.str "affine") => some 1
    | .ok (.str "quadratic") => some 2
    | _ => none
  let leaves ← leafJsons.mapM (leafOfJson n)
  return { n, chain, qStar, bodyLink, hull, obstacles, phi, phiDeg, delta, box, sStart, sGoal,
           lamDeg, leaves }

end CnpVerify
