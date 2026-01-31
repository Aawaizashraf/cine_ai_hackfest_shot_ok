"""
Utilities for clip indexing and search.
"""
from typing import Union


def timestamp_to_seconds(ts: Union[str, float, None]) -> float:
    """
    Convert timestamp to seconds.
    - String format: "00:04:25,260" or "00:04:25.260" -> 265.26
    - Float/int: returned as float.
    - None: returns 0.0.
    """
    if ts is None:
        return 0.0
    if isinstance(ts, (int, float)):
        return float(ts)
    ts_clean = ts.strip().replace(",", ".")
    parts = ts_clean.split(":")
    if len(parts) != 3:
        return 0.0
    try:
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        return 0.0


def seconds_to_display(sec: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS for display."""
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    if h > 0:
        return f"{h:01d}:{m:02d}:{s:02d}"
    return f"{m:01d}:{s:02d}"
