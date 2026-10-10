# certified-noplan — local CI.  `make setup` then `make test` must be green (G0').
#
# Rule 10 (CLAUDE.md): Homebrew Python 3.12 only (not system Python, not Anaconda),
# dedicated venv. The interpreter path is the Homebrew arm64 prefix; override with
#   make setup PYTHON=/path/to/python3.12
# if your Homebrew prefix differs.

PYTHON  ?= /opt/homebrew/opt/python@3.12/bin/python3.12
VENV    := .venv
VENV_PY := $(VENV)/bin/python
PYTEST  := $(VENV)/bin/pytest
STAMP   := $(VENV)/.installed
# `make setup LOCK=1` installs the exact versions of the reference run (requirements-lock.txt).
CONSTRAINTS := $(if $(LOCK),-c requirements-lock.txt,)

.PHONY: setup test test-fast test-slow bench-parallel figures benchmark reproduce paper-figures lean-parity lean-certs lean-kernel-bench clean

# Idempotent: re-running `make setup` does nothing unless pyproject.toml changed.
setup: $(STAMP)

$(STAMP): pyproject.toml requirements-lock.txt
	@test -x "$(PYTHON)" || { echo "ERROR: $(PYTHON) not found. Install with: brew install python@3.12  (or pass PYTHON=...)"; exit 1; }
	$(PYTHON) -m venv $(VENV)
	$(VENV_PY) -m pip install --upgrade pip
	# Drake is needed from S1 (ratfk). The sympy fallback (SPEC §9.4) lets the
	# suite degrade gracefully (importorskip) if the wheel ever fails to install.
	$(VENV_PY) -m pip install $(CONSTRAINTS) -e ".[drake,dev]"
	@touch $(STAMP)
	@echo "setup OK: $$($(VENV_PY) --version) in $(VENV)"

# The required exit gate (rule 13). Excludes `bench` — wall-clock timing benchmarks
# that need an idle machine and are NOT correctness tests (A42: test_parallel_speedup
# flaked 4x on busy desktops; the speedup claim lives in the bench target below).
test: setup
	$(PYTEST) -m "not bench"

# Fast daily subset (< 30 s, CLAUDE.md S3 task 6): skips the slow regression replays
# (E1/E2 SOS-SDP cross-check, the full E3/E4 b&b reproductions, parallel/resume).
# The FULL `make test` is the one required at every session exit (rule 13).
test-fast: setup
	$(PYTEST) -m "not slow and not bench" -q

# The slow replays on their own (handy when iterating on the engine).
test-slow: setup
	$(PYTEST) -m slow -q

# Wall-clock benchmarks (A42) — run DELIBERATELY on a quiet machine. Currently the
# >=3x parallel speedup check; the reference quiet ratio (~3.6x) is journalled (rule 7).
bench-parallel: setup
	$(PYTEST) -m bench -q

# Certified-partition figures for the regression scenes (S3 task 4 / V1 validation).
figures: setup
	$(VENV_PY) scripts/make_figures.py
	$(VENV_PY) scripts/make_scene_figures.py

# Benchmark harness (S7, gate G3'): time certify on the shipped scenes + the
# passive-dimension cost-model sweep, written to benchmarks/results/<UTC>/ (rule 7).
benchmark: setup
	$(VENV_PY) benchmarks/run_benchmark.py

# S14 — every row of the paper's summary table, ONE PROCESS PER ROW, on a CLEAN tree (the
# harness refuses a dirty tree: commit first). Writes benchmarks/results/<UTC>/reproduce.json
# and the certificate of every certified row (scenes/*.cert.json, scenes/wall/k*.cert.json),
# each re-checked by the stdlib-only verifier module and by `cnp verify <cert> <scene>`.
reproduce: setup
	$(VENV_PY) benchmarks/run_benchmark.py --reproduce

# S14 — publication figures (English, 300 dpi) into benchmarks/figures/paper/; every number
# drawn is read from the latest reproduce.json, never retyped.
paper-figures: setup
	$(VENV_PY) scripts/make_paper_figures.py

# L1 — Lean 4 checker (lean/, Lake project CnpVerify). Builds `cnp-verify`, exports the adversarial
# corpus from the test-suite mutations and compares Lean and Python verdicts on every shipped
# certificate and every mutation. NOT part of `make test` (needs elan + the Mathlib cache).
lean-parity: setup
	bash lean/check_all.sh

# L4 — certificates written as Lean terms (lean/Certs/). Checks that the generated files are up
# to date, re-checks IN THE LEAN KERNEL the staged proof of `check wallK3 = true` (several
# minutes, ~6 GB) and the per-scene theorems, checks that the parser's object equals each term,
# and audits the axioms. Needs elan + the Mathlib cache and python3 (stdlib only): no venv.
lean-certs:
	bash lean/check_certs.sh

# L4 — how far the kernel goes on each certificate (decide / decide +kernel / staged /
# native_decide), one process per attempt, under a time and a memory limit; archived in
# benchmarks/results/<UTC>/lean_kernel.{json,md} (rule 7). Quiet machine; about one hour.
lean-kernel-bench:
	python3 scripts/lean_kernel_bench.py

clean:
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf src/*.egg-info *.egg-info
