# BIB-VERIFY-S14 — the [VERIFY] entries of `docs/paper/latex/refs.bib`

**Session S14 (Claude Code), 10 September 2026.** Read-only check; `refs.bib` is not modified by
Code (supervision document). Method: arXiv abstract pages and Crossref DOI records. A background
agent did a first pass (arXiv API, Crossref, the ISSAC 2018 software page, the Polak PDF); **every
item marked "confirmed in session" below was re-fetched directly by the session** (rule 9, A28/A51).

## 1. Entries carrying a VERIFY marker

| key (refs.bib line) | refs.bib today | result | verified data | source |
|---|---|---|---|---|
| `feasibility2026` (l.132-137) | author = "[Authors to be read from the PDF]" | **FOUND — fill authors** (confirmed in session) | **Sajid Ansari, Arthi, Girish Varma, Antony Thomas** ("Arthi" is a single name on arXiv). Title: *Learning Motion Feasibility from Point Clouds in Cluttered Environments*. Submitted 25 June 2026 (v1). | https://arxiv.org/abs/2606.26700 |
| `hypercube2026` (l.227-232) | author placeholder; "exact rational certificate with archived verification scripts" | **FOUND — fill author; description CONFIRMED** (confirmed in session) | **Sven Polak** (sole author). Title as in refs.bib. Submitted 29 May 2026. Ancillary files: two Julia exact-verification scripts (coefficient matching, PSD principal minors) and rational certificate data files. | https://arxiv.org/abs/2605.31169 |
| `magron2021jsc` (l.211-216) | DOI 10.1016/j.jsc.2021.03.001, "[VERIFY volume/pages]" | **MISMATCH — WRONG DOI** (confirmed in session) | Victor Magron, Mohab Safey El Din, *On exact Reznick, Hilbert-Artin and Putinar's representations*, **Journal of Symbolic Computation 107, 221–250 (2021), DOI 10.1016/j.jsc.2021.03.005**. The DOI in refs.bib (…03.001) is M. Ansola, A. Díaz-Cano, M.A. Zurro, *Semialgebraic sets and real binary forms decompositions*, JSC 107, 209–220 — a different paper. | https://api.crossref.org/works/10.1016/j.jsc.2021.03.005 ; https://api.crossref.org/works/10.1016/j.jsc.2021.03.001 |
| `dantam2018` (l.12-18) | IJRR 37(10):1134–1151, 2018 | **FOUND — matches** (confirmed in session) | Neil T. Dantam, Zachary K. Kingston, Swarat Chaudhuri, Lydia E. Kavraki, *An incremental constraint-based framework for task and motion planning*, IJRR 37(10), 1134–1151, 2018. Add **DOI 10.1177/0278364918761570**. | https://api.crossref.org/works/10.1177/0278364918761570 |
| `garrett2018` (l.20-26) | FFRob, IJRR 37(1):104–136, 2018 | **FOUND — matches** (confirmed in session) | Caelan Reed Garrett, Tomás Lozano-Pérez, Leslie Pack Kaelbling, *FFRob: Leveraging symbolic planning for efficient task and motion planning*, IJRR 37(1), 104–136, 2018 (online 12 Nov 2017). Add **DOI 10.1177/0278364917739114**. It is FFRob, not PDDLStream. | https://api.crossref.org/works/10.1177/0278364917739114 |

## 2. Other entries checked on the way (the 2026-09-10 exact-SOS additions)

| key | result | verified data | source |
|---|---|---|---|
| `magron2018realcertify` (l.199-204) | **MISMATCH — citable form** (confirmed in session) | Presented at ISSAC 2018 as a software presentation; the published record is an **article**: Victor Magron, Mohab Safey El Din, *RealCertify: a Maple package for certifying non-negativity*, **ACM Communications in Computer Algebra 52(2), 34–37 (2018), DOI 10.1145/3282678.3282681** (arXiv:1805.02201). Cite as `@article`. | https://api.crossref.org/works/10.1145/3282678.3282681 |
| `magron2018putinar` (l.205-210) | **FOUND — incomplete** (confirmed in session) | *On Exact Polya and Putinar's Representations*, Proc. ISSAC 2018 (ACM), **pp. 279–286, DOI 10.1145/3208976.3208986**. | https://api.crossref.org/works/10.1145/3208976.3208986 |
| `henrion2025notsos` | FOUND — matches (agent pass) | Didier Henrion, sole author; arXiv:2509.01382, 1 Sep 2025. | https://arxiv.org/abs/2509.01382 |
| `henrion2025stengle` | FOUND — matches (agent pass) | Didier Henrion, sole author; arXiv:2512.19141, 22 Dec 2025. | https://arxiv.org/abs/2512.19141 |
| `peyrl2008` | FOUND — matches (agent pass) | TCS 409(2), 269–281; DOI 10.1016/j.tcs.2008.09.025. | Crossref |
| `kaltofen2008` | FOUND — matches (agent pass) | ISSAC 2008, pp. 155–164; DOI 10.1145/1390768.1390792. | Crossref |

## 3. Notes for the supervision

1. **`magron2021jsc` would send readers to the wrong paper** as written. This is the one item
   that must change before circulation.
2. **`feasibility2026` is learning work, not a proof method**: per its abstract it trains
   classifiers to predict grasp/motion feasibility (a 2.7M-label benchmark). Cite it as related
   learning work only, never as an infeasibility-proof method. Its last author, Antony Thomas,
   shares a name with the first author of `thomas2025`; whether it is the same person was not
   checked.
3. **Limits of this pass**: the 2606.26700 PDF was not opened (above the fetch size limit); its
   author list comes from the arXiv abstract page (session) and the arXiv API (agent), which
   agree. Entries without a VERIFY marker that lack pages or volume (`varava2021`,
   `dai2024ciris`, `amice2022wafr`) were not audited. The A51 "neighbours' last 12 months" sweep
   was not part of this task.
