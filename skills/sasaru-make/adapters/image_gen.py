#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""sasaru-make adapter for image-gen. quote never bills; run needs --yes and --cap-usd."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _lib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main("image-gen"))
