"""Entry point do harness: `uv run python -m einstein_test.eval`."""

import sys

from einstein_test.eval.cli import main

sys.exit(main())