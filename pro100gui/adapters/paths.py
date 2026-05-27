"""MT5 install layout and path resolution.

One immutable object that knows where the target MT5 terminal lives
and how to derive every per-run subdirectory and file path. Used by
FilesStaging and TerminalRunner so they don't hard-code paths.

The default factory points at the RoboForex MT5 install in portable
mode (`C:\\Program Files\\RoboForex MT5 Terminal\\`). For tests and
alternative deployments, construct directly with custom roots.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INSTALL_DIR = Path(r"C:\Program Files\RoboForex MT5 Terminal")
DEFAULT_PROJECT_DIR = Path(r"C:\Users\Администратор")

# Staging namespace inside MQL5/* -- isolates Pro100GUI artifacts
# from anything else the terminal may host. Mirrors TesterAgent's
# _TesterAgent convention so existing tooling does not collide.
STAGING_NAMESPACE = "_Pro100GUI"


@dataclass(frozen=True, slots=True)
class MT5Paths:
    """All paths Pro100GUI ever writes to or reads from in MT5.

    `install_dir` is the portable terminal's root (contains
    terminal64.exe and the MQL5\\ tree).
    `project_dir` is the user's home; used to locate the AppData
    Common\\Files folder.
    """

    install_dir: Path = DEFAULT_INSTALL_DIR
    project_dir: Path = DEFAULT_PROJECT_DIR

    # ---------- root resources ----------

    @property
    def terminal_exe(self) -> Path:
        return self.install_dir / "terminal64.exe"

    @property
    def mql5_dir(self) -> Path:
        return self.install_dir / "MQL5"

    @property
    def common_files_dir(self) -> Path:
        return (
            self.project_dir / "AppData" / "Roaming" / "MetaQuotes"
            / "Terminal" / "Common" / "Files"
        )

    @property
    def tester_logs_dir(self) -> Path:
        return self.install_dir / "Tester" / "Agent-127.0.0.1-3000" / "logs"

    # ---------- our staging roots ----------

    @property
    def experts_staging_root(self) -> Path:
        """MQL5\\Experts\\<NS>\\ -- staged .ex5 binaries land here."""
        return self.mql5_dir / "Experts" / STAGING_NAMESPACE

    @property
    def profile_root(self) -> Path:
        """MQL5\\Profiles\\Tester\\<NS>\\ -- .set and .ini live here."""
        return self.mql5_dir / "Profiles" / "Tester" / STAGING_NAMESPACE

    @property
    def files_dir(self) -> Path:
        """MQL5\\Files\\ -- pro100.csv input lives in subfolders here."""
        return self.mql5_dir / "Files"

    # ---------- per-run derivations ----------

    def ea_staging_dir(self, ea_id: str) -> Path:
        return self.experts_staging_root / ea_id

    def ea_staged_ex5(self, ea_id: str, ex5_basename: str) -> Path:
        return self.ea_staging_dir(ea_id) / ex5_basename

    def set_file(self, run_id: str) -> Path:
        return self.profile_root / f"{run_id}.set"

    def ini_file(self, run_id: str) -> Path:
        return self.profile_root / f"{run_id}.ini"

    def pro100_local(self, dname: str) -> Path:
        return self.files_dir / dname / "pro100.csv"

    def pro100_common(self, dname: str) -> Path:
        return self.common_files_dir / dname / "pro100.csv"

    def today_log(self) -> Path:
        import datetime as _dt
        today = _dt.datetime.now().strftime("%Y%m%d")
        return self.tester_logs_dir / f"{today}.log"

    # ---------- helpers ----------

    def expert_rel(self, ea_id: str, ex5_basename: str) -> str:
        """Path to the .ex5 as MT5 expects in .ini Expert= field
        (relative to MQL5\\Experts\\, backslash-separated, no leading sep)."""
        return f"{STAGING_NAMESPACE}\\{ea_id}\\{ex5_basename}"

    def set_rel(self, run_id: str) -> str:
        """.set path as MT5 expects in ExpertParameters= (relative to
        MQL5\\Profiles\\Tester\\)."""
        return f"{STAGING_NAMESPACE}\\{run_id}.set"

    def report_rel(self, run_id: str) -> str:
        """Report path under MQL5\\Files\\."""
        return f"{STAGING_NAMESPACE}\\{run_id}"


def default_paths() -> MT5Paths:
    """Factory: respect TESTER_AGENT_INSTALL_DIR env var if set."""
    install = Path(os.environ.get("TESTER_AGENT_INSTALL_DIR", str(DEFAULT_INSTALL_DIR)))
    return MT5Paths(install_dir=install)
