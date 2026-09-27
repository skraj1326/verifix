"""Log Intelligence Engine - Parses and analyzes simulator logs."""

import re
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter


@dataclass
class LogEntry:
    timestamp: str = ""
    severity: str = "INFO"  # INFO, WARNING, ERROR, FATAL
    source: str = ""
    message: str = ""
    line_number: int = 0
    category: str = ""  # assertion, uvm, compile, runtime, etc.


@dataclass
class FailureCluster:
    pattern: str
    count: int
    first_occurrence: int
    affected_signals: list = field(default_factory=list)
    affected_modules: list = field(default_factory=list)
    root_cause_hint: str = ""


class LogAnalyzer:
    """Analyzes simulator logs to extract meaningful information.

    Determines:
    - First meaningful failure
    - Likely root cause
    - Affected module
    - Relevant signals
    - Suggested debugging path
    """

    # Common error patterns
    ERROR_PATTERNS = [
        (r"Error.*?(\w+\.\w+:\d+)", "compile", "Compile error"),
        (r"Fatal.*?(\w+\.\w+:\d+)", "fatal", "Fatal error"),
        (r"Assertion.*?failed.*?(\w+)", "assertion", "Assertion failure"),
        (r"\[FAIL\].*?(.*)", "test_fail", "Test failure"),
        (r"UVM_FATAL.*?(.*)", "uvm_fatal", "UVM Fatal"),
        (r"UVM_ERROR.*?(.*)", "uvm_error", "UVM Error"),
        (r"Timeout.*?(.*)", "timeout", "Simulation timeout"),
        (r"Unknown.*?signal.*?(\w+)", "unknown_signal", "Unknown signal"),
        (r"Multiple.*?drivers.*?(\w+)", "multi_driver", "Multiple drivers"),
        (r"X.*?propagat.*?(\w+)", "x_propagation", "X-propagation"),
        (r"Timing.*?violation.*?(.*)", "timing", "Timing violation"),
    ]

    WARNING_PATTERNS = [
        (r"Warning.*?(\w+\.\w+:\d+)", "compile_warning", "Compile warning"),
        (r"UVM_WARNING.*?(.*)", "uvm_warning", "UVM Warning"),
        (r"Tristate.*?(\w+)", "tristate", "Tristate signal"),
        (r"Latch.*?inferred.*?(\w+)", "latch", "Latch inferred"),
    ]

    def parse_log(self, content: str) -> dict:
        """Parse a simulator log and extract structured information."""
        lines = content.split("\n")
        entries = []
        errors = []
        warnings = []
        assertion_failures = []
        uvm_errors = []

        for i, line in enumerate(lines):
            # Parse severity
            severity = self._detect_severity(line)
            category = self._detect_category(line)
            source = self._extract_source(line)

            entry = LogEntry(
                severity=severity,
                source=source,
                message=line.strip(),
                line_number=i + 1,
                category=category,
            )
            entries.append(entry)

            if severity == "ERROR":
                errors.append(entry)
            elif severity == "WARNING":
                warnings.append(entry)
            elif severity == "FATAL":
                errors.append(entry)

            # Detect assertion failures
            if "assert" in line.lower() and ("fail" in line.lower() or "error" in line.lower()):
                assertion_failures.append(entry)

            # Detect UVM errors
            if "UVM_ERROR" in line or "UVM_FATAL" in line:
                uvm_errors.append(entry)

        # Cluster similar failures
        clusters = self._cluster_failures(errors + assertion_failures)

        # Find first meaningful failure
        first_failure = self._find_first_failure(entries)

        # Generate root cause analysis
        root_cause = self._analyze_root_cause(errors, assertion_failures, entries)

        return {
            "total_lines": len(lines),
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "assertion_failures": len(assertion_failures),
            "uvm_errors": len(uvm_errors),
            "errors": [{"line": e.line_number, "message": e.message,
                       "category": e.category} for e in errors[:20]],
            "warnings": [{"line": w.line_number, "message": w.message,
                         "category": w.category} for w in warnings[:20]],
            "first_failure": first_failure,
            "failure_clusters": clusters,
            "root_cause_analysis": root_cause,
            "severity_summary": self._severity_summary(entries),
        }

    def _detect_severity(self, line: str) -> str:
        """Detect log entry severity."""
        line_lower = line.lower()
        if any(w in line_lower for w in ["fatal", "crash", "abort"]):
            return "FATAL"
        if any(w in line_lower for w in ["error", "fail", "assert"]):
            if "warning" not in line_lower:
                return "ERROR"
        if any(w in line_lower for w in ["warning", "warn"]):
            return "WARNING"
        return "INFO"

    def _detect_category(self, line: str) -> str:
        """Detect log entry category."""
        line_lower = line.lower()
        if "compil" in line_lower or "syntax" in line_lower:
            return "compile"
        if "uvm_" in line_lower or "uvm " in line_lower:
            return "uvm"
        if "assert" in line_lower:
            return "assertion"
        if "time" in line_lower and ("out" in line_lower or "limit" in line_lower):
            return "timeout"
        if "runtime" in line_lower:
            return "runtime"
        return "general"

    def _extract_source(self, line: str) -> str:
        """Extract source file/line from log entry."""
        match = re.search(r"(\w+\.(?:sv|v|svh|vh)):(\d+)", line)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
        return ""

    def _cluster_failures(self, errors: list) -> list:
        """Cluster similar error messages."""
        if not errors:
            return []

        # Group by pattern
        pattern_groups = Counter()
        for error in errors:
            # Normalize the error message
            normalized = re.sub(r"\d+", "N", error.message)
            normalized = re.sub(r"\w+\.\w+:\d+", "FILE:LINE", normalized)
            pattern_groups[normalized] += 1

        clusters = []
        for pattern, count in pattern_groups.most_common(10):
            clusters.append(FailureCluster(
                pattern=pattern,
                count=count,
                first_occurrence=0,
                root_cause_hint=self._hint_root_cause(pattern),
            ))

        return [{"pattern": c.pattern, "count": c.count,
                 "root_cause_hint": c.root_cause_hint} for c in clusters]

    def _hint_root_cause(self, pattern: str) -> str:
        """Provide a root cause hint based on error pattern."""
        pattern_lower = pattern.lower()
        if "assert" in pattern_lower:
            return "Check assertion condition and RTL logic"
        if "x" in pattern_lower or "unknown" in pattern_lower:
            return "X-propagation: check for uninitialized registers or combinational loops"
        if "driver" in pattern_lower or "multipl" in pattern_lower:
            return "Multiple drivers: check for conflicting continuous assignments"
        if "timeout" in pattern_lower:
            return "Simulation hang: check for combinational loops or deadlock"
        if "uvm" in pattern_lower:
            return "UVM component issue: check phase connections and config_db"
        return "Review RTL and testbench for logical errors"

    def _find_first_failure(self, entries: list) -> dict:
        """Find the first meaningful failure entry."""
        for entry in entries:
            if entry.severity in ("ERROR", "FATAL"):
                return {
                    "line": entry.line_number,
                    "message": entry.message,
                    "category": entry.category,
                    "source": entry.source,
                }
        return {}

    def _analyze_root_cause(self, errors: list, assertions: list,
                           entries: list) -> dict:
        """Analyze potential root causes."""
        analysis = {
            "likely_cause": "",
            "affected_module": "",
            "relevant_signals": [],
            "evidence": [],
            "suggested_investigation": [],
            "confidence": "low",
        }

        if not errors and not assertions:
            analysis["likely_cause"] = "No errors detected in log"
            analysis["confidence"] = "high"
            return analysis

        # Extract module names from errors
        modules = set()
        signals = set()
        for error in errors + assertions:
            # Extract module references
            match = re.search(r"(\w+)_(?:a|p|c)_(\w+)", error.message)
            if match:
                modules.add(match.group(1))
                signals.add(match.group(2))

            # Extract signal names
            signal_match = re.findall(r"\b(\w+(?:_r|_n|_d|_q))\b", error.message)
            signals.update(signal_match)

        analysis["affected_module"] = list(modules)[0] if modules else ""
        analysis["relevant_signals"] = list(signals)[:10]

        # Determine likely cause based on error types
        if assertions:
            analysis["likely_cause"] = (
                f"Assertion failure detected. {len(assertions)} assertion(s) failed. "
                f"This indicates the RTL behavior does not match expected protocol or functionality."
            )
            analysis["evidence"] = [
                f"Assertion failure at line {a.line_number}: {a.message[:100]}"
                for a in assertions[:5]
            ]
            analysis["suggested_investigation"] = [
                "Check assertion condition against RTL implementation",
                "Verify signal values at time of assertion failure",
                "Review FSM state and transitions at failure point",
                "Check for X-propagation or unknown states",
            ]
            analysis["confidence"] = "medium"
        else:
            analysis["likely_cause"] = "Compilation or runtime error"
            analysis["evidence"] = [
                f"Error at line {e.line_number}: {e.message[:100]}"
                for e in errors[:5]
            ]
            analysis["confidence"] = "low"

        return analysis

    def _severity_summary(self, entries: list) -> dict:
        """Summarize log entries by severity."""
        counts = Counter(e.severity for e in entries)
        return dict(counts)

    def parse_compilation_errors(self, content: str) -> list[dict]:
        """Parse compilation errors specifically."""
        errors = []
        patterns = [
            (r"Error.*?(\w+\.\w+):(\d+):\s*(.*)", "sv"),
            (r"Syntax error.*?line\s+(\d+)", "syntax"),
            (r"Undefined.*?(\w+)", "undefined"),
        ]

        for line in content.split("\n"):
            for pattern, err_type in patterns:
                match = re.search(pattern, line)
                if match:
                    errors.append({
                        "type": err_type,
                        "message": line.strip(),
                        "details": match.groups(),
                    })
                    break

        return errors

    def parse_uvm_log(self, content: str) -> dict:
        """Parse UVM-specific log information."""
        uvm_info = {
            "uvm_errors": [],
            "uvm_warnings": [],
            "phase_violations": [],
            "config_issues": [],
            "component_not_found": [],
        }

        for i, line in enumerate(content.split("\n")):
            if "UVM_ERROR" in line:
                uvm_info["uvm_errors"].append({"line": i+1, "message": line.strip()})
            elif "UVM_WARNING" in line:
                uvm_info["uvm_warnings"].append({"line": i+1, "message": line.strip()})
            elif "phase" in line.lower() and "violation" in line.lower():
                uvm_info["phase_violations"].append({"line": i+1, "message": line.strip()})
            elif "config_db" in line.lower() or "get_config" in line.lower():
                uvm_info["config_issues"].append({"line": i+1, "message": line.strip()})
            elif "not found" in line.lower() and "component" in line.lower():
                uvm_info["component_not_found"].append({"line": i+1, "message": line.strip()})

        return uvm_info
