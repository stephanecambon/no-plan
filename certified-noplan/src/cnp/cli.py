"""cnp — command-line interface.

Three commands, three honest verdicts (CLAUDE.md rules 5/6, annotation A17):

* ``cnp certify <scene.yaml> [-o cert.json]`` — solve a scene end-to-end and emit an
  exact-rational certificate. Verdicts:
    - **PROOF**       — engine proved the disconnection AND the independent exact
                        verifier (:mod:`cnp.verify`) re-checked the certificate;
    - **ENGINE-PROOF** — the engine proved it, but exact verification is unavailable
                        for this scene (a non-planar robot before S9, or a leaf that
                        would not round to an exactly-feasible certificate). ALWAYS
                        printed with its warning: this is NOT a verified proof;
    - **UNDECIDED**   — no certificate at the given budget (NOT a proof of feasibility).
* ``cnp verify <cert.json> [scene.yaml]`` — run the untrusted exact verifier; if a
  scene file is given, also cross-check that the certificate states the same problem.
* ``cnp show <scene.yaml> [--config start|goal]`` — minimal Meshcat view of the scene
  (robot at start/goal, obstacles) for visual design inspection (SPEC §6, V3).
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
        return 0
    print("verdict: UNDECIDED (certificate not verified; NOT a proof of feasibility)")
    return 1


# --------------------------------------------------------------------------- #
# certify
# --------------------------------------------------------------------------- #

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
              "EXACT verifier does not yet support this robot kind — "
              f"{scene.robot.kind!r}, exact verification arrives in S9)")
        print("  WARNING: this is NOT an exact-arithmetic-verified proof (rule 5).")
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

    s = sub.add_parser("show", help="minimal Meshcat view of a scene (design inspection)")
    s.add_argument("scene", help="path to the YAML scene")
    s.add_argument("--config", choices=["both", "start", "goal"], default="both",
                   help="which configuration(s) to draw: both (default), start, or goal")
    s.add_argument("--png", default=None,
                   help="save a 2-D top-down figure to this path (planar scenes) "
                        "instead of launching the Meshcat server")
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
