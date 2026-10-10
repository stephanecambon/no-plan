#!/usr/bin/env bash
# L4 — replay the gate of the certificates written as Lean terms (`make lean-certs`):
#   1. the generated terms (`Certs/*.lean`) are those `scripts/cert_to_lean.py` writes today
#      from the JSON certificates, and the generated staged proof (`Certs/WallK3Kernel.lean`)
#      is the one `CertStages.lean` writes today;
#   2. `lake build Certs`: the staged proof of `check wallK3 = true` is re-checked BY THE KERNEL
#      (several minutes, about 6 GB), with the `native_decide` counterparts;
#   3. `CertTermCheck.lean`: for each certificate, the object the binary's parser reads from the
#      JSON file is EQUAL to the generated term — and the control of that control: with one
#      number of one JSON file changed, the comparison must fail on that file;
#   4. the axiom audit (`scripts/lean_axioms.py`).
# Exit code 0 iff everything agrees. Needs elan and python3 (standard library only).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
PY="${PYTHON:-python3}"

cd "$HERE"
if [ ! -d .lake/packages/mathlib/.lake/build ]; then
  echo "Mathlib build cache missing: fetching it (several GB) — lake exe cache get"
  lake exe cache get
fi

echo "== 1. generated files are up to date"
"$PY" "$ROOT/scripts/cert_to_lean.py" --check
lake build +Certs.Staged +Certs.WallK3 +Certs.S3ShoulderElbow +Certs.S6IiwaRealShelf 2>&1 | tail -1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
lake env lean --run CertStages.lean wallK3 > "$TMP/WallK3Kernel.lean"
if cmp -s "$TMP/WallK3Kernel.lean" Certs/WallK3Kernel.lean; then
  echo "up to date  lean/Certs/WallK3Kernel.lean  <-  lake env lean --run CertStages.lean wallK3"
else
  echo "STALE       lean/Certs/WallK3Kernel.lean"; exit 1
fi

echo "== 2. lake build Certs (kernel evaluation of check wallK3: several minutes)"
lake build Certs 2>&1 | tail -3

echo "== 3. parsed object = generated term"
lake env lean --run CertTermCheck.lean "$ROOT"
# control of the control: delta 1/10 -> 1/11 in a COPY of wall/k3; the two other files untouched
mkdir -p "$TMP/root/scenes/wall"
cp "$ROOT/scenes/S3_shoulder_elbow.cert.json" "$ROOT/scenes/S6_iiwa_real_shelf.cert.json" "$TMP/root/scenes/"
"$PY" - "$ROOT/scenes/wall/k3.cert.json" "$TMP/root/scenes/wall/k3.cert.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["delta"] == "1/10", d["delta"]
d["delta"] = "1/11"
json.dump(d, open(sys.argv[2], "w"))
PYEOF
set +e
lake env lean --run CertTermCheck.lean "$TMP/root" > "$TMP/control.log"
STATUS=$?
set -e
if [ "$STATUS" = "1" ] && grep -q "wall/k3.cert.json: parsed object = term: false" "$TMP/control.log" \
   && grep -q "MISMATCH on 1 certificate" "$TMP/control.log"; then
  echo "control of the control: a changed delta in wall/k3 is detected (exit 1, 1 mismatch): OK"
else
  echo "control of the control FAILED: the perturbed file was not flagged"; cat "$TMP/control.log"; exit 1
fi

echo "== 4. axiom audit"
"$PY" "$ROOT/scripts/lean_axioms.py"
