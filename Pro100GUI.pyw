"""Pro100GUI entry point (windowless launcher).

Run with pythonw.exe to avoid a console window. On first launch
performs dependency bootstrap, then hands off to pro100gui.app.main.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import bootstrap

bootstrap.ensure()

from pro100gui.app.main import run

if __name__ == "__main__":
    sys.exit(run())
