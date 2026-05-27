"""AddFr config writer.

The published EA `_009` reads four constants from a plain ANSI text
file in the same `Files\\<dname>\\` folder as `pro100.csv`:

    # comment
    MAX_FR=1000
    BEST_MM=3
    BEST_FT=10
    MIN_DIFF=0.01

Two profiles are used by the GUI:

  * `STANDARD` -- BACK / FWD / REAL phases. Matches the historical
    `_tst_008` defaults so behaviour is unchanged for those phases.
  * `EXTENDED` -- MM-sweep phase. Wider AddFr filter that lets every
    `inp_mm` pass survive deduplication; needed for the "3rd pass
    after last fail" survivor algorithm.

If the file is absent the EA silently falls back to its compiled-in
defaults, so writing the config is best-effort but recommended.
"""

from __future__ import annotations

from dataclasses import dataclass


CONFIG_FILENAME = "pro100_addfr.cfg"


@dataclass(frozen=True, slots=True)
class AddFrProfile:
    """Four runtime knobs the EA reads from pro100_addfr.cfg."""

    name: str
    max_fr: int
    best_mm: int
    best_ft: int
    min_diff: float


STANDARD: AddFrProfile = AddFrProfile(
    name="standard",
    max_fr=1000,
    best_mm=3,
    best_ft=10,
    min_diff=0.01,
)
"""Default-equivalent profile used by BACK / FWD / REAL phases."""

EXTENDED: AddFrProfile = AddFrProfile(
    name="extended",
    max_fr=100000,
    best_mm=20,
    best_ft=20,
    min_diff=0.000001,
)
"""Sweep profile used by MM-sweep. Mirrors the legacy `_opt_008` build."""


def serialize_addfr_config(profile: AddFrProfile) -> bytes:
    """Render the config as ANSI bytes ready for write_bytes().

    Plain `key=value` lines, one per knob, prefixed by a header
    comment that names the profile. CRLF line endings so the file
    reads cleanly in Windows text editors -- the EA parser is
    line-based and tolerates either kind, but Notepad won't.
    """
    lines = [
        f"# Pro100GUI addfr config -- profile: {profile.name}",
        f"MAX_FR={profile.max_fr}",
        f"BEST_MM={profile.best_mm}",
        f"BEST_FT={profile.best_ft}",
        f"MIN_DIFF={_fmt_min_diff(profile.min_diff)}",
        "",
    ]
    return ("\r\n".join(lines)).encode("ascii")


def _fmt_min_diff(value: float) -> str:
    """Avoid scientific notation; the EA's StringToDouble accepts both
    but keeping the file human-readable is friendlier for debugging."""
    if value == 0:
        return "0"
    text = f"{value:.10f}".rstrip("0")
    if text.endswith("."):
        text += "0"
    return text
