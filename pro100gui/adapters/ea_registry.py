"""Registry of EA builds available to the orchestrator.

In v1 the EA is a single user-provided file (downloaded manually from
the canonical Telegram post). The registry exists so that:
  * higher layers refer to EA builds by symbolic key (e.g. 'tester'),
    not by file path -- letting future builds plug in without
    rewiring the orchestrator;
  * version verification (via EAVersionChecker) is centralized.

Future extension: when EA `_009` is published (with disk-readable
AddFr constants -- see project memory project-pro100gui-ea-v009),
mm-sweep will register the SAME 'tester' build but the orchestrator
will write a different AddFr config file alongside pro100.csv.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ea_version_checker import EAVersionChecker, VersionCheck

# Symbolic build keys -- exported so callers don't pass raw strings.
TESTER_BUILD = "tester"
"""Default key for the publicly-distributed _tst_ build. Used by all
Pro100 phases (BACK / FWD / REAL) and -- once EA _009 ships -- also
by MM-sweep with disk-based AddFr override."""

OPT_BUILD = "opt"
"""Reserved key for a separately-compiled _opt_ build with extended
AddFr filter constants. Only used if the user provides a custom
build for legacy MM-sweep on EA _008."""


@dataclass(frozen=True, slots=True)
class EABuild:
    """One compiled EA file with its derived identity."""

    path: Path
    """Absolute path to the .ex5 on local disk."""

    @property
    def ea_id(self) -> str:
        """Canonical identifier used for staging dir / .ini Expert path
        (the filename without the .ex5 extension)."""
        return self.path.stem

    @property
    def ex5_basename(self) -> str:
        """The .ex5 filename including extension."""
        return self.path.name


class EARegistry:
    """Registry of EA builds keyed by symbolic role."""

    def __init__(self, version_checker: EAVersionChecker | None = None) -> None:
        self._builds: dict[str, EABuild] = {}
        self._checker = version_checker

    def register(self, key: str, path: Path) -> EABuild:
        """Register an EA file under a symbolic key.

        Raises FileNotFoundError if path does not exist or is not a file.
        Replaces any prior registration under the same key.
        """
        if not path.is_file():
            raise FileNotFoundError(f"EA file not found: {path}")
        build = EABuild(path=path)
        self._builds[key] = build
        return build

    def unregister(self, key: str) -> None:
        """Remove a registration (best-effort, no error if absent)."""
        self._builds.pop(key, None)

    def has(self, key: str) -> bool:
        return key in self._builds

    def get(self, key: str) -> EABuild:
        """Return the EABuild for the given key.

        Raises KeyError if not registered.
        """
        if key not in self._builds:
            raise KeyError(f"EA build not registered: {key!r}")
        return self._builds[key]

    def keys(self) -> tuple[str, ...]:
        return tuple(self._builds)

    def verify(self, key: str) -> VersionCheck | None:
        """Compare the registered file against the canonical Telegram post.

        Returns None when no EAVersionChecker is configured. Use this
        return value as 'verification not available -- skip warning'.
        """
        if self._checker is None:
            return None
        build = self.get(key)
        return self._checker.check(build.path)
