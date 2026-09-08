"""cnp — command-line interface.

Three commands, three honest verdicts (CLAUDE.md rules 5/6, annotation A17):

* ``cnp certify <scene.yaml> [-o cert.json]`` — solve a scene end-to-end and emit an
  exact-rational certificate. Verdicts:
    - **PROOF**       — engine proved the disconnection AND the independent exact
                        verifier (:mod:`cnp.verify`) re-checked the certificate;
    - **ENGINE-PROOF** — the engine proved it, but exact verification is unavailable
                        for this scene (a robot configuration the verifier does not yet
                        support — e.g. q*≠0, which needs an irrational Rot(angle) — or a
                        leaf that would not round to an exactly-feasible certificate).
                        ALWAYS printed with its warning: NOT a verified proof. Since S9
                        (G3'b) the planar AND spatial revolute builtins at q*=0 are PROOF,
                        and since S9c so are scenes with LOCKED joints (exact cos/sin);
    - **UNDECIDED**   — no certificate at the given budget (NOT a proof of feasibility).
* ``cnp verify <cert.json> [scene.yaml]`` — run the untrusted exact verifier; if a
  scene file is given, also cross-check that the certificate states the same problem.
* ``cnp viz <cert.json> <scene.yaml> [--out DIR]`` — le pack de figures STANDARD d'un
  certificat (S11, D10/A11) : coupe C-space (axes nommés PHYSIQUEMENT), sweep fidèle de la
  silhouette du corps certifié, et **partition slab-aware honnête** (plein = ce que le
  théorème prouve, hachuré = la partie hors-dalle où il ne dit rien, frontière ``|φ|=δ``
  tracée). ``--meshcat`` ouvre en plus la vue 3-D de la scène.
* ``cnp show <scene.yaml> [--config start|goal|sweep]`` — minimal Meshcat view of the
  scene (robot at start/goal, obstacles) for visual design inspection (SPEC §6, V3);
  ``--interactive OUT.html`` exports a self-contained interactive widget for a spatial
  scene (sliders, live collision, ghosts, escape-attempt buttons — A24); ``--png OUT``
  saves a 2-D top-down figure for a planar scene.
"""
from __future__ import annotations

import argparse
import sys

from . import verify as _verify


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #

def _cmd_verify(args) -> int:
    from . import certificate as _cert
    cert = _cert.load(args.cert)
    ok, msg = _verify.verify(cert)
    if ok and args.scene is not None:
        from . import scenes as _scenes
        scene, _ = _scenes.load(args.scene)
        match, why = _scenes.scene_matches_cert(scene, cert)
        if not match:
            ok, msg = False, why
    print(("OK    — " if ok else "REJECT — ") + msg)
    if ok:
        print("verdict: PROOF (verified in exact arithmetic"
              + (" + scene cross-check)" if args.scene is not None else ")"))
        import math
        from fractions import Fraction as _F
        lims = " · ".join(
            f"q{i} {round(math.degrees(2*math.atan(float(_F(lo)))))}…"
            f"{round(math.degrees(2*math.atan(float(_F(hi)))))}°"
            for i, (lo, hi) in enumerate(cert.get("box", [])))
        print("  hypotheses (SPEC §2) : limites articulaires " + lims
              + " (within ±180° => pas de wrap-around) ; "
              + ", ".join(cert.get("assumptions", [])))
        return 0
    print("verdict: UNDECIDED (certificate not verified; NOT a proof of feasibility)")
    return 1


# --------------------------------------------------------------------------- #
# certify
# --------------------------------------------------------------------------- #

def _print_assumptions(scene) -> None:
    """A25: every PROOF / ENGINE-PROOF reminds its hypotheses (SPEC §2), including the
    EXPLICIT joint limits in degrees — the proof is only as strong as these premises."""
    from . import viz as _viz
    print("  hypotheses (SPEC §2, rappelees a chaque preuve) :")
    print("    - " + _viz.limits_caption(scene) + " ; toutes within (-180,180) deg => "
          "pas de wrap-around")
    print("    - obstacles statiques ; corps robot = polytopes convexes ; "
          "geometrie de scene exacte (rationnels)")


