"""L1 — parity of the Lean checker ``cnp-verify`` with the Python verifier ``cnp.verify``.

Runs both on (a) every certificate shipped in ``scenes/`` and ``scenes/wall/`` and (b) the
adversarial corpus written by ``scripts/export_mutations.py``, and compares:

  * the VERDICT (PROOF / REJECT) — any difference is a divergence, exit code 1;
  * for a rejection, the REASON: the Python message is mapped to the stable code the Lean
    checker prints (table ``PY_CODES``), and the leaf index and face / vertex index are compared
    whenever the Python message carries them.

Both tools are timed on the shipped certificates: ``verify_file`` in this process, the Lean
binary by its own clock (parse + check, process start-up excluded) and by wall clock.

``--fuzz N`` adds (c) a seeded DIFFERENTIAL FUZZ: N random single mutations of small valid
certificates (multipliers, geometry, barrier, partition, number spelling, garbage). The gate
is the verdict: a certificate accepted by one tool and rejected by the other is a divergence —
except the one documented asymmetry, counted and listed apart: the Lean parser reads the whole
document before checking, so it rejects as ``malformed`` a certificate whose defect sits in a
field ``verify.py`` never reads. A Python exception (``verify.py`` can still abort on
ill-formed input) is not an acceptance: Lean must reject.

Usage:  .venv/bin/python scripts/lean_parity.py --bin lean/.lake/build/bin/cnp-verify \
            --mutations <dir written by export_mutations.py> [--markdown] [--fuzz N --seed S]
"""
from __future__ import annotations

import argparse
import ast
import copy
import glob
import json
import os
import random
import re
import subprocess
import sys
import time
from fractions import Fraction as F

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cnp import verify  # noqa: E402  (stdlib-only module)

# Python message (regex, anchored at the start) -> Lean reason code.
PY_CODES = [
    (r"verify: not a disconnection certificate", "not_disconnection"),
    (r"verify: unknown kinematic substitution", "unknown_substitution"),
    (r"verify: delta must be > 0", "delta_nonpos"),
    (r"verify: degenerate box bound", "degenerate_box"),
    (r"verify: malformed obstacle", "malformed_obstacle"),
    (r"verify: phi\(s_start\) is not < -delta", "cond_i_start"),
    (r"verify: phi\(s_goal\) is not > \+delta", "cond_i_goal"),
    (r"verify: empty partition", "empty_partition"),
    (r"verify: leaf cell does not match its region", "tiling_leaf_mismatch"),
    (r"verify: cells do not tile the box", "tiling_not_bisection"),
    (r"verify: nonzero q_star", "qstar_nonzero"),
    (r"verify: spatial joint axis is not a unit vector", "axis_not_unit"),
    (r"verify: unsupported robot kind", "unsupported_kind"),
    (r"verify: robot n disagrees", "n_mismatch"),
    (r"verify: locked joint cos\^2\+sin\^2 != 1", "lock_not_unit"),
    (r"verify: 'outside' leaf", "outside_not_disjoint"),
    (r"verify: lambda count", "lambda_count"),
    (r"verify: sum_k lambda_k != 1", "lambda_sum"),
    (r"verify: lambda_(\d+) is not >= 0", "lambda_negative"),
    (r"verify: mu count", "mu_count"),
    (r"verify: mu_(\d+) < 0", "mu_negative"),
    (r"verify: face (\d+) of ", "face_not_certified"),
    (r"verify: undecided leaf status", "leaf_status"),
    (r"polynomial degree exceeds the declared Bernstein degree", "degree_exceeds"),
    (r"verify: phi/lambda exponent arity mismatch", "arity_mismatch"),
    (r"verify: malformed certificate", "malformed"),
]


def classify(msg: str, cert) -> tuple:
    """(code, leaf index or None, face/vertex index or None) of a Python rejection message."""
    code = index = None
    for pattern, c in PY_CODES:
        m = re.match(pattern, msg)
        if m:
            code = c
            index = int(m.group(1)) if m.groups() else None
            break
    leaf = None
    m = re.search(r"leaf (\[\[.*?\]\])", msg)
    if m and isinstance(cert, dict):
        cell = ast.literal_eval(m.group(1))
        leaf = next((i for i, lf in enumerate(cert.get("leaves", []))
                     if lf.get("cell") == cell), None)
    return code, leaf, index


