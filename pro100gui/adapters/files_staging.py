"""Filesystem staging for one tester run.

Responsibilities:
  * Copy a compiled .ex5 into MQL5\\Experts\\_Pro100GUI\\<ea_id>\\.
  * Write the .set and .ini files into the profile staging dir.
  * Write the pro100.csv input file into MQL5\\Files\\<dname>\\ and
    erase any stale Common copy (the EA mirrors output there).
  * Collect the pro100.csv produced by the EA on test completion.
  * Tear down staging artifacts after the run.

All operations are pure filesystem ops -- no subprocess, no MT5
launch (that's TerminalRunner's job).
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .ini_file import IniConfig, write_ini_file
from .paths import MT5Paths
from .set_file import SetParam, write_set_file


@dataclass(frozen=True, slots=True)
class StagedRun:
    """Paths created during stage(); used by TerminalRunner and cleanup()."""

    ea_id: str
    run_id: str
    dname: str | None  # None when pro100 input isn't used (regular optimize)
    ex5_staged: Path
    set_path: Path
    ini_path: Path


class FilesStaging:
    """Filesystem mediator for one tester run."""

    def __init__(self, paths: MT5Paths) -> None:
        self.paths = paths

    # ---------- EA binary staging ----------

    def stage_ea(self, ea_id: str, ex5_source: Path) -> Path:
        """Copy `ex5_source` into MQL5\\Experts\\_Pro100GUI\\<ea_id>\\.

        Returns the destination path. Idempotent: re-copies on each call
        (overwrites the existing file via shutil.copy2).
        """
        if not ex5_source.is_file():
            raise FileNotFoundError(f"ex5 source not found: {ex5_source}")
        staging_dir = self.paths.ea_staging_dir(ea_id)
        staging_dir.mkdir(parents=True, exist_ok=True)
        dst = staging_dir / ex5_source.name
        shutil.copy2(ex5_source, dst)
        return dst

    def unstage_ea(self, ea_id: str) -> None:
        """Remove the EA staging directory (best-effort)."""
        d = self.paths.ea_staging_dir(ea_id)
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    # ---------- profile staging (.set / .ini) ----------

    def write_set(self, run_id: str, params: Sequence[SetParam]) -> Path:
        """Write the .set file for this run into the profile staging dir."""
        p = self.paths.set_file(run_id)
        write_set_file(p, params)
        return p

    def write_ini(self, run_id: str, cfg: IniConfig) -> Path:
        """Write the .ini config for this run into the profile staging dir."""
        p = self.paths.ini_file(run_id)
        write_ini_file(p, cfg)
        return p

    def cleanup_profile(self, run_id: str) -> None:
        """Remove .ini and .set files for given run_id (best-effort)."""
        for p in (self.paths.ini_file(run_id), self.paths.set_file(run_id)):
            try:
                if p.is_file():
                    p.unlink()
            except OSError:
                pass

    # ---------- pro100.csv input/output ----------

    def write_pro100_input(self, dname: str, raw_bytes: bytes) -> Path:
        """Place a pre-encoded pro100.csv at MQL5\\Files\\<dname>\\pro100.csv.

        Caller provides the fully-encoded bytes (UTF-16 LE BOM + ...).
        Use pro100gui.core.pro100_csv.write_pro100_csv to produce them,
        or pass through an existing file's contents verbatim.

        Also erases any stale Common copy so the EA's _form_file_fwd
        path produces a clean rewrite.
        """
        dst = self.paths.pro100_local(dname)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw_bytes)
        common = self.paths.pro100_common(dname)
        if common.is_file():
            try:
                common.unlink()
            except OSError:
                pass
        return dst

    def cleanup_pro100(self, dname: str) -> list[Path]:
        """Remove both local and Common pro100.csv copies for a dname.

        Returns the list of paths that were actually removed.
        """
        removed: list[Path] = []
        for p in (self.paths.pro100_local(dname), self.paths.pro100_common(dname)):
            if p.is_file():
                try:
                    p.unlink()
                    removed.append(p)
                except OSError:
                    pass
        return removed

    def collect_pro100_output(self, dname: str, dest: Path) -> Path | None:
        """Copy pro100.csv from MQL5\\Files\\<dname>\\ to `dest`.

        Returns `dest` on success, None if the source file is missing
        (tester produced no useful frames, e.g. all sets failed).
        """
        src = self.paths.pro100_local(dname)
        if not src.is_file():
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest
