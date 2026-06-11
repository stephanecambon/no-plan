"""``python -m cnp`` entry point (delegates to :func:`cnp.cli.main`)."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