def run_lean(binary: str, path: str) -> tuple:
    t0 = time.perf_counter()
    proc = subprocess.run([binary, "--json", path], capture_output=True, text=True)
    wall = time.perf_counter() - t0
    if proc.returncode not in (0, 1):
        raise SystemExit(f"cnp-verify failed on {path} (exit {proc.returncode}): {proc.stderr}")
    out = json.loads(proc.stdout)
    if out["ok"] != (proc.returncode == 0):
        raise SystemExit(f"cnp-verify: exit code and verdict disagree on {path}")
    return out, wall


def run_python(path: str) -> tuple:
    with open(path) as f:
        cert = json.load(f)
    t0 = time.perf_counter()
    ok, msg = verify.verify(cert)
    return ok, msg, time.perf_counter() - t0, cert


def compare(path: str, binary: str) -> dict:
    ok, msg, t_py, cert = run_python(path)
    lean, wall = run_lean(binary, path)
    row = {"file": os.path.relpath(path, _REPO) if path.startswith(_REPO) else os.path.basename(path),
           "python_ok": ok, "lean_ok": lean["ok"], "python_s": t_py, "lean_s": lean["ms"] / 1000.0,
           "lean_wall_s": wall, "python_message": msg, "lean_message": lean["message"]}
    row["verdict_match"] = ok == lean["ok"]
    if ok:
        row["python_reason"] = row["lean_reason"] = "PROOF"
        row["reason_match"] = lean["ok"]
    else:
        code, leaf, index = classify(msg, cert)
        row["python_reason"] = _fmt(code, leaf, index)
        row["lean_reason"] = _fmt(lean["code"], lean["leaf"], lean["index"])
        row["reason_match"] = (
            code is not None and code == lean["code"]
            and (leaf is None or leaf == lean["leaf"])
            and (index is None or index == lean["index"]))
    return row


def _fmt(code, leaf, index) -> str:
    out = str(code)
    if leaf is not None:
        out += f" leaf={leaf}"
    if index is not None:
        out += f" idx={index}"
    return out


# --------------------------------------------------------------------------- #
# Differential fuzz (seeded): one random mutation of a valid certificate per case
# --------------------------------------------------------------------------- #

def _eps(rng) -> F:
    """A rational perturbation: mostly tiny, sometimes large, either sign."""
    mag = rng.choice([F(1, 10 ** 9), F(1, 10 ** 6), F(1, 1000), F(1, 100), F(1, 10), F(1), F(7)])
    return mag * rng.choice([-1, 1]) * rng.randint(1, 9)


def _collision(rng, c):
    return rng.choice([lf for lf in c["leaves"] if lf["status"] == "collision"])


def _respell(rng, v: str) -> str:
    """The SAME rational, written differently (all spellings Fraction() accepts)."""
    q = F(v)
    forms = [f"{q.numerator}/{q.denominator}", f" {q.numerator}/{q.denominator} ",
             f"+{q}" if q >= 0 else str(q), f"{q.numerator * 3}/{q.denominator * 3}",
             f"{q.numerator} / {q.denominator}", f"{q.numerator}e0/{q.denominator}"]
    if q.denominator in (1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40, 50, 64, 80, 100):
        from decimal import Decimal
        d = Decimal(q.numerator) / Decimal(q.denominator)
        forms += [str(d), f"{d}e0", f"{d * 10}E-1", f"{q.numerator * 100 // q.denominator}e-2"
                  if (q.numerator * 100) % q.denominator == 0 else str(d)]
    return rng.choice(forms)


