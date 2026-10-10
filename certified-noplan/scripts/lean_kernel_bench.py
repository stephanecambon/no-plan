#!/usr/bin/env python3
"""L4 — can the Lean KERNEL evaluate ``check c`` on a shipped certificate? Measured.

    python3 scripts/lean_kernel_bench.py [--only wallK3,…] [--mem-gb 9] [--timeout 1800]
                                         [--no-archive]

For each certificate written as a Lean term (``lean/Certs/*.lean``), four ways of proving
``check c = true`` are tried, each in its own ``lake env lean`` process, under a wall-clock
limit and a memory limit (the process tree is killed when its resident memory passes
``--mem-gb``):

  decide          ``by decide`` — the elaborator reduces the ``Decidable`` instance first;
  kernel          ``by decide +kernel`` — ONE evaluation of ``check c`` by the kernel;
  staged          the proof written by ``lean/CertStages.lean`` — the same evaluation cut into
                  independent kernel evaluations (``lean/Certs/Staged.lean``); stages are run
                  ONE PROCESS EACH, in file order. The proof needs them all: at the first
                  stage that fails the certificate is recorded as FAIL, and only one stage of
                  each kind not yet seen is still run, for information. When every stage
                  passes, the whole file is compiled once more in a single process: that is
                  the proof as built;
  native_decide   ``by native_decide`` — compiled evaluation, which adds an axiom.

``decide``, ``kernel`` and ``staged`` use the kernel only. ``native_decide`` trusts the
compiler: its row is there to show the gap, and its axioms are printed.

An "import only" process per certificate gives the fixed cost (loading the imports) included
in every wall-clock figure. ``kernel s`` is the sum of the profiler's ``type checking took``
lines of 1 ms and more: the time spent in the kernel itself.

Unless ``--no-archive``: writes ``benchmarks/results/<UTC>/lean_kernel.{json,md}`` (rule 7:
never overwritten; commit, state of the tree, versions, load average at each probe).
Stdlib only; needs ``lake`` (elan) and ``lake build Certs`` done.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAN = os.path.join(ROOT, "lean")

# (Lean name, module of the term, certificate file)
TARGETS = [
    ("wallK3", "WallK3", "scenes/wall/k3.cert.json"),
    ("s3ShoulderElbow", "S3ShoulderElbow", "scenes/S3_shoulder_elbow.cert.json"),
    ("s6IiwaRealShelf", "S6IiwaRealShelf", "scenes/S6_iiwa_real_shelf.cert.json"),
]
PROFILE = "set_option Elab.async false\nset_option profiler true\nset_option profiler.threshold 1\n"
_UNITS = {"ms": 1e-3, "s": 1.0, "µs": 1e-6, "us": 1e-6, "ns": 1e-9, "min": 60.0}


def tree_rss(root: int) -> int:
    """Resident memory (bytes) of a process and its descendants."""
    out = subprocess.run(["ps", "-Ao", "pid=,ppid=,rss="], capture_output=True, text=True).stdout
    kids, rss = {}, {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            pid, ppid, r = map(int, parts)
            kids.setdefault(ppid, []).append(pid)
            rss[pid] = r
    total, stack = 0, [root]
    while stack:
        x = stack.pop()
        total += rss.get(x, 0)
        stack += kids.get(x, [])
    return total * 1024


def run_lean(source: str, timeout: float, mem_gb: float) -> dict:
    """Compile one Lean source in its own process tree, under the two limits."""
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, encoding="utf-8") as f:
        f.write(source)
        path = f.name
    load = os.getloadavg()[0]
    t0 = time.time()
    # output to a FILE: the profiler is verbose, and an unread pipe would block the process
    log = tempfile.TemporaryFile("w+", encoding="utf-8")
    proc = subprocess.Popen(["lake", "env", "lean", path], cwd=LEAN, stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    peak, killed = 0, None
    while proc.poll() is None:
        time.sleep(0.2)
        r = tree_rss(proc.pid)
        peak = max(peak, r)
        if r > mem_gb * 2**30:
            killed = f"memory > {mem_gb:g} GB"
        elif time.time() - t0 > timeout:
            killed = f"time > {timeout:g} s"
        if killed:
            os.killpg(proc.pid, 9)
            break
    proc.wait()
    wall = time.time() - t0
    log.seek(0)
    out = log.read()
    log.close()
    os.unlink(path)
    kernel = sum(float(v) * _UNITS[u]
                 for v, u in re.findall(r"type checking took ([0-9.]+)\s*(ms|s|µs|us|ns|min)\b", out))
    errors = [ln for ln in out.splitlines() if re.search(r": error", ln)]
    ok = killed is None and proc.returncode == 0 and not errors
    return {"ok": ok, "killed": killed, "exit": proc.returncode, "wall_s": round(wall, 1),
            "kernel_s": round(kernel, 1), "peak_rss_gb": round(peak / 2**30, 2),
            "load1_at_start": round(load, 2), "output": out}


def brief(r: dict) -> str:
    """One cell of the table."""
    if r["ok"]:
        return f"{r['wall_s']:.1f} s (kernel {r['kernel_s']:.1f} s), {r['peak_rss_gb']:.2f} GB"
    if r["killed"]:
        return f"FAIL — killed, {r['killed']}, after {r['wall_s']:.0f} s (peak {r['peak_rss_gb']:.2f} GB)"
    return f"FAIL — {r.get('cause', 'error')} ({r['wall_s']:.1f} s)"


def stuck_cause(out: str) -> str:
    """Why `decide` gave up: the instance the reduction got stuck at, from Lean's own message."""
    m = re.search(r"reduction got stuck at the `Decidable` instance\s*\n\s*(.+)", out)
    if m:
        return "reduction stuck at `" + m.group(1).strip() + "`"
    m = re.search(r"error: (.+)", out)
    return m.group(1).strip()[:160] if m else "error"


