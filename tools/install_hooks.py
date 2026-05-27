"""Install git hooks from tools/hooks/ into .git/hooks/.

Run once after cloning the repo:

    python tools/install_hooks.py

Forces LF line endings and (on POSIX) the executable bit, so the hook
runs reliably regardless of the user's core.autocrlf setting.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "hooks"
DST = ROOT / ".git" / "hooks"


def install() -> int:
    if not (ROOT / ".git").is_dir():
        print(f"ERROR: {ROOT} is not a git repository.", file=sys.stderr)
        return 1
    DST.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in SRC.iterdir():
        if not src.is_file():
            continue
        body = src.read_bytes().replace(b"\r\n", b"\n")
        dst = DST / src.name
        dst.write_bytes(body)
        if os.name != "nt":
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"installed: {dst.relative_to(ROOT)}")
        n += 1
    if n == 0:
        print("WARNING: no hook files found in tools/hooks/", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(install())