def _numeric_slots(c):
    """Every (container, key) holding a rational string the verifier may read."""
    slots = [(c, "delta")]
    for name in ("start_s", "goal_s"):
        slots += [(c[name], i) for i in range(len(c[name]))]
    for pair in c["box"]:
        slots += [(pair, 0), (pair, 1)]
    slots += [(c["phi"]["coeffs"], k) for k in c["phi"]["coeffs"]]
    for v in c["body"]["hull_vertices"]:
        slots += [(v, i) for i in range(3)]
    for obs in c["obstacles"].values():
        slots += [(row, i) for row in obs["A"] for i in range(3)]
        slots += [(obs["b"], i) for i in range(len(obs["b"]))]
    r = c["robot"]
    slots += [(r["q_star"], i) for i in range(len(r["q_star"]))]
    slots += [(r["link_lengths"], i) for i in range(len(r["link_lengths"]))]
    for jt in r.get("joints", []):
        slots += [(jt["axis"], i) for i in range(3)] + [(jt["offset"], i) for i in range(3)]
    for lk in (r.get("locked_joints") or {}).values():
        slots += [(lk, "cos"), (lk, "sin")]
    for lf in c["leaves"]:
        for pair in lf["cell"]:
            slots += [(pair, 0), (pair, 1)]
        if lf["status"] == "collision":
            slots += [(lf["mu"], i) for i in range(len(lf["mu"]))]
            slots += [(lam, k) for lam in lf["lambda"] for k in lam]
    return slots


def _m_mu(rng, c):
    lf = _collision(rng, c)
    j = rng.randrange(len(lf["mu"]))
    lf["mu"][j] = str(rng.choice([F(0), F(lf["mu"][j]) + _eps(rng), F(lf["mu"][j]) * rng.choice(
        [F(1, 2), F(99, 100), F(101, 100), F(2)])]))


def _m_lambda_pair(rng, c):
    """Move mass between two vertices: keeps sum_k lambda_k == 1 exactly."""
    lf = _collision(rng, c)
    a, b = rng.sample(range(len(lf["lambda"])), 2)
    key = rng.choice(list(lf["lambda"][a]))
    e = _eps(rng) / 100
    lf["lambda"][a][key] = str(F(lf["lambda"][a][key]) + e)
    lf["lambda"][b][key] = str(F(lf["lambda"][b].get(key, "0")) - e)


def _m_lambda_one(rng, c):
    lf = _collision(rng, c)
    lam = rng.choice(lf["lambda"])
    key = rng.choice(list(lam))
    lam[key] = str(F(lam[key]) + _eps(rng))


def _m_lambda_new_term(rng, c):
    """Add a term of degree 0..3 in one variable (may exceed the declared lambda degree)."""
    lf = _collision(rng, c)
    n = int(c["robot"]["n"])
    e = [0] * n
    e[rng.randrange(n)] = rng.randint(0, 3)
    key = ",".join(map(str, e))
    a, b = rng.sample(range(len(lf["lambda"])), 2)
    v = rng.choice([F(0), _eps(rng) / 1000])
    lf["lambda"][a][key] = str(F(lf["lambda"][a].get(key, "0")) + v)
    lf["lambda"][b][key] = str(F(lf["lambda"][b].get(key, "0")) - v)


def _m_geometry(rng, c):
    kind = rng.choice(["b", "A", "hull", "chain"])
    if kind == "b":
        obs = rng.choice(list(c["obstacles"].values()))
        j = rng.randrange(len(obs["b"]))
        obs["b"][j] = str(F(obs["b"][j]) + _eps(rng))
    elif kind == "A":
        obs = rng.choice(list(c["obstacles"].values()))
        row = rng.choice(obs["A"])
        i = rng.randrange(3)
        row[i] = str(F(row[i]) + _eps(rng))
    elif kind == "hull":
        v = rng.choice(c["body"]["hull_vertices"])
        i = rng.randrange(3)
        v[i] = str(F(v[i]) + _eps(rng))
    elif c["robot"]["kind"] == "planar_revolute":
        ll = c["robot"]["link_lengths"]
        i = rng.randrange(len(ll))
        ll[i] = str(F(ll[i]) + _eps(rng))
    else:
        jt = rng.choice(c["robot"]["joints"])
        field = rng.choice(["offset", "offset", "axis"])
        i = rng.randrange(3)
        jt[field][i] = str(F(jt[field][i]) + _eps(rng)) if field == "offset" else \
            rng.choice(["0", "1", "-1", "3/5", "4/5"])


