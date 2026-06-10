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

.PHONY: setup test clean

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

clean:
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf src/*.egg-info *.egg-info
