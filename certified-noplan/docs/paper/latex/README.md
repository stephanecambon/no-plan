# docs/paper/latex — build notes

`paper.tex` (draft v0.3, deposited by Stéphane, a supervision document: Code does not edit it)
and `refs.bib`.

## Figures

`figures/` is a **symbolic link** to `../../../benchmarks/figures/paper/` (the repository's
`benchmarks/figures/paper/`, three levels up from this folder). The figures there are produced
by `make paper-figures` (S14): English labels, 300 dpi, no internal annotation codes, every
benchmark number read from the latest clean-tree `benchmarks/results/<stamp>/reproduce.json`
(`make reproduce`). `benchmarks/figures/paper/SOURCES.json` records which benchmark run,
certificate and scene each figure read.

| file expected by `paper.tex` | present | produced by |
|---|---|---|
| `figures/fig1.png` | yes | `scripts/make_paper_fig1.py` |
| `figures/cost_vs_active_dims.png` | yes | `scripts/make_paper_figures.py` |
| `figures/partition_E3.png` | yes | `scripts/make_paper_figures.py` |
| `figures/scene_S3_shoulder_elbow_sweep.png` | yes | `scripts/make_paper_figures.py` |
| `figures/scene_S3_shoulder_elbow_cspace.png` | yes | `scripts/make_paper_figures.py` |

If the link is lost (for instance after copying this folder elsewhere), copy the five PNGs into
a local `figures/` folder; missing figures fall back to a labelled placeholder
(`\figfallback` in `paper.tex`), so the document still compiles.

Three captions in `paper.tex` still describe the previous figures (see
`docs/paper/FACTCHECK-figs.md`): the "[Draft: …]" notes of Fig. 1, the partition figure and the
cost figure; the cost figure's "Dashed" curve (no longer drawn) and "k = 8 is not plotted" (it
now is); and the partition figure's right panel, which is now a zoom on the slab.

## Compiling

```
latexmk -pdf paper.tex
```

**Not tested locally in S14**: no TeX distribution (`latexmk`, `pdflatex`) is installed on the
development machine. The layout is a generic two-column `article`; switch `\documentclass` to
the target template at submission.

## Bibliography items still to settle

See `docs/paper/BIB-VERIFY-S14.md` for the S14 check. Corrections to apply to `refs.bib`
(by the supervision): fill the author fields of `feasibility2026` and `hypercube2026`; fix the
DOI of `magron2021jsc` and add its volume/pages; cite `magron2018realcertify` as the ACM
Communications in Computer Algebra article; add DOIs to `dantam2018`, `garrett2018` and
`magron2018putinar`.
