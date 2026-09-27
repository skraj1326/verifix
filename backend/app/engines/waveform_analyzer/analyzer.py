"""Waveform Intelligence Engine - VCD/FST waveform analysis."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SignalTransition:
    time: float
    value: str
    signal_name: str = ""


@dataclass
class WaveformAnalysis:
    signal_name: str
    transitions: list = field(default_factory=list)
    min_value: str = ""
    max_value: str = ""
    toggle_count: int = 0
    x_count: int = 0
    z_count: int = 0


class WaveformAnalyzer:
    """Analyzes VCD/FST waveform files for debugging.

    Initially supports basic VCD parsing.
    Later: FST, FSDB (with licensing).
    """

    def parse_vcd(self, content: str) -> dict:
        """Parse a VCD (Value Change Dump) file."""
        signals = {}
        timescale = "1ns"
        current_time = 0.0
        signal_map = {}

        lines = content.split("\n")
        for line in lines:
            line = line.strip()

            # Timescale
            if line.startswith("$timescale"):
                match = re.search(r"\$(\w+)\s+(\d+)", line)
                if match:
                    timescale = f"{match.group(2)}{match.group(1)}"

            # Signal definitions
            elif line.startswith("$var"):
                match = re.search(r"\$var\s+\w+\s+\d+\s+(\S+)\s+(\S+)", line)
                if match:
                    sig_id = match.group(1)
                    sig_name = match.group(2)
                    signal_map[sig_id] = sig_name
                    signals[sig_name] = WaveformAnalysis(signal_name=sig_name)

            # Time changes
            elif line.startswith("#"):
                try:
                    current_time = float(line[1:])
                except ValueError:
                    pass

            # Value changes (single bit)
            elif len(line) >= 2 and line[0] in "01xzXZ" and line[1] in signal_map:
                sig_name = signal_map[line[1]]
                if sig_name in signals:
                    signals[sig_name].transitions.append(
                        SignalTransition(time=current_time, value=line[0])
                    )

            # Value changes (multi bit)
            elif line.startswith("b"):
                match = re.match(r"b([01xzXZ]+)\s+(\S+)", line)
                if match:
                    value = match.group(1)
                    sig_id = match.group(2)
                    if sig_id in signal_map:
                        sig_name = signal_map[sig_id]
                        if sig_name in signals:
                            signals[sig_name].transitions.append(
                                SignalTransition(time=current_time, value=value)
                            )

        # Compute statistics
        for sig_name, analysis in signals.items():
            self._compute_statistics(analysis)

        return {
            "timescale": timescale,
            "time_range": {"min": 0, "max": current_time if 'current_time' in locals() else 0},
            "transitions": sum(len(a.transitions) for a in signals.values()),
            "total_signals": len(signals),
            "signals": {name: {
                "transitions": len(a.transitions),
                "toggle_count": a.toggle_count,
                "x_count": a.x_count,
                "z_count": a.z_count,
                "min_value": a.min_value,
                "max_value": a.max_value,
            } for name, a in signals.items()},
        }

    def analyze_signal_around_failure(self, signals: dict,
                                       failure_time: float,
                                       window: float = 100.0) -> dict:
        """Analyze signal values around a failure time point."""
        context = {}

        for sig_name, sig_data in signals.items():
            if isinstance(sig_data, WaveformAnalysis):
                relevant = [
                    t for t in sig_data.transitions
                    if failure_time - window <= t.time <= failure_time + window
                ]
                if relevant:
                    context[sig_name] = {
                        "value_at_failure": next(
                            (t.value for t in reversed(sig_data.transitions)
                             if t.time <= failure_time),
                            "unknown"
                        ),
                        "transitions_near_failure": [
                            {"time": t.time, "value": t.value}
                            for t in relevant
                        ],
                    }

        return context

    def find_signal_drivers(self, signal_name: str, rtl_content: str) -> list:
        """Find what drives a signal in the RTL."""
        drivers = []

        # Continuous assignment
        pattern = rf'assign\s+{re.escape(signal_name)}\s*=\s*(.+?);'
        for match in re.finditer(pattern, rtl_content):
            drivers.append({
                "type": "assign",
                "driver": match.group(1).strip(),
                "line": rtl_content[:match.start()].count("\n") + 1,
            })

        # Always block assignment
        pattern = rf'{re.escape(signal_name)}\s*<=?\s*(.+?);'
        for match in re.finditer(pattern, rtl_content):
            drivers.append({
                "type": "always",
                "driver": match.group(1).strip(),
                "line": rtl_content[:match.start()].count("\n") + 1,
            })

        return drivers

    def compare_waveforms(self, expected: dict, actual: dict,
                          tolerance: float = 0.0) -> list[dict]:
        """Compare expected vs actual waveform data."""
        differences = []

        all_signals = set(list(expected.keys()) + list(actual.keys()))

        for sig in all_signals:
            exp = expected.get(sig, {})
            act = actual.get(sig, {})

            exp_val = exp.get("value_at_failure", "")
            act_val = act.get("value_at_failure", "")

            if exp_val != act_val:
                differences.append({
                    "signal": sig,
                    "expected": exp_val,
                    "actual": act_val,
                    "type": "value_mismatch",
                })

        return differences

    def _compute_statistics(self, analysis: WaveformAnalysis) -> None:
        """Compute statistics for a signal analysis."""
        if not analysis.transitions:
            return

        values = [t.value for t in analysis.transitions]
        analysis.toggle_count = sum(
            1 for i in range(1, len(values)) if values[i] != values[i-1]
        )
        analysis.x_count = sum(1 for v in values if "x" in v.lower())
        analysis.z_count = sum(1 for v in values if "z" in v.lower())

        # Find min/max (treating as binary)
        numeric_values = []
        for v in values:
            try:
                numeric_values.append(int(v, 2))
            except (ValueError, TypeError):
                pass

        if numeric_values:
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            analysis.min_value = bin(min_val)
            analysis.max_value = bin(max_val)