def _cmd_certify(args) -> int:
    from . import certificate as _cert
    from . import engine as _engine
    from . import scenes as _scenes

    scene, budget = _scenes.load(args.scene)
    problem = _scenes.build_problem(scene, max_depth=budget.max_depth)
    result = _engine.solve(problem, budget=budget.engine_budget(), axis=budget.axis)
    counts = result.counts()
    print(f"engine: verdict {result.verdict}, {counts['n_leaves']} leaves "
          f"{counts['status']}")

    if result.verdict != "PROOF":
        print("verdict: UNDECIDED (no certificate at the given budget; NOT a proof "
              "of feasibility)")
        if result.failed:
            print(f"  {len(result.failed)} undecided cell(s) exported for diagnosis")
        return 1

    if not _scenes.is_exactly_verifiable(scene):
        print("verdict: ENGINE-PROOF (engine proved the disconnection; the independent "
              "EXACT verifier does not support this scene's robot configuration — "
              f"{scene.robot.kind!r} with q*≠0 needs irrational Rot(angle); "
              "planar/spatial at q*=0, incl. locked joints (exact cos/sin), are PROOF)")
        print("  WARNING: this is NOT an exact-arithmetic-verified proof (rule 5).")
        _print_assumptions(scene)
        return 0

    try:
        cert = _cert.make_certificate(scene, result, verify_loop=True)
    except ValueError as exc:
        print("verdict: ENGINE-PROOF (engine proved the disconnection; the certificate "
              "could not be rounded to an exactly-verifiable form)")
        print(f"  WARNING: NOT exact-verified (rule 5): {exc}")
        return 0

    out = args.out or _default_cert_path(args.scene)
    _cert.save(cert, out)
    ok, msg = _verify.verify(cert)              # independent re-check (defence in depth)
    if not ok:                                  # pragma: no cover - verify_loop guarantees ok
        print(f"verdict: ENGINE-PROOF (cert written to {out} but exact verify rejected: "
              f"{msg})")
        return 0
    print(f"certificate written to {out}")
    print(f"verdict: PROOF — {msg}")
    _print_assumptions(scene)
    return 0


def _default_cert_path(scene_path: str) -> str:
    base = scene_path.rsplit("/", 1)[-1]
    base = base[:-5] if base.endswith(".yaml") else base
    return f"{base}.cert.json"


# --------------------------------------------------------------------------- #
# show
# --------------------------------------------------------------------------- #

def _cmd_show(args) -> int:
    from . import scenes as _scenes
    from . import viz as _viz

    scene, _ = _scenes.load(args.scene)
    if args.interactive is not None:            # self-contained interactive HTML (A24)
        active = None                           # the distal-redundancy escape needs active dims
        if scene.robot.kind == "spatial_revolute":
            try:
                from . import engine as _engine
                prob = _scenes.build_problem(scene)
                active = _engine._global_active(_engine.pair_views(prob), prob)
            except Exception:                   # viz must never fail on an engine hiccup
                active = None
        # le modèle de corps suit la GÉOMÉTRIE de la scène : un corps à K>2 sommets exige
        # la coque + GJK (A43) — un rendu segment mentirait sur une silhouette réelle.
        mode = args.body_mode or ("hull" if len(scene.hull_vertices) > 2 else "segment")
        path = _viz.export_interactive_html(scene, args.interactive,
                                            title=f"scene {args.scene}", active_dims=active,
                                            body_mode=mode)
        print(f"interactive HTML written to {path} (open it in a browser; no server)")
        return 0
    if args.png is not None:                    # 2-D top-down figure (planar), no server
        path = _viz.save_planar_figure(scene, args.png,
                                       title=f"scene {args.scene}")
        print(f"figure written to {path}")
        return 0
    url = _viz.show_scene(scene, config=args.config)
    print(f"Meshcat: {url}")
    if args.config == "both":
        print(f"showing scene {args.scene!r}: start (blue) and goal (green) in one "
              "view (Ctrl-C to stop the server)")
    elif args.config == "sweep":
        print(f"showing scene {args.scene!r}: start->goal sweep, colliding poses in "
              "red (Ctrl-C to stop the server)")
    else:
        print(f"showing scene {args.scene!r} at config {args.config!r} "
              "(Ctrl-C to stop the server)")
    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


# --------------------------------------------------------------------------- #
# viz  (S11 — pack de figures standard d'un certificat ; D10 + A11)
# --------------------------------------------------------------------------- #

