"""Build a single-file Windows installer for Pro100GUI.

Steps:
  1. Download the Python embeddable zip from python.org.
  2. Unpack it into installer/work/python-embed/.
  3. Enable site-packages (uncomment `import site` in python3xx._pth).
  4. Bootstrap pip via get-pip.py.
  5. pip install all runtime deps from pyproject.toml [project.dependencies].
  6. Stage app source files into installer/work/app/.
  7. Run ISCC.exe on installer/Pro100GUI.iss.
  8. The .exe lands in installer/dist/.

Run from the repo root:
    python installer/build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PY_VERSION = "3.13.0"
PY_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PY_VERSION}/"
    f"python-{PY_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
ISCC = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_DIR = REPO_ROOT / "installer"
WORK_DIR = INSTALLER_DIR / "work"
DOWNLOADS_DIR = WORK_DIR / "_downloads"
EMBED_DIR = WORK_DIR / "python-embed"
APP_STAGE_DIR = WORK_DIR / "app"
DIST_DIR = INSTALLER_DIR / "dist"

RUNTIME_DEPS = [
    # Must match [project.dependencies] in pyproject.toml.
    "PySide6>=6.6",
    "reportlab>=4.4",
    "pypdfium2>=4.30",
    "pypdf>=4.0",
    "Pillow>=10.0",
    "requests>=2.31",
]


def step(msg: str) -> None:
    print(f"\n=== {msg}", flush=True)


def download(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file() and dst.stat().st_size > 0:
        print(f"  cached: {dst.name} ({dst.stat().st_size // 1024} KB)")
        return
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"  saved {dst.stat().st_size // 1024} KB")


def fetch_python_embed() -> None:
    step("Fetch Python embeddable")
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DOWNLOADS_DIR / f"python-{PY_VERSION}-embed-amd64.zip"
    download(PY_EMBED_URL, zip_path)
    if EMBED_DIR.is_dir():
        shutil.rmtree(EMBED_DIR)
    EMBED_DIR.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(EMBED_DIR)
    print(f"  extracted to {EMBED_DIR}")


def enable_site_packages() -> None:
    """Embed Python ships with `import site` disabled in *._pth.
    pip will fail without it. Uncomment that line."""
    step("Enable site-packages in embed")
    pth_files = list(EMBED_DIR.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("python._pth not found in embed")
    pth = pth_files[0]
    text = pth.read_text(encoding="utf-8")
    new = text.replace("#import site", "import site")
    if new == text and "import site" not in text:
        # Already raw -- inject anyway
        new = text + "\nimport site\n"
    pth.write_text(new, encoding="utf-8")
    print(f"  patched {pth.name}")


def bootstrap_pip() -> None:
    step("Bootstrap pip via get-pip.py")
    get_pip = DOWNLOADS_DIR / "get-pip.py"
    download(GET_PIP_URL, get_pip)
    python_exe = EMBED_DIR / "python.exe"
    subprocess.run(
        [str(python_exe), str(get_pip), "--no-warn-script-location"],
        check=True,
    )


def install_runtime_deps() -> None:
    step(f"pip install runtime deps ({len(RUNTIME_DEPS)} pkgs)")
    python_exe = EMBED_DIR / "python.exe"
    cmd = [
        str(python_exe), "-m", "pip", "install",
        "--no-warn-script-location",
        "--no-cache-dir",
        "--disable-pip-version-check",
        *RUNTIME_DEPS,
    ]
    subprocess.run(cmd, check=True)


def stage_app_files() -> None:
    """Copy the app source tree (no tests, no docs, no .git)."""
    step("Stage app source")
    if APP_STAGE_DIR.exists():
        shutil.rmtree(APP_STAGE_DIR)
    APP_STAGE_DIR.mkdir(parents=True)

    # Top-level files
    for name in ("Pro100GUI.pyw", "bootstrap.py", "README.md",
                 "ROADMAP.md", "LICENSE", "pyproject.toml"):
        src = REPO_ROOT / name
        if src.is_file():
            shutil.copy2(src, APP_STAGE_DIR / name)

    # Package
    pkg_src = REPO_ROOT / "pro100gui"
    shutil.copytree(
        pkg_src, APP_STAGE_DIR / "pro100gui",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    # docs/
    docs_src = REPO_ROOT / "docs"
    if docs_src.is_dir():
        shutil.copytree(
            docs_src, APP_STAGE_DIR / "docs",
            ignore=shutil.ignore_patterns("_preview", "*.py"),
        )

    print(f"  staged to {APP_STAGE_DIR}")


def read_app_version() -> str:
    """Best-effort: pull version from pyproject.toml."""
    pyproject = REPO_ROOT / "pyproject.toml"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "0.0.1"


def run_iscc() -> Path:
    step("Run Inno Setup Compiler")
    if not ISCC.is_file():
        raise RuntimeError(f"ISCC not found at {ISCC}")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    iss = INSTALLER_DIR / "Pro100GUI.iss"
    version = read_app_version()
    cmd = [
        str(ISCC),
        f"/DAppVersion={version}",
        f"/DAppSrcDir={APP_STAGE_DIR}",
        f"/DEmbedDir={EMBED_DIR}",
        f"/DOutputDir={DIST_DIR}",
        str(iss),
    ]
    subprocess.run(cmd, check=True)
    out = DIST_DIR / f"Pro100GUI-Setup-{version}.exe"
    if not out.is_file():
        # ISCC names by AppVersion + OutputBaseFilename macro; fall back
        # to anything in dist/.
        candidates = list(DIST_DIR.glob("Pro100GUI-Setup*.exe"))
        if not candidates:
            raise RuntimeError("ISCC ran but no .exe produced")
        out = max(candidates, key=lambda p: p.stat().st_mtime)
    return out


def main() -> int:
    if not sys.platform.startswith("win"):
        print("This build script only works on Windows.", file=sys.stderr)
        return 1
    fetch_python_embed()
    enable_site_packages()
    bootstrap_pip()
    install_runtime_deps()
    stage_app_files()
    out = run_iscc()
    print(f"\n=== DONE: {out}  ({out.stat().st_size // (1024*1024)} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
