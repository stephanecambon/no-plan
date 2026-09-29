# docs/paper/latex — build notes

`paper.tex` (supervision version of 29/09/2026, finalised in S15), `refs.bib`, and `paper.bbl`
(generated from `refs.bib` with `plainnat`; regenerating it gives an identical file).

## Figures

`figures/` is a **symbolic link** to `../../../benchmarks/figures/paper/`. The five figures there
are produced by `make paper-figures`: English labels, 300 dpi, every benchmark number read from the
latest clean-tree `benchmarks/results/<stamp>/reproduce.json`; `SOURCES.json` records which run,
certificate and scene each figure read. All current timings in the text and in Table 2 come from the
same run (`docs/paper/TABLE-reproduce.md`).

## Compiling

```
tectonic paper.tex
```

(or `latexmk -pdf paper.tex` with a TeX Live distribution). Compiled in S15 with tectonic 0.17.0:
13 pages, no undefined citation or reference. The compiled PDF is archived as `../paper.pdf`.

## arXiv

- `../arxiv-submission.tar.gz` = `paper.tex` + `paper.bbl` + the five figures actually used, under
  `figures/`. Checked self-contained: extracted alone and compiled with TeX-only passes (no BibTeX,
  as arXiv does when `paper.bbl` is supplied), zero undefined references, same output as the full
  build.
- `../arxiv-abstract.txt` = the abstract as plain text for the arXiv form (limit 1 920 characters).
- `\ZENODODOI{}` in §7.8 is empty until the Zenodo DOI exists; once filled it adds
  "; archived on Zenodo, doi:…" to the repository sentence. Regenerate the archive afterwards.