def split_staged(text: str):
    """(preamble with every non-theorem item, [(theorem name, its source)]) of a generated
    staged proof; the theorems that only ASSEMBLE stages (`…_ok`, `leaves_ok`, the final one) are
    dropped: they evaluate nothing."""
    body = text.split("end CnpVerify.Certs.")[0]          # before the final namespace
    cut = body.index("abbrev c : Certificate")            # header: comment, imports, options
    blocks = re.split(r"\n(?=theorem |def |abbrev |/-!)", body[cut:])
    pre, stages = [body[:cut]], []
    for b in blocks:
        m = re.match(r"theorem (\S+)", b)
        if not m:
            pre.append(b)
        elif "decide +kernel" in b and not m.group(1).endswith("_ok"):
            stages.append((m.group(1), b))
    return "\n".join(pre), stages


def bench(name: str, mod: str, cert: str, args) -> dict:
    d = json.load(open(os.path.join(ROOT, cert)))
    kinds = [lf["status"] for lf in d["leaves"]]
    row = {"certificate": cert, "term": f"CnpVerify.Certs.{name}", "n": int(d["robot"]["n"]),
           "leaves": len(kinds), "collision_leaves": kinds.count("collision"),
           "outside_leaves": kinds.count("outside"),
           "hull_vertices": len(d["body"]["hull_vertices"])}
    head = f"import Certs.{mod}\nopen CnpVerify CnpVerify.Certs\n{PROFILE}"
    goal = f"check {name} = true"

    def say(label, r):
        print(f"  {label:<22} {brief(r)}   [load {r['load1_at_start']}]", flush=True)

    r = run_lean(head, args.timeout, args.mem_gb)
    row["import_only"] = r
    say("import only", r)

    r = run_lean(head + f"theorem t : {goal} := by decide\n", args.timeout, args.mem_gb)
    if not r["ok"]:
        # where does the reduction stop? ask for the FIRST test of the checker alone (δ > 0)
        first = run_lean(head + f"example : ¬ ({name}.delta ≤ 0) := by decide\n",
                         args.timeout, args.mem_gb)
        r["cause"] = stuck_cause(r["output"])
        r["first_test"] = (f"`¬ ({name}.delta ≤ 0)` decided" if first["ok"]
                           else f"already on the first test `¬ ({name}.delta ≤ 0)`: "
                                + stuck_cause(first["output"]))
        r["cause"] += "; " + r["first_test"]
    row["decide"] = r
    say("decide", r)

    r = run_lean(head + f"theorem t : {goal} := by decide +kernel\n", args.timeout, args.mem_gb)
    row["kernel"] = r
    say("decide +kernel", r)

    gen = subprocess.run(["lake", "env", "lean", "--run", "CertStages.lean", name], cwd=LEAN,
                         capture_output=True, text=True)
    if gen.returncode != 0:
        raise SystemExit(f"CertStages.lean {name} failed:\n{gen.stdout}{gen.stderr}")
    pre, stages = split_staged(gen.stdout)
    pre = pre.replace("set_option Elab.async false\n", PROFILE, 1)
    staged = {"n_stages": len(stages), "stages": [], "first_failure": None, "probes": []}
    seen_kinds = set()
    for sname, src in stages:
        kind = re.sub(r"^[LO]\d+_", "", sname)
        kind = re.sub(r"\d+$", "", kind)                   # face0..face5 -> face
        if staged["first_failure"] is not None and kind in seen_kinds:
            continue                                       # after a failure: one probe per NEW kind
        seen_kinds.add(kind)
        r = run_lean(pre + "\n" + src + "\n", args.timeout, args.mem_gb)
        err = re.search(r": error.*", r.pop("output"))
        if err and not r["ok"]:
            r["cause"] = err.group(0)[2:200]
        if staged["first_failure"] is None:
            staged["stages"].append({"stage": sname, **r})
            if not r["ok"]:
                staged["first_failure"] = sname
                print(f"    stage {sname}: {brief(r)}", flush=True)
        else:
            staged["probes"].append({"stage": sname, **r})
            print(f"    (information) later stage {sname}: {brief(r)}", flush=True)
    done = [s for s in staged["stages"] if s["ok"]]
    staged["stages_passed"] = len(done)
    staged["sum_kernel_s"] = round(sum(s["kernel_s"] for s in done), 1)
    staged["max_stage_rss_gb"] = max([s["peak_rss_gb"] for s in staged["stages"]], default=0)
    if staged["first_failure"] is None:
        whole = gen.stdout.replace("set_option Elab.async false\n", PROFILE, 1)
        whole += f"\n#print axioms CnpVerify.Certs.{name}_proof\n"
        r = run_lean(whole, args.timeout, args.mem_gb)
        m = re.search(r"depends on axioms: \[([^\]]*)\]", r["output"], re.S)
        r["axioms"] = [a.strip() for a in m.group(1).split(",")] if m else None
        staged["whole_file"] = r
        say(f"staged ({len(stages)} stages)", r)
    else:
        f = staged["stages"][-1]
        print(f"  {'staged':<22} FAIL at stage {staged['stages_passed'] + 1}/{len(stages)} "
              f"`{staged['first_failure']}` — {brief(f)}", flush=True)
    row["staged"] = staged

    r = run_lean(head + f"theorem t : {goal} := by native_decide\n#print axioms t\n",
                 args.timeout, args.mem_gb)
    m = re.search(r"depends on axioms: \[([^\]]*)\]", r["output"], re.S)
    r["axioms"] = [a.strip() for a in m.group(1).split(",")] if m else None
    # time of the evaluation proper (the profiler names it: the IR interpreter runs the term)
    m = re.search(r"interpretation of \S*native_decide\S* took ([0-9.]+)\s*(ms|s|min)\b", r["output"])
    r["evaluation_s"] = round(float(m.group(1)) * _UNITS[m.group(2)], 3) if m else None
    row["native_decide"] = r
    say("native_decide", r)
    return row


