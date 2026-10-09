#!/usr/bin/env bash
# L1 — replay the whole Lean parity gate (`make lean-parity`):
#   1. build the Lean project: the `cnp-verify` executable (core Lean only) AND the library with
#      the specification layer, so that every statement type-checks against Mathlib;
#   2. export the adversarial corpus from the Python test-suite mutations (temporary directory);
#   3. compare Lean and Python on every shipped certificate, on the corpus, and on a seeded
#      differential fuzz (FUZZ cases, default 1000; FUZZ=0 to skip).
# Exit code 0 iff verdicts agree everywhere and rejection reasons agree on the corpus.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
PY="${PYTHON:-$ROOT/.venv/bin/python}"

cd "$HERE"
if [ ! -d .lake/packages/mathlib/.lake/build ]; then
  echo "Mathlib build cache missing: fetching it (several GB) — lake exe cache get"
  lake exe cache get
fi
lake build cnp-verify CnpVerify 2>&1 | { grep -v "declaration uses .sorry." || true; } | tail -3

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
"$PY" "$ROOT/scripts/export_mutations.py" "$TMP/mutations"

run_parity() {
  "$PY" "$ROOT/scripts/lean_parity.py" --bin "$HERE/.lake/build/bin/cnp-verify" \
    --mutations "$TMP/mutations" --fuzz "${FUZZ:-1000}" "$@"
}

# ARCHIVE=1 keeps the run (rule 7): benchmarks/results/<UTC>/lean_parity.log, never overwritten,
# with the commit, the state of the tree and the pinned versions.
if [ "${ARCHIVE:-0}" = "1" ]; then
  # read the state of the tree BEFORE creating the archive directory (which makes it dirty)
  DIRTY="$([ -n "$(git -C "$ROOT" status --porcelain)" ] && echo true || echo false)"
  OUT="$ROOT/benchmarks/results/$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir "$OUT"
  {
    echo "lean-parity run — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "commit: $(git -C "$ROOT" rev-parse HEAD)"
    echo "git_dirty_at_start: $DIRTY"
    echo "lean: $(lean --version)"
    echo "lake: $(lake --version)"
    echo "mathlib: $(git -C .lake/packages/mathlib rev-parse HEAD) ($(grep '^rev' lakefile.toml))"
    echo "python: $("$PY" --version)"
    echo "machine: $(uname -srm), $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)"
    echo "load average at start: $(sysctl -n vm.loadavg 2>/dev/null || uptime)"
    echo
  } > "$OUT/lean_parity.log"
  run_parity --markdown "$@" | tee -a "$OUT/lean_parity.log"
  echo "archived: $OUT/lean_parity.log"
else
  run_parity "$@"
fi
