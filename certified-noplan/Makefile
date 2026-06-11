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

.PHONY: setup test test-fast test-slow figures clean

# Idempotent: re-running `make setup` does nothing unless pyproject.toml changed.
setup: $(STAMP)

$(STAMP): pyproject.toml
	@test -x "$(PYTHON)" || { echo "ERROR: $(PYTHON) not found. Install with: brew install python@3.12  (or pass PYTHON=...)"; exit 1; }
	$(PYTHON) -m venv $(VENV)
	$(VENV_PY) -m pip install --upgrade pip
	# Drake is needed from S1 (ratfk). The sympy fallback (SPEC §9.4) lets the
	# suite degrade gracefully (importorskip) if the wheel ever fails to install.
	$(VENV_PY) -m pip install -e ".[drake,dev]"
	@touch $(STAMP)
	@echo "setup OK: $$($(VENV_PY) --version) in $(VENV)"

test: setup
	$(PYTEST)

# Fast daily subset (< 30 s, CLAUDE.md S3 task 6): skips the slow regression replays
# (E1/E2 SOS-SDP cross-check, the full E3/E4 b&b reproductions, parallel/resume).
# The FULL `make test` is the one required at every session exit (rule 13).
test-fast: setup
	$(PYTEST) -m "not slow" -q

# The slow replays on their own (handy when iterating on the engine).
test-slow: setup
	$(PYTEST) -m slow -q

# Certified-partition figures for the regression scenes (S3 task 4 / V1 validation).
figures: setup
	$(VENV_PY) scripts/make_figures.py
	$(VENV_PY) scripts/make_scene_figures.py

clean:
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf src/*.egg-info *.egg-info
