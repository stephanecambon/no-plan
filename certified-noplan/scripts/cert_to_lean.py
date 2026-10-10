#!/usr/bin/env python3
"""L4 — write a disconnection certificate (SPEC §4 JSON) as a Lean TERM of type ``Certificate``.

    .venv/bin/python scripts/cert_to_lean.py            # regenerate every file of TARGETS
    .venv/bin/python scripts/cert_to_lean.py --check    # exit 1 if a committed file is stale
    .venv/bin/python scripts/cert_to_lean.py <cert.json> <defName> <out.lean>

Why: the soundness theorem of ``lean/CnpVerify/Soundness.lean`` is about the Lean term
``check``. To evaluate ``check c`` INSIDE THE KERNEL (``by decide``), ``c`` must be a term; the
JSON parser cannot be run there (``Lean.Json.parse`` is a ``partial`` function, opaque to the
kernel). This script is the second, independent reader of the JSON: it follows the same
reading rules as ``Certificate.ofJson`` (``lean/CnpVerify/Certificate.lean``) — fields read,
``Fraction`` grammar of the numbers, obstacles and polynomial terms in sorted key order,
storage degree of a polynomial = largest exponent LISTED — and ``lean/CertTermCheck.lean``
then checks that the parser's object and the generated term are EQUAL.

The script only transcribes: it checks nothing about the certificate, imports nothing from
``src/`` (stdlib only), and refuses any document it cannot transcribe faithfully.

Rationals are written ``(a : Rat) / b`` (``Rat`` is ``ℚ``; the generated files are core Lean,
without Mathlib), integers as numerals, polynomials as ``Tensor.ofTerms deg #[(exponents,
coefficient), …]`` — the very call the parser makes.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (certificate, Lean definition name, generated file) — paths relative to the repository root.
TARGETS = [
    ("scenes/wall/k3.cert.json", "wallK3", "lean/Certs/WallK3.lean"),
    ("scenes/S3_shoulder_elbow.cert.json", "s3ShoulderElbow", "lean/Certs/S3ShoulderElbow.lean"),
    ("scenes/S6_iiwa_real_shelf.cert.json", "s6IiwaRealShelf", "lean/Certs/S6IiwaRealShelf.lean"),
]

_SAFE = re.compile(r"[A-Za-z0-9_ .:+\-]*\Z")


class Untranscribable(ValueError):
    """The document cannot be written as a term (the Lean parser would reject it, or the script
    does not cover the case)."""


def _no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Untranscribable(f"duplicate JSON key {k!r}")
        out[k] = v
    return out


def rat(x, what: str) -> Fraction:
    """A rational field: a ``Fraction`` string, or a JSON integer literal."""
    if isinstance(x, bool):
        raise Untranscribable(f"{what}: boolean where a rational is expected")
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, str):
        try:
            return Fraction(x)
        except (ValueError, ZeroDivisionError) as e:
            raise Untranscribable(f"{what}: invalid rational {x!r}") from e
    raise Untranscribable(f"{what}: expected a rational string or an integer")


def nat(x, what: str) -> int:
    """A natural-number field: a JSON integer literal or an integer string, >= 0."""
    if isinstance(x, bool) or not isinstance(x, (int, str)):
        raise Untranscribable(f"{what}: expected an integer")
    try:
        v = int(x)
    except ValueError as e:
        raise Untranscribable(f"{what}: invalid integer {x!r}") from e
    if v < 0:
        raise Untranscribable(f"{what}: negative integer")
    return v


def lean_str(s, what: str) -> str:
    if not isinstance(s, str) or not _SAFE.match(s):
        raise Untranscribable(f"{what}: string {s!r} outside the plain-ASCII subset")
    return f'"{s}"'


def lean_rat(q: Fraction) -> str:
    if q.denominator == 1:
        return str(q.numerator) if q.numerator >= 0 else f"({q.numerator})"
    return f"({q.numerator} : Rat) / {q.denominator}"


def lean_vec(qs) -> str:
    return "#v[" + ", ".join(lean_rat(q) for q in qs) + "]"


def vec3(x, what: str):
    if not isinstance(x, list) or len(x) != 3:
        raise Untranscribable(f"{what}: expected 3 entries")
    return [rat(v, what) for v in x]


def box(x, n: int, what: str):
    if not isinstance(x, list) or len(x) != n:
        raise Untranscribable(f"{what}: expected {n} intervals")
    out = []
    for p in x:
        if not isinstance(p, list) or len(p) != 2:
            raise Untranscribable(f"{what}: an interval must be [lo, hi]")
        out.append((rat(p[0], what), rat(p[1], what)))
    return out


def lean_box(b) -> str:
    return "#v[" + ", ".join(f"({lean_rat(lo)}, {lean_rat(hi)})" for lo, hi in b) + "]"


def tensor(x, n: int, what: str) -> str:
    """``{"e0,e1,…": coeff}`` -> ``Tensor.ofTerms deg #[…]``, terms in sorted key order, storage
    degree = largest exponent listed (zero coefficients included), as the Lean parser does."""
    if not isinstance(x, dict):
        raise Untranscribable(f"{what}: expected an object")
    terms, seen, deg = [], set(), 0
    for key in sorted(x):
        if key == "":
            e = (0,) * n
        else:
            try:
                e = tuple(int(t) for t in key.split(","))
            except ValueError as err:
                raise Untranscribable(f"{what}: invalid exponent key {key!r}") from err
        if any(v < 0 for v in e):
            raise Untranscribable(f"{what}: negative exponent in {key!r}")
        if len(e) != n:
            raise Untranscribable(f"{what}: exponent arity mismatch in {key!r}")
        if e in seen:
            raise Untranscribable(f"{what}: exponent {key!r} listed twice")
        seen.add(e)
        deg = max([deg, *e])
        terms.append((e, rat(x[key], what)))
    body = ", ".join(f"(#[{', '.join(map(str, e))}], {lean_rat(c)})" for e, c in terms)
    return f"Tensor.ofTerms {deg} #[{body}]"


def chain(robot) -> list:
    kind = robot.get("kind")
    if kind == "planar_revolute":
        free, prev = [], Fraction(0)
        for ln in robot["link_lengths"]:
            free.append(([prev, Fraction(0), Fraction(0)], [Fraction(0), Fraction(0), Fraction(1)]))
            prev = rat(ln, "robot.link_lengths")
    elif kind == "spatial_revolute":
        free = [(vec3(j["offset"], "joint offset"), vec3(j["axis"], "joint axis"))
                for j in robot["joints"]]
    else:
        raise Untranscribable(f"unsupported robot kind {kind!r}")
    locks = {}
    for key, val in sorted((robot.get("locked_joints") or {}).items()):
        idx = nat(key, "locked joint index")
        if idx >= len(free) or idx in locks:
            raise Untranscribable(f"locked joint index {key!r} out of range or repeated")
        locks[idx] = (rat(val["cos"], "locked cos"), rat(val["sin"], "locked sin"))
    out = []
    for i, (offset, axis) in enumerate(free):
        lock = "none" if i not in locks else \
            f"some ({lean_rat(locks[i][0])}, {lean_rat(locks[i][1])})"
        out.append(f"{{ offset := {lean_vec(offset)}, axis := {lean_vec(axis)}, locked := {lock} }}")
    return out


def obstacle(name: str, o) -> str:
    rows, bs = o["A"], o["b"]
    if not isinstance(rows, list) or not isinstance(bs, list) or len(rows) != len(bs):
        raise Untranscribable(f"malformed obstacle {name!r}")
    faces = [f"{{ a := {lean_vec(vec3(r, 'obstacle A'))}, b := {lean_rat(rat(b, 'obstacle b'))} }}"
             for r, b in zip(rows, bs)]
    inner = ",\n        ".join(faces)
    return f"{{ name := {lean_str(name, 'obstacle name')}, faces := #[\n        {inner}] }}"


def leaf(lf, n: int) -> str:
    cell = lean_box(box(lf["cell"], n, "leaf cell"))
    status = lf["status"]
    if status == "outside":
        kind = ".outside"
    elif status == "collision":
        lam = ",\n          ".join(tensor(t, n, "lambda") for t in lf["lambda"])
        mu = ", ".join(lean_rat(rat(m, "leaf mu")) for m in lf["mu"])
        kind = (f".collision {lean_str(lf['obstacle'], 'leaf obstacle')}\n"
                f"        #[{lam}]\n        #[{mu}]")
    else:
        kind = f".undecided {lean_str(status, 'leaf status')}"
    return f"{{ cell := {cell},\n      kind := {kind} }}"


def render(cert_rel: str, name: str) -> str:
    path = os.path.join(ROOT, cert_rel)
    raw = open(path, "rb").read()
    d = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
                   parse_float=lambda s: (_ for _ in ()).throw(Untranscribable(f"float literal {s}")))
    if d.get("theorem") != "disconnection":
        raise Untranscribable("not a disconnection certificate")
    if d["kinematics"]["substitution"] != "half_angle_homemade_v1":
        raise Untranscribable("unknown kinematic substitution")
    robot = d["robot"]
    n = nat(robot["n"], "robot.n")
    start = [rat(v, "start_s") for v in d["start_s"]][:n]
    goal = [rat(v, "goal_s") for v in d["goal_s"]][:n]
    if len(start) != n or len(goal) != n:
        raise Untranscribable("start_s / goal_s: fewer than n entries")
    lam_deg = {"const": "some 0", "affine": "some 1", "quadratic": "some 2"}.get(
        d.get("lam_degree") if isinstance(d.get("lam_degree"), str) else None, "none")
    joints = ",\n    ".join(chain(robot))
    hull = ",\n    ".join(lean_vec(vec3(v, "hull vertex")) for v in d["body"]["hull_vertices"])
    obstacles = ",\n    ".join(obstacle(k, d["obstacles"][k]) for k in sorted(d["obstacles"]))
    leaves = ",\n    ".join(leaf(lf, n) for lf in d["leaves"])
    q_star = ", ".join(lean_rat(rat(v, "robot.q_star")) for v in robot["q_star"])
    return f"""/-
