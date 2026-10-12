# CHANGES-v2.md — what version 2 changes, and on what evidence

Version 1 = the 3 October 2026 revision after first-read comments from two colleagues (its blue marks are now plain,
macro `\vone`). Version 2 marks = macro `\new` (blue in `paper-v2-highlighted.pdf`). Nothing in the Experiments tables
changed; no number was retyped from memory.

## Title, abstract, contributions
- Title: "…, with a Verifier Proved Sound in Lean". Author line: "Version 2, 12 October 2026".
- Abstract (+1 sentence, 1 916 characters, under arXiv's 1 920): second verifier in Lean 4, soundness theorem under the three
  standard axioms, agreement on 13 certificates + 48-case corpus + 1 000 fuzz, one scene evaluated in the kernel.
- Intro: one sentence after the EGC paragraph; new contribution **(C5)** (Lean verifier, numbers from LEAN-NOTES (d)).

## Related work
- New paragraph "Machine-checked positivity": Muñoz & Narkawicz 2013 (PVS), Solovyev & Hales 2013 (HOL Light), Magron,
  Allamigeon, Gaubert & Werner 2015 (Coq), Martin-Dorel & Roux 2017 (ValidSDP, Coq); Wang & Abdulaziz 2025 (Isabelle/HOL,
  temporal planning — adjacent, abstract-level); "after a limited search, no machine-checked verifier of disconnection
  certificates for geometric motion planning". All references from LEAN-NOTES (e) (A28 pass by Code, 2026-10-10);
  `lean4` and `mathlib2020` checked by the supervision 2026-10-12. Lean 4 entry cited without page numbers (not read).

## Method (§3) — the five points of the L4 relecture + two dialogue points
1. §3.1: a certificate concerns **one** certified body; "the certified body" in the claim.
2. §3.2: per-joint frame convention clause (axis in the preceding link's frame, translate then rotate, right-composition
   along joints 0..ℓ inclusive, k-th unlocked joint reads s_k) — the convention the Lean reference definitions fix.
3. §3.3: "typically a single joint coordinate" → "in all thirteen, a single joint coordinate, φ = s_1 or s_2, chosen by the
   scene author" (Code's reading of the 13 `phi.coeffs`, DIALOGUE-2 tour 1; s_1 on ten, s_2 on the three iiwa7).
4. §3.6: "Different pairs have different passive sets" → pairs differing in their body; with one body per certificate all
   pairs share the passive set.

## Theorem (§4)
- Theorem 1: "a certified body … on a named link"; conclusion "keeps **the certified body** out of every obstacle"
  (matches the Lean `CollisionFree`).
- New paragraph "Three kinds of hypotheses" (soundness / meaning / agreement) — from LEAN-NOTES (c) findings 1–4;
  includes the untested "start/goal ∈ box" condition (D89).
- New "Remark (sides, not points)": region-to-region consequence, stated as a remark, explicitly NOT formalised
  (Code estimates ≈25 lines; not done).
- New "Joint angles and s": the q↔s homeomorphism remark, explicitly not formalised.
- Restrictions: the iiwa7 scenes declare ±70° (active) / ±143° (passive) against ±170°/±120° limits in the Drake model
  (box read from `S6_iiwa_real_shelf.cert.json`: s ∈ ±7/10 → 69.98°, ±3 → 143.1°; limits read by Code in the Drake SDF,
  `benchmarks/results/20261011T080711Z/rail_wrist.json`).

## §5 verifier
- New paragraph "A second verifier" pointing to §6.

## NEW §6 "A verifier proved sound in Lean" (`section-lean.tex`, ≈1.5 pages)
- 6.1 What was built (1 087 / 2 501 lines, 145 theorems, 19 obligations, 0 sorry, 3 axioms).
- 6.2 The two statements: `soundness` quoted verbatim from `Soundness.lean:576-580`; `soundness_ref` and the reference
  definitions in words; the eight fields the statement reads; the relecture of the definitions (A54); what the statement
  does not say (s-space, one body, touching, soundness only).
- 6.3 What soundness depends on (A53): findings 1–4 of LEAN-NOTES (c).
- 6.4 From the theorem to a binary, and for one scene to a theorem: trust base; wall/k3 kernel proof (34 stages,
  102.8 s, 101.6 s kernel, 5.63 GiB); `decide` fails; single kernel evaluation > 9 GiB; S3/S6 out of reach (quadratic
  arrays ×25–30 vs ×5); `native_decide` kept apart.
- 6.5 Agreement measured: 13 PROOF both; corpus 48/48; fuzz 498/487/15/0; FK parity 1 299 values; **Table 2** (both
  checkers, same run, 13 rows, totals 16.702 s / 13.947 s, ×0.83); CI 10 min 8 s, kernel proof re-checked in 200 s.
- 6.6 What this changes (1 061 agreeing inputs = 13 + 48 + 1 000).

## Limitations, provenance, objections
- Limitations: new paragraph "Formalisation" (kernel twin of the checker; remark and q↔s not yet formalised; prismatic
  absent from both verifiers).
- Provenance: Version 2 sentence (three Lean sessions from 19 obligations; definitions re-read by the supervising
  system; numbers from two archived quiet runs; four prior-work references checked, one author order corrected, one
  non-existent reference removed).
- Objections: three new entries ("A Lean proof only proves what it states", "Why keep the Python verifier", "native_decide
  would have proved every scene").

## Not changed, deliberately
- Experiments tables and figures (no new engine run); scope (§6 cost model) and the sealed-wall numbers.
- The point-to-point theorem is kept as the main statement because that is what is formalised.

## Open before a preprint
- Decide the title's wording ("Proved Sound in Lean" vs "Machine-Checked") — current choice is the precise one.
- If Code formalises the sides-not-points corollary (≈25 lines by its estimate), promote the Remark to a Corollary and
  say so in §6.
- `lean4` page numbers (LNCS 12699) to be read from the Springer page before submission.
- arXiv endorsement still pending; Zenodo DOI for the repository at the tagged commit.
