"""S12 [L6] — the EXPORT CONTRACT switch: ship the reduced witness, embedded in full dim.

Until S11 every collision leaf was RE-SOLVED at full dimension to be exported, even when the
decision LP had already produced a witness on a strictly smaller problem. S12 flips the
default: when the reduced problem provably IS the full one restricted, the reduced witness is
EMBEDDED (zero exponents on the passive axes) instead of being recomputed. On the iiwa7
flagship that term goes from ~10 minutes to seconds.

What these tests actually guard (CLAUDE.md rule 1 — a contract change is where soundness dies
quietly, so nothing here trusts the new path):

  * the applicability test is a RUN-TIME test with the right truth table — in particular it
    says NO on S3, where A29 had to divide a ``(1+s^2)`` factor the slab tensor does not
    carry (``test_applicability_truth_table``);
  * the FALLBACK is really exercised, not just present in the source (``test_s3_*``);
  * where the embedding is the identity (a pair with no passive axis) it reproduces the old
    path leaf for leaf, coefficient for coefficient (``test_embedding_is_identity_*``) — the
    "same output" half of the contract;
  * a DELIBERATELY WRONG embedding is caught by the exact verifier, counted, and replaced by
    a re-resolved leaf, leaving a certificate that still verifies exactly
    (``test_forced_bad_embedding_*``) — the loud guard, tested rather than asserted.

``verify.py`` is untouched by this session (zero diff). That is not an aesthetic constraint:
it is *why* the switch is sound. The arbiter re-derives everything at full dimension with no
shared code, so a wrong embedding can only ever cost a rejection (⇒ ENGINE-PROOF / UNDECIDED),
never buy a false PROOF — the S8 argument, unchanged.
"""
from __future__ import annotations

import os

import pytest

from cnp import certificate, engine, scenes, verify

SCENES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scenes")
BACKEND = engine.ENGINE_BACKEND


def _load(name):
    sc, budget = scenes.load(os.path.join(SCENES, name + ".yaml"))
    prob = scenes.build_problem(sc, max_depth=budget.max_depth)
    return sc, budget, prob


def _certify(name):
    sc, budget, prob = _load(name)
    res = engine.solve(prob, budget=budget.engine_budget(), axis=budget.axis)
    cert = certificate.make_certificate(sc, res, verify_loop=True)
    return sc, res, cert


# --------------------------------------------------------------------------- #
# Task 1 — the run-time applicability test
# --------------------------------------------------------------------------- #

def test_applicability_truth_table():
    """The two clauses, on the scenes that exhibit each of them.

    ``S3_shoulder_elbow`` is the counter-example the switch exists to respect: its base roll
    is passive only AFTER A29 divides ``(1 + s2^2)`` out of ``D`` and every numerator. The
    slab tensor ``T = delta^2 - phi^2`` is NOT divided, so the full-dimensional
    ``g - mu*T`` is a different polynomial and the embedded multipliers would not certify it.
    Clause (i) must therefore say NO — and the leaf must re-solve at full dim."""
    _sc, _b, s3 = _load("S3_shoulder_elbow")
    chk = engine.embedding_applicable(s3)["PANEL"]
    assert chk.a29_removed == (2,), "premise: A29 divides the S3 roll factor"
    assert chk.passive == (2, 3) and chk.applicable is False
    assert "A29 divided" in chk.reason

    # ... while every scene whose passive axes are absent from the ORIGINAL tensors is
    # embeddable, whether it has passive axes (S2/S4) or none at all (S1/S2b).
    for name, expected_passive in (("S1_relais", ()), ("S2_peigne", (2,)),
                                   ("S2b_spatial3", ()), ("S4_iiwa_bin", (3, 4))):
        _sc, _b, prob = _load(name)
        checks = engine.embedding_applicable(prob)
        assert checks, name
        for pair, chk in checks.items():
            assert chk.applicable is True, f"{name}/{pair}: {chk.reason}"
            assert chk.a29_removed == () and chk.blocking == ()
            assert chk.passive == expected_passive, f"{name}/{pair}"


