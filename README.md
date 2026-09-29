# Exactly Verifiable Infeasibility Certificates for Robot Motion Planning

Code, certificates and benchmark data for the paper of the same title
(Stéphane Cambon, Cambon AI, 2026).

When a motion planner fails, it produces no evidence that no path exists. This project
produces that evidence: an **infeasibility certificate** for an articulated arm — start and
goal lie in different connected components of the free configuration space, within a declared
joint box — that an **independent 499-line verifier re-checks in exact rational arithmetic**,
importing nothing beyond the Python standard library and nothing from the generator. No
semidefinite program enters the trust chain; the LP solver, the collision checker and the
generator are not trusted.

What is proven, and what is not:

- The theorem is about the robot and obstacles **declared in the certificate**: serial revolute
  chains, a joint box within one turn (no wrap-around), static polytopal obstacles, certified
  bodies that are convex hulls of rational vertices. A separate cross-check ties the declaration
  to the authored scene file; tying the scene to a physical cell is a human responsibility.
- The KUKA iiwa7 kinematics are exact as an internal object and reproduce the published URDF to
  2·10⁻⁶ m at the flange — not "the exact iiwa", since no such description exists.
- The method is **sound, not complete**. Its verdicts are `PROOF` (exactly verified),
  `ENGINE-PROOF` (accepted by the generator, exact verification unavailable for that scene class,
  always flagged) and `UNDECIDED`. **`UNDECIDED` never means "infeasible", and it never means
  "feasible" either.**
- The disconnections certified at low cost are *proximal* (a body early in the chain is trapped
  whatever the downstream joints do). This is a selection effect of the method, stated as its
  scope in the paper.

## Verify a certificate in one command

From a clone of this repository, with any Python ≥ 3.9 and **no package installed**:

```bash
cd certified-noplan
python3 -S -I -c "import sys; sys.path.insert(0, 'src'); from cnp.verify import verify_file; print(verify_file('scenes/S6_iiwa_real_shelf.cert.json'))"
```

Expected output (about 2 s with Python 3.12, about 11 s with the macOS system Python 3.9):

```
(True, 'PROOF verified exactly: 2 leaves (2 collision, 0 outside); start/goal separated by the slab |phi| <= 1/5.')
```

`-S -I` disables site-packages and the user environment: the verifier runs on the standard
library alone (`json`, `fractions`, `math.comb`). This is the 7-DOF iiwa7 flagship certificate
of the paper. Every certificate in `certified-noplan/scenes/` (including `scenes/wall/`) can be
checked the same way.

The command-line form adds a field-by-field cross-check of the certificate's declared geometry
against the authored scene file (it parses YAML, so it needs the package installed by `make setup`,
see below):

```bash
.venv/bin/cnp verify scenes/S6_iiwa_real_shelf.cert.json scenes/S6_iiwa_real_shelf.yaml
```

## Reproduce the paper's table

```bash
cd certified-noplan
make setup        # venv + pip install -e ".[drake,dev]"
make test         # full test suite (correctness only; no timing assertions)
make reproduce    # every row of the summary table, one process per row
make paper-figures
```

Prerequisites: Python 3.12 (the Makefile defaults to Homebrew's on macOS arm64; pass
`make setup PYTHON=/path/to/python3.12` elsewhere). `make setup` installs NumPy, SciPy, SymPy,
HiGHS (`highspy`), PyYAML, matplotlib and Drake; Drake is only needed to re-derive the frozen
iiwa7 kinematics and link hull from Drake's model.

`make reproduce` refuses to run on a dirty working tree (commit first). It writes
`benchmarks/results/<UTC stamp>/reproduce.json` — commit hash, clean-tree flag, machine, package
versions, load average — regenerates the certificate of every row, and re-proves each one twice:
with `verify_file` under `python -S -I`, and with `cnp verify <cert> <scene>`. Expect about
30 minutes on a laptop (27 minutes on an Apple M4), about 7 of them the deliberately over-budget
`k = 8` point (UNDECIDED on a 300 s budget). Timings depend on the machine; verdicts and certificates do not (a fresh clone with newer
NumPy, SciPy and HiGHS releases regenerated all twelve certificates byte for byte). Package versions
are not pinned: the versions of each run are recorded in its `reproduce.json`.

## Repository map

All paths below are under `certified-noplan/`.

| What | Where |
|---|---|
| The exact verifier (the trust anchor) | `src/cnp/verify.py` |
| Generator: rational FK, witnesses, branch-and-bound, export | `src/cnp/ratfk.py`, `witness.py`, `engine.py`, `certificate.py` |
| Scene parser and scene↔certificate cross-check | `src/cnp/scenes.py` |
| Command line (`cnp certify`, `cnp verify`, `cnp show`, `cnp viz`) | `src/cnp/cli.py` |
| Scenes (YAML) and their certificates (`*.cert.json`) | `scenes/`, sealed synthetic family in `scenes/wall/` |
| Frozen iiwa7 chain and link-3 hull (rational) | `scripts/iiwa7_chain.json`, `scripts/iiwa7_body_link3.json` |
| Benchmark harness | `benchmarks/run_benchmark.py` |
| Dated benchmark results (never overwritten) | `benchmarks/results/<stamp>/` |
| Paper figures (and the JSON each one read) | `benchmarks/figures/paper/`, `SOURCES.json` |
| Interactive 3-D pages of the iiwa7 scenes | `benchmarks/figures/share/*.html` |
| Paper source | `docs/paper/latex/` |
| Tests, including adversarial certificate mutations | `tests/` |
| Specification | `SPEC.md` |

`scenes/S5_iiwa_shelf.cert.json` is an earlier iiwa-*like* benchmark kept for the record; it is
not one of the paper's rows.

## Provenance

The work was carried out with AI coding assistants under human direction: an autonomous coding
agent implemented it in sessions from a written specification, a second AI system reviewed the
sessions, and every gate, scene validation and design decision was signed by the author, who
takes full responsibility for the result. The verifier is the trust anchor precisely because the
generation pipeline is not to be trusted.

The full record is in the repository: `CLAUDE.md` (the binding rules and session plan given to the
coding agent), `JOURNAL.md` (every session, supervision review, human validation and decision,
dated), `DECISION-G2.md` (the signed go/no-go), and the git history itself. **These documents are
written in French.** The fact-checks of the paper against the code and the benchmark files are in
`docs/paper/`.

## License

The code is released under the MIT License (see `LICENSE`). The paper is distributed by arXiv
under its own license.

## Citation

If you use this work, please cite the paper and, for the code and data, the archived release
(see `CITATION.cff`):

```bibtex
@misc{cambon2026certificates,
  author       = {Cambon, St{\'e}phane},
  title        = {Exactly Verifiable Infeasibility Certificates for Robot Motion Planning},
  year         = {2026},
  howpublished = {arXiv preprint (identifier to be added)},
  note         = {Code and data: \url{https://github.com/stephanecambon/no-plan}, doi: to be added}
}
```
