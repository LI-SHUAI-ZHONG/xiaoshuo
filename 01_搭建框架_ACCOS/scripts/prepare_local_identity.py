"""Compatibility CLI: --output is an .env file inside a NEW private directory.

The shared installer writes the bootstrap token to a private sibling file and
prints paths only. Existing installation directories are never overwritten.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Support isolated (-I) invocation as well as package imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.setup_identity import main as main

if __name__ == "__main__":
    raise SystemExit(main(legacy_output_file=True))