def test_applicability_clause_ii_is_the_exact_original_tensor_test():
    """Clause (ii) reads the ORIGINAL tensors, not the simplified ones.

    On S3 the SIMPLIFIED geometry is independent of the roll axis — that is the whole point of
    A29 — so a check written against ``_PairView`` geometry would wrongly report the axis as
    absent and green-light the embedding. The blocking set must be computed on the raw pair."""
    _sc, _b, s3 = _load("S3_shoulder_elbow")
    pair = s3.pairs[0]
    view = engine.pair_views(s3)[0]
    assert engine._tensor_depends(pair.D, 2)            # raw D carries the roll ...
    assert not engine._tensor_depends(view.D, 2)        # ... simplified D does not
    assert 2 in engine.embedding_applicable(s3)["PANEL"].blocking


# --------------------------------------------------------------------------- #
# Task 2 — the two export paths, and the counters that tell them apart
# --------------------------------------------------------------------------- #

def test_s3_falls_back_to_full_dim_reresolution():
    """S3: condition false ⇒ every collision leaf is RE-SOLVED (the fallback is exercised,
    not merely reachable), and the certificate verifies exactly as it always did."""
    _sc, _res, cert = _certify("S3_shoulder_elbow")
    ok, msg = verify.verify(cert)
    assert ok, msg
    st = cert["stats"]
    assert st["n_leaves_embedded"] == 0
    assert st["n_leaves_resolved"] == st["n_collision"] > 0
    assert st["n_embed_rejected"] == 0 and st["n_reresolve_failed"] == 0


@pytest.mark.parametrize("name", ["S2_peigne", "S4_iiwa_bin"])
def test_embedded_export_proves_and_verifies(name):
    """A scene with genuinely passive axes takes the embedded path for every collision leaf,
    the verdict is unchanged (PROOF), and the EXACT verifier accepts at full dimension."""
    _sc, res, cert = _certify(name)
    assert res.verdict == "PROOF"
    ok, msg = verify.verify(cert)
    assert ok, msg
    st = cert["stats"]
    assert st["n_leaves_embedded"] == st["n_collision"] > 0
    assert st["n_leaves_resolved"] == 0
    assert st["n_embed_rejected"] == 0                              # A32 extended
    assert st["n_reresolve_failed"] == 0                            # A32


@pytest.mark.parametrize("name", ["S2_peigne", "S4_iiwa_bin"])
def test_embedded_lambda_is_constant_along_passive_axes(name):
    """The embedding writes exponent 0 on every passive axis — the shipped multipliers are
    literally the reduced ones, read as full-dimensional polynomials."""
    _sc, _b, prob = _load(name)
    checks = engine.embedding_applicable(prob)
    _sc2, _res, cert = _certify(name)
    for lf in cert["leaves"]:
        if lf["status"] != "collision":
            continue
        passive = checks[lf["obstacle"]].passive
        assert passive, "premise: this scene has passive axes"
        for tensor in lf["lambda"]:
            for key in tensor:
                expo = [int(x) for x in key.split(",")]
                assert len(expo) == prob.n
                assert all(expo[i] == 0 for i in passive), (key, passive)


