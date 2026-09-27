"""Utility helpers."""

import json
import re
from typing import Optional


def parse_declared_width(width_str: str) -> int:
    """Parse an RTL signal width declaration into bits.

    "[31:0]" -> 32
    "[7:0]" -> 8
    "" -> 1
    """
    if not width_str:
        return 1
    match = re.match(r"\[(\d+):(\d+)\]", width_str)
    if match:
        msb, lsb = int(match.group(1)), int(match.group(2))
        return abs(msb - lsb) + 1
    return 1


def safe_json_dumps(obj) -> str:
    """JSON serialization that handles non-serializable types."""
    def _default(o):
        try:
            if hasattr(o, "__dict__"):
                return o.__dict__
            return str(o)
        except Exception:
            return str(o)

    return json.dumps(obj, default=_default, indent=2)


def current_iso_timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def chunk_text(text: str, chunk_size: int = 2000) -> list[str]:
    """Split text into manageable chunks for LLM processing."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


def extract_signal_names(code: str) -> list[str]:
    """Extract unique signal-like identifiers from RTL code."""
    patterns = [
        r"\b[a-zA-Z_][a-zA-Z0-9_]*_(?:r|n|d|q|reg|wire|clk|rst)\b",
        r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:addr|data|valid|ready|en|full|empty)\b",
    ]
    signals = set()
    for pattern in patterns:
        signals.update(re.findall(pattern, code))
    return sorted(signals)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"