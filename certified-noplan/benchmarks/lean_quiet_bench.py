#!/usr/bin/env python3
"""L4-bis — the Lean measurements of L4 replayed on a QUIET machine (L4 review, decision 7).

    python3 benchmarks/lean_quiet_bench.py kernel   # -> benchmarks/results/<UTC>/lean_kernel_bench.{json,md}
    python3 benchmarks/lean_quiet_bench.py parity   # ARCHIVE=1 make lean-parity, then lean_parity.json beside its log

Both refuse to measure unless the tree is clean and the 1-minute load average is below
``--max-load`` (they wait for it at most ``--wait`` seconds, then stop without measuring), and
both write ``uptime`` before and after the run into their JSON.

kernel   the probes of ``scripts/lean_kernel_bench.py`` — imported, not copied: same
         ``run_lean``, one ``lake env lean`` process per probe, same time and memory limits —
         restricted to what SUCCEEDED in L4:
           wall/k3   the staged kernel proof of ``check wallK3 = true`` (each stage alone,
                     then the whole file in one process: the proof as built), and
                     ``by native_decide``;
           S3, S6    ``by native_decide`` only.
         ``by decide``, ``by decide +kernel`` in one evaluation, and the staged attempts on S3
         and S6 are failures established in L4 (killed above 9 GiB, or stuck at once): they do
         not depend on the load and are NOT replayed; the JSON says so and names the runs.
         The table of array operations in the kernel is replayed (timings, not failures).

parity   runs the unmodified gate (``lean/check_all.sh``: 13 shipped certificates,
         adversarial corpus, seeded fuzz of 1 000 cases) and turns the log it archives into
         ``lean_parity.json``, so that the paper's Lean/Python ratio is read from a file.

Stdlib only; needs ``lake`` (elan), the Mathlib cache and, for ``parity``, the venv.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAN = os.path.join(ROOT, "lean")
STAGED_CERT = "wallK3"                      # the only certificate whose staged proof passes (L4)
L4_FAILURE_RUNS = ["20261010T163223Z", "20261010T171636Z"]
NOT_RERUN = ("failures documented in runs " + " and ".join(L4_FAILURE_RUNS) + ", not re-run: "
             "`by decide` and `by decide +kernel` in one evaluation on the three certificates, "
             "the staged kernel proof on S3 and S6")


def sh(cmd, cwd=ROOT) -> str:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout.strip()


def state() -> dict:
    """The machine at this instant: `uptime` verbatim and the three load averages."""
    return {"local_time": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "uptime": sh(["uptime"]), "loadavg": [round(x, 2) for x in os.getloadavg()]}


def wait_quiet(max_load: float, wait_s: float) -> dict | None:
    """The state once the 1-minute load is below `max_load`; None if it is not within `wait_s`."""
    t0 = time.time()
    while True:
        s = state()
        if s["loadavg"][0] < max_load:
            s["waited_s"] = round(time.time() - t0)
            return s
        if time.time() - t0 >= wait_s:
            print(f"NOT QUIET: 1-minute load {s['loadavg'][0]} >= {max_load:g} after "
                  f"{wait_s:g} s — nothing measured.\n{s['uptime']}")
            return None
        time.sleep(10)


def base_meta(args) -> dict | None:
    if sh(["git", "status", "--porcelain"]):
        print("tree not clean — nothing measured (commit first: the JSON must name the code it ran).")
        return None
    return {"utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "commit": sh(["git", "rev-parse", "HEAD"]), "git_dirty": False,
            "lean": sh(["lean", "--version"], LEAN), "lake": sh(["lake", "--version"], LEAN),
            "mathlib": sh(["git", "-C", ".lake/packages/mathlib", "describe", "--tags", "--always"], LEAN),
            "mathlib_commit": sh(["git", "-C", ".lake/packages/mathlib", "rev-parse", "HEAD"], LEAN),
            "machine": f"{sh(['uname', '-srm'])}, {sh(['sysctl', '-n', 'machdep.cpu.brand_string']) or 'unknown CPU'}, "
                       f"{sh(['sysctl', '-n', 'hw.ncpu'])} cores, "
                       f"{int(sh(['sysctl', '-n', 'hw.memsize']) or 0) / 2**30:.0f} GiB, "
                       f"macOS {sh(['sw_vers', '-productVersion'])}",
            "max_load": args.max_load, "driver": "benchmarks/lean_quiet_bench.py"}


def load_l4_bench():
    spec = importlib.util.spec_from_file_location(
        "lean_kernel_bench", os.path.join(ROOT, "scripts", "lean_kernel_bench.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slim(r: dict) -> dict:
    """A probe without its raw output (the tail is kept when it failed)."""
    out = r.pop("output", "")
    if not r["ok"]:
        r["output_tail"] = out[-800:]
    return r


def axioms_of(out: str):
    m = re.search(r"depends on axioms: \[([^\]]*)\]", out, re.S)
    return [a.strip() for a in m.group(1).split(",")] if m else None


def probe(lkb, name: str, mod: str, cert: str, args) -> dict:
    d = json.load(open(os.path.join(ROOT, cert)))
    kinds = [lf["status"] for lf in d["leaves"]]
    row = {"certificate": cert, "term": f"CnpVerify.Certs.{name}", "n": int(d["robot"]["n"]),
           "leaves": len(kinds), "collision_leaves": kinds.count("collision"),
           "outside_leaves": kinds.count("outside"),
           "hull_vertices": len(d["body"]["hull_vertices"])}
    head = f"import Certs.{mod}\nopen CnpVerify CnpVerify.Certs\n{lkb.PROFILE}"
    lim = (args.timeout, args.mem_gb)
    print(f"{cert}  ({name})", flush=True)

    row["import_only"] = slim(lkb.run_lean(head, *lim))
    print(f"  import only            {row['import_only']['wall_s']} s", flush=True)

    if name == STAGED_CERT:
        gen = subprocess.run(["lake", "env", "lean", "--run", "CertStages.lean", name], cwd=LEAN,
                             capture_output=True, text=True)
        if gen.returncode != 0:
            raise SystemExit(f"CertStages.lean {name} failed:\n{gen.stdout}{gen.stderr}")
        with open(os.path.join(LEAN, "Certs", "WallK3Kernel.lean"), encoding="utf-8") as f:
            shipped = f.read()
        pre, stages = lkb.split_staged(gen.stdout)
        st = {"n_stages": len(stages), "stages": [], "first_failure": None,
              "generated_equals_shipped_file": gen.stdout.strip() == shipped.strip()}
        for sname, src in stages:                          # each stage alone, one process each
            r = slim(lkb.run_lean(lkb.preamble_for(pre, src) + "\n" + src + "\n", *lim))
            st["stages"].append({"stage": sname, **r})
            if not r["ok"] and st["first_failure"] is None:
                st["first_failure"] = sname
                print(f"    stage {sname}: {lkb.brief(r)}", flush=True)
        done = [s for s in st["stages"] if s["ok"]]
        st["stages_passed"] = len(done)
        st["sum_kernel_s"] = round(sum(s["kernel_s"] for s in done), 1)
        st["sum_wall_s"] = round(sum(s["wall_s"] for s in done), 1)
        st["max_stage_rss_gb"] = max(s["peak_rss_gb"] for s in st["stages"])
        print(f"  stages alone           {st['stages_passed']}/{len(stages)} pass, kernel "
              f"{st['sum_kernel_s']} s, largest {st['max_stage_rss_gb']} GiB", flush=True)
        if st["first_failure"] is None:                    # the proof as built: one process
            whole = gen.stdout.replace("set_option Elab.async false\n", lkb.PROFILE, 1)
            whole += f"\n#print axioms CnpVerify.Certs.{name}_proof\n"
            before = state()
            r = lkb.run_lean(whole, *lim)
            r["axioms"] = axioms_of(r["output"])
            r = slim(r)
            r["before"], r["after"] = before, state()
            st["whole_file"] = r
            print(f"  staged, whole file     {lkb.brief(r)}   [load {r['load1_at_start']}]", flush=True)
        row["staged"] = st
    else:
        row["staged"] = None

    r = lkb.run_lean(head + f"theorem t : check {name} = true := by native_decide\n#print axioms t\n", *lim)
    r["axioms"] = axioms_of(r["output"])
    m = re.search(r"interpretation of \S*native_decide\S* took ([0-9.]+)\s*(ms|s|min)\b", r["output"])
    r["evaluation_s"] = round(float(m.group(1)) * lkb._UNITS[m.group(2)], 3) if m else None
    row["native_decide"] = slim(r)
    print(f"  native_decide          {lkb.brief(r)}   [load {r['load1_at_start']}]", flush=True)
    return row


def kernel_markdown(doc: dict) -> str:
    meta = doc["meta"]
    lines = [f"# Lean kernel bench on a quiet machine — {meta['utc']}", "",
             f"- commit `{meta['commit']}` (tree dirty: {meta['git_dirty']})",
             f"- {meta['lean']}; Mathlib `{meta['mathlib']}`", f"- {meta['machine']}",
             f"- `uptime` before: `{meta['before']['uptime']}`",
             f"- `uptime` after:  `{meta['after']['uptime']}`",
             f"- limits per process: {meta['timeout_s']:g} s, {meta['mem_gb']:g} GiB resident "
             "(1 GiB = 2^30 bytes)", f"- {doc['not_rerun']}", "",
             "| certificate | n | leaves (collision / outside) | staged kernel proof (`decide +kernel` "
             "per stage), whole file | `native_decide` (one axiom more) |", "|---|---|---|---|---|"]
    for r in doc["rows"]:
        s, nd = r["staged"], r["native_decide"]
        if s is None:
            cell = "not re-run (FAIL in L4)"
        elif "whole_file" in s:
            w = s["whole_file"]
            cell = (f"{w['wall_s']:.1f} s (kernel {w['kernel_s']:.1f} s), peak {w['peak_rss_gb']:.2f} GiB, "
                    f"{s['n_stages']} stages")
        else:
            cell = f"FAIL at `{s['first_failure']}`"
        ev = f" (evaluation {nd['evaluation_s']:g} s)" if nd.get("evaluation_s") is not None else ""
        ncell = f"{nd['wall_s']:.1f} s{ev}, peak {nd['peak_rss_gb']:.2f} GiB" if nd["ok"] else "FAIL"
        lines.append(f"| `{r['certificate']}` | {r['n']} | {r['leaves']} ({r['collision_leaves']} / "
                     f"{r['outside_leaves']}) | {cell} | {ncell} |")
    lines += ["", "Wall-clock figures include loading the imports ("
              + ", ".join(f"{r['import_only']['wall_s']} s" for r in doc["rows"]) + ").", ""]
    for r in doc["rows"]:
        if r["staged"]:
            lines += [f"## Stages — `{r['certificate']}`, one process each", "",
                      "| stage | result | wall s | kernel s | peak GiB |", "|---|---|---|---|---|"]
            lines += [f"| `{s['stage']}` | {'ok' if s['ok'] else 'FAIL'} | {s['wall_s']} | {s['kernel_s']} | "
                      f"{s['peak_rss_gb']} |" for s in r["staged"]["stages"]]
            lines += ["", f"Axioms of the staged proof: {(r['staged'].get('whole_file') or {}).get('axioms')}", ""]
        lines += [f"Axioms of `by native_decide` on `{r['certificate']}`: {r['native_decide'].get('axioms')}", ""]
    return "\n".join(lines)


def kernel(args) -> int:
    lkb = load_l4_bench()
    meta = base_meta(args)
    if meta is None:
        return 3
    t0 = time.time()
    build = subprocess.run(["lake", "build", "Certs"], cwd=LEAN, capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stdout + build.stderr)
        return 2
    meta["certs_build_before_measuring_s"] = round(time.time() - t0, 1)
    before = wait_quiet(args.max_load, args.wait)
    if before is None:
        return 3
    meta.update({"before": before, "timeout_s": args.timeout, "mem_gb": args.mem_gb})
    rows = [probe(lkb, name, mod, cert, args) for name, mod, cert in lkb.TARGETS]
    print("array operations in the kernel", flush=True)
    prim = lkb.primitives(args)
    meta["after"] = state()
    meta["wall_s"] = round(time.time() - t0)
    k3 = next(r for r in rows if r["term"].endswith("." + STAGED_CERT))["staged"]
    peak = max(k3["max_stage_rss_gb"], (k3.get("whole_file") or {}).get("peak_rss_gb", 0))
    doc = {"meta": meta, "not_rerun": NOT_RERUN, "l4_failure_runs": L4_FAILURE_RUNS, "rows": rows,
           "primitives": prim,
           "k3_staged_peak_rss_gb": peak, "k3_staged_peak_over_8_gib": peak > 8.0}
    md = kernel_markdown(doc) + "\n" + lkb.primitives_markdown(prim)
    print("\n" + md)
    out = os.path.join(ROOT, "benchmarks", "results", meta["utc"])
    os.mkdir(out)
    with open(os.path.join(out, "lean_kernel_bench.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "lean_kernel_bench.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(f"archived: {out}/lean_kernel_bench.{{json,md}}")
    ok = all(r["native_decide"]["ok"] for r in rows) and k3["first_failure"] is None \
        and k3["whole_file"]["ok"]
    return 0 if ok else 1


def parse_parity_log(text: str) -> dict:
    head, _, body = text.partition("\n\n")
    header = dict(ln.split(": ", 1) for ln in head.splitlines()[1:] if ": " in ln)
    shipped = [{"certificate": m[0], "python": m[1], "lean": m[2], "python_s": float(m[3]),
                "lean_s": float(m[4]), "lean_wall_s": float(m[5]), "lean_over_python": float(m[6])}
               for m in re.findall(r"^\| (scenes/\S+) \| (\w+) \| (\w+) \| ([\d.]+) \| ([\d.]+) \| "
                                   r"([\d.]+) \| x([\d.]+) \|$", body, re.M)]
    corpus_rows = re.findall(r"^\| \S+/\S+ \| (?:PROOF|REJECT) \| (?:PROOF|REJECT) \| .* \| (ok|DIVERGENCE) \|$",
                             body, re.M)
    m = re.search(r"shipped: (\d+) certificates; corpus: (\d+) rejected \+ (\d+) accepted by Python; "
                  r"divergences: (\d+)", body)
    summary = {"shipped": int(m[1]), "corpus_rejected": int(m[2]), "corpus_accepted": int(m[3]),
               "divergences": int(m[4]), "corpus_rows_ok": corpus_rows.count("ok"),
               "corpus_rows": len(corpus_rows)}
    fuzz = None
    m = re.search(r"== differential fuzz \(seed (\d+)\) ==\ncases: (\d+); both PROOF: (\d+); both REJECT: "
                  r"(\d+); Python raises / Lean rejects: (\d+); Lean stricter at parsing: (\d+); "
                  r"reason differs: (\d+); VERDICT DIVERGENCES: (\d+)", body)
    if m:
        keys = ["seed", "cases", "both_proof", "both_reject", "python_raises_lean_rejects",
                "lean_stricter_at_parsing", "reason_differs", "verdict_divergences"]
        fuzz = dict(zip(keys, map(int, m.groups())))
        e = re.search(r"uncaught Python exceptions: (\{.*\})", body)
        fuzz["uncaught_python_exceptions"] = e[1] if e else None
    ratios = [r["lean_over_python"] for r in shipped]
    py, ln = sum(r["python_s"] for r in shipped), sum(r["lean_s"] for r in shipped)
    timing = {"python_s_total": round(py, 3), "lean_s_total": round(ln, 3),
              "lean_over_python_total": round(ln / py, 3),
              "lean_over_python_min": min(ratios), "lean_over_python_max": max(ratios),
              "lean_over_python_geomean": round(math.exp(sum(map(math.log, ratios)) / len(ratios)), 3)}
    return {"log_header": header, "shipped": shipped, "summary": summary, "fuzz": fuzz,
            "timing": timing}


def parity(args) -> int:
    meta = base_meta(args)
    if meta is None:
        return 3
    before = wait_quiet(args.max_load, args.wait)
    if before is None:
        return 3
    t0 = time.time()
    run = subprocess.run(["make", "lean-parity"], cwd=ROOT, env=dict(os.environ, ARCHIVE="1"),
                         capture_output=True, text=True)
    meta.update({"before": before, "after": state(), "wall_s": round(time.time() - t0),
                 "command": "ARCHIVE=1 make lean-parity", "exit": run.returncode})
    m = re.search(r"archived: (\S+)/lean_parity\.log", run.stdout)
    if not m:
        print(run.stdout[-3000:] + run.stderr[-3000:])
        return 2
    out = m[1]
    with open(os.path.join(out, "lean_parity.log"), encoding="utf-8") as f:
        doc = {"meta": meta, **parse_parity_log(f.read())}
    doc["meta"]["log"] = os.path.relpath(os.path.join(out, "lean_parity.log"), ROOT)
    with open(os.path.join(out, "lean_parity.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    s, fz, t = doc["summary"], doc["fuzz"], doc["timing"]
    print(f"shipped {s['shipped']}, corpus {s['corpus_rejected']} rejected + {s['corpus_accepted']} "
          f"accepted, divergences {s['divergences']}; fuzz {fz['cases']}: verdict divergences "
          f"{fz['verdict_divergences']}; Lean/Python x{t['lean_over_python_min']}–x{t['lean_over_python_max']}"
          f"\nuptime before: {before['uptime']}\nuptime after:  {meta['after']['uptime']}"
          f"\narchived: {out}/lean_parity.{{log,json}}")
    return run.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("what", choices=["kernel", "parity"])
    ap.add_argument("--max-load", type=float, default=1.5, help="1-minute load average required to start")
    ap.add_argument("--wait", type=float, default=300.0, help="seconds to wait for a quiet machine")
    ap.add_argument("--mem-gb", type=float, default=9.0)
    ap.add_argument("--timeout", type=float, default=1800.0)
    args = ap.parse_args()
    return kernel(args) if args.what == "kernel" else parity(args)


if __name__ == "__main__":
    sys.exit(main())