@pytest.mark.parametrize("name", ["S1_relais", "S2b_spatial3"])
def test_embedding_is_identity_when_no_axis_is_passive(name):
    """"Repli ⇒ même sortie", proved where it is provable in one process.

    When a pair has NO passive axis the reduced LP *is* the full LP, so the embedded export
    must reproduce the historical re-resolved leaf exactly — same cell, same rational lambda
    tensors, same mu, same margin string. Any drift here (a different LP assembly, a different
    rounding order) would show up as a coefficient mismatch."""
    sc, budget, prob = _load(name)
    checks = engine.embedding_applicable(prob)
    assert all(c.passive == () for c in checks.values()), "premise: no passive axis"
    res = engine.solve(prob, budget=budget.engine_budget(), axis=budget.axis)
    views = {v.pair.name: v for v in engine.pair_views(prob)}
    verts, D = certificate._body_numerators(sc)
    checked = 0
    for lf in res.leaves:
        if lf.status != "collision":
            continue
        embedded = certificate._embedded_collision_leaf(
            lf, views[lf.pair], prob, BACKEND, certificate.DEFAULT_MAX_DEN)
        resolved = certificate._collision_leaf(
            sc, lf, verts, D, BACKEND, certificate.DEFAULT_MAX_DEN)
        assert embedded == resolved, lf.cell
        checked += 1
    assert checked > 0


# --------------------------------------------------------------------------- #
# Task 3 (c) — a WRONG embedding must be rejected, counted, and replaced
# --------------------------------------------------------------------------- #

def _sabotage_passive_axis(monkeypatch):
    """Mutation 1 — write a NONZERO exponent on a passive axis.

    The first lambda's constant term is moved onto ``s_passive^1``. The polynomial is no
    longer constant along an axis the geometry ignores, and ``sum_k lambda_k == 1`` breaks as
    an exact identity — precisely what the verifier checks first."""
    real = certificate._embed_tensor

    def bad(t, active, n_full):
        out = real(t, active, n_full)
        passive = [i for i in range(n_full) if i not in active]
        if not passive:                       # nothing to corrupt on this pair
            return out
        origin = tuple([0] * n_full)
        if origin in out:
            spoiled = list(origin)
            spoiled[passive[0]] = 1
            out[tuple(spoiled)] = out.pop(origin)
        return out

    # corrupt only the FIRST tensor of each leaf: enough to break it, and it keeps the
    # rest of the export honest so the failure is attributable.
    state = {"n": 0}

    def patched(t, active, n_full):
        state["n"] += 1
        return bad(t, active, n_full) if state["n"] % 3 == 1 else real(t, active, n_full)

    monkeypatch.setattr(certificate, "_embed_tensor", patched)


def _sabotage_reuse_other_leaf(monkeypatch):
    """Mutation 2 — ship ANOTHER leaf's reduced witness.

    Each leaf's multipliers individually satisfy ``sum_k lambda_k == 1``, so this survives the
    identity check and can only be caught by the Bernstein positivity of ``g - mu*T`` ON THIS
    CELL. It is the mutation that actually exercises the per-leaf exact audit."""
    real = certificate._embedded_collision_leaf
    first = {}

    def patched(lf, view, problem, backend, max_den):
        leaf = real(lf, view, problem, backend, max_den)
        if "witness" not in first:
            first["witness"] = (leaf["lambda"], leaf["mu"])
            return leaf
        leaf["lambda"], leaf["mu"] = first["witness"]      # someone else's certificate
        return leaf

    monkeypatch.setattr(certificate, "_embedded_collision_leaf", patched)


@pytest.mark.parametrize("sabotage", [_sabotage_passive_axis, _sabotage_reuse_other_leaf],
                         ids=["nonzero-on-passive-axis", "lambda-of-another-leaf"])
