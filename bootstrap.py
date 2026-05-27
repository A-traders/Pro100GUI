"""First-run dependency bootstrap.

Checks that all runtime dependencies declared in pyproject.toml are
importable. Missing ones are installed via pip in the current
interpreter. A marker file (.bootstrap_done) skips the check on
subsequent runs unless dependencies change.

This module must not import anything outside the stdlib so that it can
run on a fresh Python install.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

REQUIRED = {
    "PySide6": "PySide6>=6.6",
    "reportlab": "reportlab>=4.4",
    "pypdfium2": "pypdfium2>=4.30",
    "pypdf": "pypdf>=4.0",
    "PIL": "Pillow>=10.0",
    "requests": "requests>=2.31",
}

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / ".bootstrap_done"


def _signature() -> str:
    blob = "\n".join(f"{k}={v}" for k, v in sorted(REQUIRED.items()))
    return hashlib.sha256(blob.encode()).hexdigest()


def _missing() -> list[str]:
    out = []
    for mod, spec in REQUIRED.items():
        if importlib.util.find_spec(mod) is None:
            out.append(spec)
    return out


def ensure(progress=None) -> None:
    sig = _signature()
    if MARKER.exists() and MARKER.read_text().strip() == sig:
        return

    missing = _missing()
    if not missing:
        MARKER.write_text(sig)
        return

    if progress:
        progress(f"Installing {len(missing)} package(s): {', '.join(missing)}")

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *missing]
    subprocess.check_call(cmd)
    MARKER.write_text(sig)


if __name__ == "__main__":
    ensure(progress=print)