def _cmd_viz(args) -> int:
    import os
    from . import certificate as _cert
    from . import scenes as _scenes
    from . import viz as _viz

    cert = _cert.load(args.cert)
    scene, _ = _scenes.load(args.scene)
    match, why = _scenes.scene_matches_cert(scene, cert)
    if not match:                       # une figure ne doit jamais illustrer un autre problème
        print(f"error: la scène ne correspond pas au certificat — {why}", file=sys.stderr)
        return 2
    ok, msg = _verify.verify(cert)
    print(f"certificat : {'OK (exact)' if ok else 'REJETÉ'} — {msg}")

    os.makedirs(args.out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.scene))[0]
    bdim = _viz._barrier_dim(scene)
    other = next(i for i in range(scene.robot.n) if i != bdim)
    oracle = _scenes.convex_collision_oracle(scene)
    caption = _viz.limits_caption(scene)

    paths = [_viz.save_cspace_figure(
        scene, oracle, os.path.join(args.out, f"{stem}_cspace.png"),
        axes=(bdim, other), n=args.grid, axis_labels=_viz._axis_labels(scene, (bdim, other)),
        footer=caption,
        title=f"{stem} — coupe C-space (gris = collision ; le cadre = les limites)")]
    paths.append(_viz.save_hull_sweep_figure(
        scene, oracle, os.path.join(args.out, f"{stem}_sweep.png"), n=11, project=(0, 2),
        footer=caption,
        title=f"{stem} — sweep start→goal, silhouette FIDÈLE du corps certifié (A20)"))
    paths.append(_viz.save_partition_figure(
        scene, cert["leaves"], os.path.join(args.out, f"{stem}_partition.png"),
        axes=(bdim, other), n=args.grid, footer=caption, oracle=oracle,
        title=f"{stem} — partition certifiée slab-aware ({cert['stats']['n_leaves']} feuilles)"))
    for pth in paths:
        print("wrote", pth)

    if args.meshcat:
        url = _viz.show_scene(scene, config="both")
        print(f"Meshcat: {url}  (Ctrl-C pour arrêter)")
        try:
            import time
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cnp",
                                description="certified-noplan: disconnection "
                                            "certificates for motion planning")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verify", help="independently verify a certificate (exact)")
    v.add_argument("cert", help="path to the JSON certificate")
    v.add_argument("scene", nargs="?", default=None,
                   help="optional scene file to cross-check the embedded problem")
    v.set_defaults(func=_cmd_verify)

    c = sub.add_parser("certify", help="solve a scene end-to-end and emit a certificate")
    c.add_argument("scene", help="path to the YAML scene")
    c.add_argument("-o", "--out", default=None,
                   help="certificate output path (default: <scene>.cert.json)")
    c.set_defaults(func=_cmd_certify)

    z = sub.add_parser("viz", help="standard figure pack for a certificate (C-space, "
                                   "sweep, slab-aware partition)")
    z.add_argument("cert", help="path to the JSON certificate")
    z.add_argument("scene", help="path to the YAML scene (cross-checked against the cert)")
    z.add_argument("--out", default="benchmarks/figures", help="output directory")
    z.add_argument("--grid", type=int, default=140, help="figure sampling grid (default 140)")
    z.add_argument("--meshcat", action="store_true", help="also open the 3-D Meshcat view")
    z.set_defaults(func=_cmd_viz)

    s = sub.add_parser("show", help="minimal Meshcat view of a scene (design inspection)")
    s.add_argument("scene", help="path to the YAML scene")
    s.add_argument("--config", choices=["both", "start", "goal", "sweep"],
                   default="both",
                   help="draw: both (default), start, goal, or 'sweep' (a fan of "
                        "start->goal poses, colliding ones in red — shows why the "
                        "direct motion is blocked)")
    s.add_argument("--png", default=None,
                   help="save a 2-D top-down figure to this path (planar scenes) "
                        "instead of launching the Meshcat server")
    s.add_argument("--body-mode", dest="body_mode", choices=["segment", "hull"],
                   default=None,
                   help="modèle du corps dans l'interactif (défaut : déduit de la scène — "
                        "'hull' + GJK dès que le corps a plus de 2 sommets, A43)")
    s.add_argument("--interactive", default=None, metavar="OUT.html",
                   help="export a self-contained interactive HTML (spatial scenes, A24): "
                        "joint sliders, live collision, start/goal ghosts, escape-attempt "
                        "buttons — no server, no dependencies")
    s.set_defaults(func=_cmd_show)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, KeyError, NotImplementedError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