def _m_barrier(rng, c):
    kind = rng.choice(["delta", "delta_edge", "phi", "start", "goal", "degree"])
    if kind == "delta":
        c["delta"] = str(F(c["delta"]) * rng.choice(
            [F(1, 2), F(9, 10), F(999, 1000), F(1001, 1000), F(11, 10), F(2)]))
    elif kind == "delta_edge":
        # put delta EXACTLY on a cell edge: a Bernstein coefficient of an outside test is then 0
        edges = sorted({abs(F(x)) for lf in c["leaves"] for x in lf["cell"][0]} - {F(0)})
        c["delta"] = str(rng.choice(edges))
    elif kind == "phi":
        n = int(c["robot"]["n"])
        e = [0] * n
        e[rng.randrange(n)] = rng.randint(0, 2)
        key = ",".join(map(str, e))
        c["phi"]["coeffs"][key] = str(F(c["phi"]["coeffs"].get(key, "0")) + _eps(rng) / 100)
    elif kind in ("start", "goal"):
        s = c[kind + "_s"]
        i = rng.randrange(len(s))
        s[i] = str(F(s[i]) + _eps(rng))
    else:
        c["phi"]["degree_per_var"] = rng.choice([0, 1, 2, 3, "2", 4])


def _m_partition(rng, c):
    kind = rng.choice(["drop", "dup", "cell", "box", "status", "obstacle", "shuffle", "split"])
    lv = c["leaves"]
    if kind == "drop":
        del lv[rng.randrange(len(lv))]
    elif kind == "dup":
        lv.insert(rng.randrange(len(lv) + 1), copy.deepcopy(rng.choice(lv)))
    elif kind == "cell":
        pair = rng.choice(rng.choice(lv)["cell"])
        i = rng.randrange(2)
        pair[i] = str(F(pair[i]) + _eps(rng))
    elif kind == "box":
        pair = rng.choice(c["box"])
        i = rng.randrange(2)
        pair[i] = str(F(pair[i]) + _eps(rng))
    elif kind == "status":
        rng.choice(lv)["status"] = rng.choice(["outside", "collision", "undecided", "fail"])
    elif kind == "obstacle":
        _collision(rng, c)["obstacle"] = rng.choice(list(c["obstacles"]) + ["NOPE"])
    elif kind == "shuffle":
        rng.shuffle(lv)                                   # same tiling, another file order
    else:
        # bisect a leaf at the midpoint of one axis: still a valid tiling, both halves certified
        i = rng.randrange(len(lv))
        lf = lv[i]
        ax = rng.randrange(len(lf["cell"]))
        lo, hi = (F(x) for x in lf["cell"][ax])
        a, b = copy.deepcopy(lf), copy.deepcopy(lf)
        a["cell"][ax] = [str(lo), str((lo + hi) / 2)]
        b["cell"][ax] = [str((lo + hi) / 2), str(hi)]
        lv[i:i + 1] = [a, b]


def _m_structure(rng, c):
    kind = rng.choice(["lam_degree", "link", "n", "qstar", "lock", "kind"])
    r = c["robot"]
    if kind == "lam_degree":
        c["lam_degree"] = rng.choice(["const", "affine", "quadratic", "cubic"])
    elif kind == "link":
        c["body"]["link"] = max(0, int(c["body"]["link"]) + rng.choice([-1, 1, 1, 5]))
    elif kind == "n":
        r["n"] = int(r["n"]) + rng.choice([-1, 1])
    elif kind == "qstar":
        r["q_star"][rng.randrange(len(r["q_star"]))] = rng.choice(["0", "0.0", "0/7", "1/10"])
    elif kind == "lock":
        locks = r.get("locked_joints") or {}
        if locks and rng.random() < 0.7:
            k = rng.choice(list(locks))
            locks[k] = rng.choice([{"cos": "3/5", "sin": "4/5"}, {"cos": "0", "sin": "1"},
                                   {"cos": "1", "sin": "0"}, {"cos": "1/2", "sin": "1/2"},
                                   {"cos": "-1", "sin": "0"}])
        else:
            n_j = len(r.get("joints") or r["link_lengths"])
            r["locked_joints"] = dict(locks, **{str(rng.randrange(n_j)): {"cos": "1", "sin": "0"}})
    else:
        r["kind"] = rng.choice(["planar_revolute", "spatial_revolute", "prismatic"])


def _m_respell(rng, c):
    """Rewrite several numbers without changing their value: the verdict must not move."""
    slots = _numeric_slots(c)
    for box, key in rng.sample(slots, min(len(slots), 12)):
        box[key] = _respell(rng, box[key])