def markdown(rows, meta) -> str:
    def staged_cell(s):
        if s["first_failure"] is None:
            w = s["whole_file"]
            return (f"{w['wall_s']:.0f} s (kernel {w['kernel_s']:.0f} s), {w['peak_rss_gb']:.1f} GB, "
                    f"{s['n_stages']} stages")
        f = s["stages"][-1]
        why = (f"killed, {f['killed']}, after {f['wall_s']:.0f} s" if f["killed"]
               else f.get("cause", "error"))
        return (f"FAIL at stage {s['stages_passed'] + 1}/{s['n_stages']} `{s['first_failure']}` "
                f"({why}); {s['stages_passed']} stages passed in {s['sum_kernel_s']:.0f} s of kernel")

    def cell(r):
        if r["ok"]:
            ev = f" (evaluation {r['evaluation_s']:g} s)" if r.get("evaluation_s") is not None else ""
            return f"{r['wall_s']:.1f} s{ev}, {r['peak_rss_gb']:.1f} GB"
        if r["killed"]:
            return f"FAIL (killed, {r['killed']}, after {r['wall_s']:.0f} s)"
        return f"FAIL ({r.get('cause', 'error')})"

    lines = [f"# Kernel evaluation of `check c` — {meta['utc']}", ""]
    lines += [f"- commit `{meta['commit']}` (tree dirty at start: {meta['git_dirty_at_start']})",
              f"- {meta['lean']}; Mathlib `{meta['mathlib']}`",
              f"- {meta['machine']}; load average at start {meta['load_at_start']}",
              f"- limits per process: {meta['timeout_s']:g} s, {meta['mem_gb']:g} GB resident", "",
              "| certificate | n | leaves (collision / outside) | body vertices | `decide` | "
              "`decide +kernel`, one evaluation | staged kernel proof | `native_decide` (adds an axiom) |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['certificate']}` | {r['n']} | {r['leaves']} "
                     f"({r['collision_leaves']} / {r['outside_leaves']}) | {r['hull_vertices']} | "
                     f"{cell(r['decide'])} | {cell(r['kernel'])} | {staged_cell(r['staged'])} | "
                     f"{cell(r['native_decide'])} |")
    lines += ["", "Wall-clock figures include loading the imports "
              f"({', '.join(str(r['import_only']['wall_s']) + ' s' for r in rows)}).", ""]
    for r in rows:
        s = r["staged"]
        lines += [f"## Stages — `{r['certificate']}`", "",
                  "| stage | result | wall s | kernel s | peak GB |", "|---|---|---|---|---|"]
        for st in s["stages"]:
            res = "ok" if st["ok"] else ("killed: " + st["killed"] if st["killed"]
                                         else st.get("cause", "error"))
            lines.append(f"| `{st['stage']}` | {res} | {st['wall_s']} | {st['kernel_s']} | "
                         f"{st['peak_rss_gb']} |")
        if s["first_failure"] is not None:
            lines.append(f"| … {s['n_stages'] - len(s['stages'])} later stage(s) | not needed: the proof "
                         "already fails; one stage of each other kind probed below | | | |")
            for st in s["probes"]:
                res = "ok" if st["ok"] else ("killed: " + st["killed"] if st["killed"]
                                             else st.get("cause", "error"))
                lines.append(f"| (information) `{st['stage']}` | {res} | {st['wall_s']} | "
                             f"{st['kernel_s']} | {st['peak_rss_gb']} |")
        ax = (s.get("whole_file") or {}).get("axioms")
        lines += ["", f"Axioms of the staged proof: {ax}" if ax else "No proof obtained.",
                  f"Axioms of the `native_decide` proof: {r['native_decide'].get('axioms')}", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--only", default="", help="comma-separated Lean names (default: all)")
    ap.add_argument("--mem-gb", type=float, default=9.0)
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()
    only = {x for x in args.only.split(",") if x}

    def sh(cmd, cwd=ROOT):
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout.strip()

    meta = {"utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "commit": sh(["git", "rev-parse", "HEAD"]),
            "git_dirty_at_start": bool(sh(["git", "status", "--porcelain"])),
            "lean": sh(["lean", "--version"], LEAN),
            "mathlib": sh(["git", "-C", ".lake/packages/mathlib", "describe", "--tags", "--always"], LEAN),
            "machine": sh(["uname", "-srm"]) + ", "
                       + (sh(["sysctl", "-n", "machdep.cpu.brand_string"]) or "unknown CPU"),
            "load_at_start": [round(x, 2) for x in os.getloadavg()],
            "timeout_s": args.timeout, "mem_gb": args.mem_gb}
    build = subprocess.run(["lake", "build", "Certs"], cwd=LEAN, capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stdout + build.stderr)
        return 2
    rows = []
    for name, mod, cert in TARGETS:
        if only and name not in only:
            continue
        print(f"{cert}  ({name})", flush=True)
        rows.append(bench(name, mod, cert, args))
    for r in rows:                                        # raw outputs: keep the tail only
        for k in ("import_only", "decide", "kernel", "native_decide"):
            r[k]["output"] = r[k]["output"][-1500:]
        if "whole_file" in r["staged"]:
            r["staged"]["whole_file"]["output"] = r["staged"]["whole_file"]["output"][-1500:]
    md = markdown(rows, meta)
    print("\n" + md)
    if not args.no_archive:
        out = os.path.join(ROOT, "benchmarks", "results", meta["utc"])
        os.mkdir(out)
        with open(os.path.join(out, "lean_kernel.json"), "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "rows": rows}, f, indent=1, ensure_ascii=False)
        with open(os.path.join(out, "lean_kernel.md"), "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print(f"archived: {out}/lean_kernel.{{json,md}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
