"""cnp — command-line interface.

S4 ships the credibility command: ``cnp verify <cert.json>`` runs the INDEPENDENT
exact-arithmetic verifier (:mod:`cnp.verify`) and prints the honest verdict
(CLAUDE.md rules 5/6: a result is "certified" only if verify returns OK; otherwise
the verdict is UNDECIDED, never "feasible"). ``cnp certify``/``cnp show`` and the YAML
scene argument arrive in S6 (scene parser); for now the certificate is self-contained
(it embeds the exact-rational robot + obstacles the verifier recomputes against).
"""
from __future__ import annotations

import argparse
import sys

from . import verify as _verify


def _cmd_verify(args) -> int:
    ok, msg = _verify.verify_file(args.cert)
    print(("OK    — " if ok else "REJECT — ") + msg)
    if ok:
        print("verdict: PROOF (verified in exact arithmetic)")
        return 0
    print("verdict: UNDECIDED (certificate not verified; NOT a proof of feasibility)")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cnp",
                                description="certified-noplan: disconnection "
                                            "certificates for motion planning")
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("verify", help="independently verify a certificate (exact)")
    v.add_argument("cert", help="path to the JSON certificate")
    v.add_argument("scene", nargs="?", default=None,
                   help="optional scene file to cross-check (S6; cert is "
                        "self-contained in S4)")
    v.set_defaults(func=_cmd_verify)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