def test_forced_bad_embedding_is_rejected_counted_and_replaced(monkeypatch, sabotage):
    """The guard, end to end: the exact verifier refuses the bad embedding, the leaf falls
    back to full-dimensional re-resolution, the rejection is COUNTED and made LOUD — and the
    certificate that comes out of it is still a fully valid, exactly verified PROOF.

    This is the S8 argument made mechanical: the worst a broken generator can do to the
    exported object is cost time. It cannot forge a proof, because the thing that says
    "proof" is ``verify.py``, which never learned about any of this."""
    sc, budget, prob = _load("S2_peigne")
    res = engine.solve(prob, budget=budget.engine_budget(), axis=budget.axis)
    n_collision = sum(1 for lf in res.leaves if lf.status == "collision")
    assert n_collision >= 2                                  # mutation 2 needs a second leaf

    sabotage(monkeypatch)
    with pytest.raises(certificate.EmbeddingRejected) as exc:
        certificate.make_certificate(sc, res, verify_loop=True)

    cert = exc.value.certificate
    assert cert is not None, "the loud failure must hand back the certificate it built"
    st = cert["stats"]
    assert st["n_embed_rejected"] == len(exc.value.rejected) > 0
    assert st["n_leaves_resolved"] >= st["n_embed_rejected"]  # every rejection fell back
    assert st["n_collision"] == n_collision                   # no leaf was silently dropped
    ok, msg = verify.verify(cert)
    assert ok, f"the fallback certificate must still verify exactly: {msg}"


def test_unsabotaged_run_of_the_same_scene_is_silent():
    """Control for the two mutations above: without sabotage the same scene exports every
    leaf by embedding, raises nothing, and reports zero rejections."""
    _sc, _res, cert = _certify("S2_peigne")
    assert cert["stats"]["n_embed_rejected"] == 0
    assert cert["stats"]["n_leaves_embedded"] == cert["stats"]["n_collision"]


# --------------------------------------------------------------------------- #
# The flagship, end to end on the real robot (the claim the paper quotes)
# --------------------------------------------------------------------------- #

IIWA7_CERTS = ["S6_iiwa_real_shelf", "usecase_binpicking_iiwa7", "usecase_capot_surete_iiwa7"]


@pytest.mark.parametrize("name", IIWA7_CERTS)
def test_archived_iiwa7_certificates_are_embedded_and_verify_exactly(name):
    """Rule 5, on the three SHIPPED iiwa7 certificates: what the reader re-counts is the
    artefact in the repo, so re-verify THAT — and assert it is the S12 artefact (every
    collision leaf embedded, nothing re-resolved, nothing rejected). Costs one exact
    verification each; no FK build, so it stays in the required suite."""
    cert = certificate.load(os.path.join(SCENES, name + ".cert.json"))
    ok, msg = verify.verify(cert)
    assert ok, msg
    sc, _ = scenes.load(os.path.join(SCENES, name + ".yaml"))
    match, why = scenes.scene_matches_cert(sc, cert)
    assert match, why
    st = cert["stats"]
    assert st["n_leaves_embedded"] == st["n_collision"] > 0
    assert st["n_leaves_resolved"] == 0
    assert st["n_embed_rejected"] == 0 and st["n_reresolve_failed"] == 0


@pytest.mark.slow
def test_real_iiwa7_flagship_certifies_by_embedding():
    """The headline case: the real iiwa7, certified end to end through the NEW contract.

    Four passive axes (s3..s6 are downstream of the certified link 3) are absent from the
    original ``D``, numerators and ``phi``, so the export ships the 3-dimensional decision
    witness instead of re-solving a 473 870-row LP. PROOF, exact verification, zero
    rejections — the same verdict as S11, reached the cheap way."""
    sc, _budget = scenes.load(os.path.join(SCENES, "S6_iiwa_real_shelf.yaml"))
    prob = scenes.build_problem(sc)
    checks = engine.embedding_applicable(prob)
    assert all(c.applicable for c in checks.values()), checks
    assert all(c.passive == (3, 4, 5, 6) for c in checks.values())

    res = engine.solve(prob, axis="margin")
    assert res.verdict == "PROOF"
    cert = certificate.make_certificate(sc, res, verify_loop=True)
    ok, msg = verify.verify(cert)
    assert ok, msg
    match, why = scenes.scene_matches_cert(sc, cert)
    assert match, why
    st = cert["stats"]
    assert st["n_leaves_embedded"] == st["n_collision"] > 0
    assert st["n_leaves_resolved"] == 0
    assert st["n_embed_rejected"] == 0 and st["n_reresolve_failed"] == 0