def _m_garbage(rng, c):
    box, key = rng.choice(_numeric_slots(c))
    box[key] = rng.choice(["abc", "", "1/0", "1.2.3", "0x10", "nan", "inf", "1e", "--1", " ", "1/-2",
                           "１", None, 3, -2, 0, [], {}, "1_0", "1e400"])


FUZZ_MUTATORS = [(_m_mu, 3), (_m_lambda_pair, 3), (_m_lambda_one, 1), (_m_lambda_new_term, 2),
                 (_m_geometry, 4), (_m_barrier, 4), (_m_partition, 4), (_m_structure, 2),
                 (_m_respell, 2), (_m_garbage, 2)]


def fuzz(binary: str, bases: list, n_cases: int, seed: int, tmp_dir: str) -> dict:
    rng = random.Random(seed)
    names = [m.__name__[3:] for m, w in FUZZ_MUTATORS]
    weights = [w for _, w in FUZZ_MUTATORS]
    stats = {"cases": 0, "both_proof": 0, "both_reject": 0, "python_raises_lean_rejects": 0,
             "python_exceptions": {}, "reason_differs": [], "lean_stricter_parse": [],
             "divergences": [],
             "by_mutator": {nm: {"proof": 0, "reject": 0} for nm in names}}
    path = os.path.join(tmp_dir, "fuzz.cert.json")
    for case in range(n_cases):
        base_name, base = rng.choice(bases)
        c = copy.deepcopy(base)
        k = rng.choices(range(len(FUZZ_MUTATORS)), weights=weights)[0]
        try:
            FUZZ_MUTATORS[k][0](rng, c)
        except (ValueError, IndexError, KeyError):
            continue                                       # mutation not applicable to this base
        with open(path, "w") as f:
            json.dump(c, f)
        tag = f"#{case} {base_name} {names[k]}"
        stats["cases"] += 1
        try:
            ok, msg = verify.verify(c)
        except Exception as exc:                           # verify.py aborted: not an acceptance
            ok, msg = None, f"RAISES {exc!r}"
            kind = type(exc).__name__
            stats["python_exceptions"][kind] = stats["python_exceptions"].get(kind, 0) + 1
        lean, _ = run_lean(binary, path)
        if ok is True and lean["ok"]:
            stats["both_proof"] += 1
            stats["by_mutator"][names[k]]["proof"] += 1
        elif ok is True:
            if lean["code"] in ("malformed", "malformed_obstacle", "arity_mismatch"):
                stats["lean_stricter_parse"].append(f"{tag}: {lean['message']}")
            else:
                stats["divergences"].append(f"{tag}: Python PROOF, Lean {lean['message']}")
        elif lean["ok"]:
            stats["divergences"].append(f"{tag}: Lean PROOF, Python {msg}")
        elif ok is None:
            stats["python_raises_lean_rejects"] += 1
            stats["by_mutator"][names[k]]["reject"] += 1
        else:
            stats["both_reject"] += 1
            stats["by_mutator"][names[k]]["reject"] += 1
            code, leaf, index = classify(msg, c)
            if (code, index) != (lean["code"], lean["index"]) or \
                    (leaf is not None and leaf != lean["leaf"]):
                stats["reason_differs"].append(
                    f"{tag}: Python {_fmt(code, leaf, index)} / "
                    f"Lean {_fmt(lean['code'], lean['leaf'], lean['index'])}")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bin", required=True, help="path to the cnp-verify executable")
    ap.add_argument("--mutations", required=True, help="directory written by export_mutations.py")
    ap.add_argument("--markdown", action="store_true", help="print Markdown tables")
    ap.add_argument("--fuzz", type=int, default=0, help="number of differential fuzz cases")
    ap.add_argument("--seed", type=int, default=20261009, help="fuzz seed")
    args = ap.parse_args(argv)

    shipped = sorted(glob.glob(os.path.join(_REPO, "scenes", "*.cert.json"))) + \
        sorted(glob.glob(os.path.join(_REPO, "scenes", "wall", "*.cert.json")))
    with open(os.path.join(args.mutations, "manifest.json")) as f:
        manifest = json.load(f)

    sep = " | " if args.markdown else "  "
    edge = "| " if args.markdown else ""
    bad = 0

    print(f"\n== shipped certificates ({len(shipped)}) ==")
    head = ["certificate", "Python", "Lean", "Python s", "Lean s", "Lean wall s", "Lean/Python"]
    print(edge + sep.join(head) + (" |" if args.markdown else ""))
    if args.markdown:
        print("|" + "---|" * len(head))
    for path in shipped:
        r = compare(path, args.bin)
        bad += not (r["verdict_match"] and r["python_ok"])
        cells = [r["file"], "PROOF" if r["python_ok"] else "REJECT",
                 "PROOF" if r["lean_ok"] else "REJECT", f"{r['python_s']:.3f}",
                 f"{r['lean_s']:.3f}", f"{r['lean_wall_s']:.3f}",
                 f"x{r['lean_s'] / r['python_s']:.2f}" if r["python_s"] > 0 else "-"]
        print(edge + sep.join(cells) + (" |" if args.markdown else ""))

    print(f"\n== adversarial corpus ({len(manifest)}) ==")
    head = ["certificate", "Python", "Lean", "Python reason", "Lean reason", "match"]
    print(edge + sep.join(head) + (" |" if args.markdown else ""))
    if args.markdown:
        print("|" + "---|" * len(head))
    n_rej = n_acc = 0
    for entry in manifest:
        r = compare(os.path.join(args.mutations, entry["file"]), args.bin)
        if r["python_ok"] != entry["python_ok"] or r["python_message"] != entry["python_message"]:
            raise SystemExit(f"{entry['file']}: the exported JSON does not reproduce the "
                             "in-memory Python verdict recorded in the manifest")
        match = r["verdict_match"] and r["reason_match"]
        bad += not match
        n_rej += not r["python_ok"]
        n_acc += r["python_ok"]
        cells = [f"{entry['suite']}/{entry['name']}", "PROOF" if r["python_ok"] else "REJECT",
                 "PROOF" if r["lean_ok"] else "REJECT", r["python_reason"], r["lean_reason"],
                 "ok" if match else "DIVERGENCE"]
        print(edge + sep.join(cells) + (" |" if args.markdown else ""))

    print(f"\nshipped: {len(shipped)} certificates; corpus: {n_rej} rejected + {n_acc} accepted "
          f"by Python; divergences: {bad}")

    if args.fuzz:
        # bases: the small valid certificates (fast to check), planar, spatial and locked
        bases = [(e["name"], json.load(open(os.path.join(args.mutations, e["file"]))))
                 for e in manifest if e["suite"] == "baseline"]
        for rel in ("scenes/S3_shoulder_elbow.cert.json", "scenes/S4_iiwa_bin.cert.json",
                    "scenes/wall/k3.cert.json", "scenes/wall/k4.cert.json"):
            bases.append((os.path.basename(rel), json.load(open(os.path.join(_REPO, rel)))))
        st = fuzz(args.bin, bases, args.fuzz, args.seed, args.mutations)
        print(f"\n== differential fuzz (seed {args.seed}) ==")
        print(f"cases: {st['cases']}; both PROOF: {st['both_proof']}; both REJECT: "
              f"{st['both_reject']}; Python raises / Lean rejects: "
              f"{st['python_raises_lean_rejects']}; Lean stricter at parsing: "
              f"{len(st['lean_stricter_parse'])}; reason differs: {len(st['reason_differs'])}; "
              f"VERDICT DIVERGENCES: {len(st['divergences'])}")
        for nm, d in st["by_mutator"].items():
            print(f"  {nm:16s} proof {d['proof']:5d}  reject {d['reject']:5d}")
        print(f"  uncaught Python exceptions: {st['python_exceptions']}")
        for title in ("divergences", "lean_stricter_parse", "reason_differs"):
            for line in st[title][:40]:
                print(f"  [{title}] {line}")
        bad += len(st["divergences"])
        # The documented asymmetry must stay marginal: a checker that rejected everything as
        # "malformed" would otherwise pass this section.
        if len(st["lean_stricter_parse"]) > max(1, st["cases"] // 100):
            print("  TOO MANY certificates accepted by Python and rejected by the Lean parser "
                  "(> 1 % of the cases): counted as a divergence")
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
