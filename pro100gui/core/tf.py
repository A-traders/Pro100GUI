"""MT5 timeframe table.

Maps between three representations of a timeframe:
  - canonical string ('M1', 'H4', ...)
  - duration in minutes
  - MT5 PERIOD_* enum value (used in .set files)

The full table comes from opt_pro100_002 and covers everything the
MT5 Strategy Tester supports.
"""

from __future__ import annotations

# (str, minutes, MT5 ENUM_TIMEFRAMES value)
_TF_TABLE: tuple[tuple[str, int, int], ...] = (
    ("M1", 1, 1),
    ("M2", 2, 2),
    ("M3", 3, 3),
    ("M4", 4, 4),
    ("M5", 5, 5),
    ("M6", 6, 6),
    ("M10", 10, 10),
    ("M12", 12, 12),
    ("M15", 15, 15),
    ("M20", 20, 20),
    ("M30", 30, 30),
    ("H1", 60, 16385),
    ("H2", 120, 16386),
    ("H3", 180, 16387),
    ("H4", 240, 16388),
    ("H6", 360, 16390),
    ("H8", 480, 16392),
    ("H12", 720, 16396),
    ("D1", 1440, 16408),
    ("W1", 10080, 32769),
    ("MN1", 43200, 49153),
)

_BY_STR = {row[0]: row for row in _TF_TABLE}
_BY_MIN = {row[1]: row for row in _TF_TABLE}
_BY_ENUM = {row[2]: row for row in _TF_TABLE}


def tf_enum(tf: str | int) -> int:
    """Resolve TF identifier -> MT5 PERIOD_* enum value.

    Accepts canonical string ('H1'), duration in minutes (60), or the
    enum value itself (16385). Rejects unknown values.
    """
    if isinstance(tf, str):
        s = tf.strip().upper()
        row = _BY_STR.get(s)
        if row:
            return row[2]
        if s.lstrip("-").isdigit():
            return tf_enum(int(s))
        raise ValueError(f"unknown TF: {tf!r}")
    if isinstance(tf, bool):
        raise TypeError("TF must not be bool")
    if isinstance(tf, int):
        if tf in _BY_ENUM:
            return tf
        if tf in _BY_MIN:
            return _BY_MIN[tf][2]
        raise ValueError(f"unknown TF numeric: {tf}")
    raise TypeError(f"TF must be str or int, got {type(tf).__name__}")


def tf_str(tf: str | int) -> str:
    """Resolve TF identifier -> canonical string ('H1', 'M5', ...)."""
    enum = tf_enum(tf)
    return _BY_ENUM[enum][0]


def tf_minutes(tf: str | int) -> int:
    """Resolve TF identifier -> duration in minutes."""
    enum = tf_enum(tf)
    return _BY_ENUM[enum][1]