GENERATED by scripts/cert_to_lean.py — DO NOT EDIT (regenerate: `python scripts/cert_to_lean.py`).

Source : {cert_rel}
sha256 : {hashlib.sha256(raw).hexdigest()}

The certificate as a Lean term, field for field what `Certificate.ofJson` reads from the JSON
file (`lean/CertTermCheck.lean` checks that the two objects are equal). Core Lean only: this
file does not import Mathlib. Nothing is proved here.
-/
import CnpVerify.Check

namespace CnpVerify.Certs

def {name} : Certificate where
  n := {n}
  chain := #[
    {joints}]
  qStar := #[{q_star}]
  bodyLink := {nat(d["body"]["link"], "body.link")}
  hull := #[
    {hull}]
  obstacles := #[
    {obstacles}]
  phi := {tensor(d["phi"]["coeffs"], n, "phi")}
  phiDeg := {nat(d["phi"]["degree_per_var"], "phi.degree_per_var")}
  delta := {lean_rat(rat(d["delta"], "delta"))}
  box := {lean_box(box(d["box"], n, "box"))}
  sStart := {lean_vec(start)}
  sGoal := {lean_vec(goal)}
  lamDeg := {lam_deg}
  leaves := #[
    {leaves}]

end CnpVerify.Certs
"""


def main(argv) -> int:
    if len(argv) == 3:
        cert, name, out = argv
        text = render(os.path.relpath(os.path.abspath(cert), ROOT), name)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {out}")
        return 0
    if argv not in ([], ["--check"]):
        print(__doc__)
        return 2
    stale = 0
    for cert, name, out in TARGETS:
        text = render(cert, name)
        dest = os.path.join(ROOT, out)
        if argv == ["--check"]:
            ok = os.path.exists(dest) and open(dest, encoding="utf-8").read() == text
            print(f"{'up to date' if ok else 'STALE     '}  {out}  <-  {cert}")
            stale += not ok
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"wrote {out}  <-  {cert}  ({len(text.splitlines())} lines)")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
