"""Root Cause Analysis Engine - Automated failure diagnosis."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FailureEvidence:
    fact: str
    source: str = ""
    confidence: str = "observed"  # observed, inferred, hypothesized


@dataclass
class RootCauseHypothesis:
    hypothesis: str
    confidence: str = "low"  # low, medium, high
    evidence: list = field(default_factory=list)
    suggested_investigation: list = field(default_factory=list)
    potential_fix: str = ""


class RootCauseEngine:
    """Automated root cause analysis for simulation failures.

    For every failure generates:
    - Failure summary
    - First failing assertion/error
    - Relevant RTL
    - Relevant signals
    - Likely root cause
    - Evidence
    - Confidence
    - Suggested investigation
    - Potential fix

    Separates FACTS from HYPOTHESES. Never fabricates observations.
    """

    def analyze(self, failure_info: dict, rtl_content: str = "",
                log_analysis: dict = None) -> dict:
        """Perform root cause analysis on a failure."""
        facts = self._extract_facts(failure_info, log_analysis)
        signals = self._identify_signals(failure_info, rtl_content)
        rtl_context = self._find_rtl_context(failure_info, rtl_content)
        hypotheses = self._generate_hypotheses(facts, signals, rtl_context)
        investigation = self._suggest_investigation(facts, hypotheses)

        return {
            "failure_summary": self._summarize_failure(failure_info),
            "facts": [vars(f) for f in facts],
            "relevant_signals": signals,
            "rtl_context": rtl_context,
            "hypotheses": [vars(h) for h in hypotheses],
            "suggested_investigation": investigation,
            "confidence": self._overall_confidence(hypotheses),
            "separation_of_concerns": {
                "facts_count": len(facts),
                "hypotheses_count": len(hypotheses),
                "note": "Facts are directly observed. Hypotheses require validation.",
            },
        }

    def _extract_facts(self, failure_info: dict,
                       log_analysis: dict = None) -> list[FailureEvidence]:
        """Extract directly observable facts from failure data."""
        facts = []

        # Fact: Assertion failed
        if failure_info.get("assertion_name"):
            facts.append(FailureEvidence(
                fact=f"Assertion '{failure_info['assertion_name']}' failed",
                source="simulation log",
                confidence="observed",
            ))

        # Fact: Error message
        if failure_info.get("error_message"):
            facts.append(FailureEvidence(
                fact=f"Error: {failure_info['error_message'][:200]}",
                source="simulation log",
                confidence="observed",
            ))

        # Fact: Failure time
        if failure_info.get("failure_time"):
            facts.append(FailureEvidence(
                fact=f"Failure occurred at time {failure_info['failure_time']}",
                source="simulation log",
                confidence="observed",
            ))

        # Fact: Exit code
        if failure_info.get("exit_code") is not None:
            facts.append(FailureEvidence(
                fact=f"Process exited with code {failure_info['exit_code']}",
                source="simulation",
                confidence="observed",
            ))

        # Fact: Signal values at failure
        if failure_info.get("signal_values"):
            for sig, val in failure_info["signal_values"].items():
                facts.append(FailureEvidence(
                    fact=f"Signal '{sig}' = {val}",
                    source="waveform/log",
                    confidence="observed",
                ))

        # Facts from log analysis
        if log_analysis:
            if log_analysis.get("first_failure"):
                ff = log_analysis["first_failure"]
                facts.append(FailureEvidence(
                    fact=f"First failure: {ff.get('message', 'unknown')[:200]}",
                    source="log analysis",
                    confidence="observed",
                ))

            if log_analysis.get("failure_clusters"):
                for cluster in log_analysis["failure_clusters"][:3]:
                    facts.append(FailureEvidence(
                        fact=f"Failure pattern '{cluster['pattern'][:100]}' occurred {cluster['count']} times",
                        source="log clustering",
                        confidence="observed",
                    ))

        return facts

    def _identify_signals(self, failure_info: dict,
                          rtl_content: str) -> list[dict]:
        """Identify signals relevant to the failure."""
        signals = []

        # From assertion name (module_signal_pattern)
        assertion_name = failure_info.get("assertion_name", "")
        if assertion_name:
            # Extract module and signal names
            parts = assertion_name.split("_")
            if len(parts) >= 2:
                signals.append({
                    "name": parts[-1] if len(parts) > 1 else assertion_name,
                    "relevance": "mentioned_in_assertion",
                    "source": "assertion",
                })

        # From error message
        error_msg = failure_info.get("error_message", "")
        if error_msg:
            # Find signal-like names
            signal_matches = re.findall(r'\b(\w+(?:_\w+){1,4})\b', error_msg)
            for sig in signal_matches[:5]:
                if len(sig) > 2 and not sig.startswith(("the", "this", "that", "with")):
                    signals.append({
                        "name": sig,
                        "relevance": "mentioned_in_error",
                        "source": "error_message",
                    })

        # From RTL content
        if rtl_content:
            # Find signals related to failure
            relevant_patterns = [
                r'(\w+_r\b)',  # registered signals
                r'(\w+_n\b)',  # next state
                r'(\w+_d\b)',  # delayed
                r'(\w+_q\b)',  # output register
            ]
            for pattern in relevant_patterns:
                matches = re.findall(pattern, rtl_content)
                for m in matches[:3]:
                    signals.append({
                        "name": m,
                        "relevance": "rtl_structure",
                        "source": "rtl_analysis",
                    })

        # Deduplicate
        seen = set()
        unique_signals = []
        for sig in signals:
            if sig["name"] not in seen:
                seen.add(sig["name"])
                unique_signals.append(sig)

        return unique_signals

    def _find_rtl_context(self, failure_info: dict,
                          rtl_content: str) -> dict:
        """Find RTL code context around the failure."""
        context = {
            "module_name": "",
            "relevant_lines": [],
            "always_blocks": [],
            "assign_statements": [],
        }

        if not rtl_content:
            return context

        # Find module containing the failing assertion
        assertion_name = failure_info.get("assertion_name", "")
        module_match = re.search(
            rf'module\s+(\w+).*?{re.escape(assertion_name)}',
            rtl_content, re.DOTALL
        )
        if module_match:
            context["module_name"] = module_match.group(1)

        # Find always blocks near the failure
        always_pattern = re.compile(
            r'always\s*@\s*\([^)]*\)\s*(?:begin.*?end)',
            re.DOTALL
        )
        for match in always_pattern.finditer(rtl_content):
            context["always_blocks"].append({
                "line": rtl_content[:match.start()].count("\n") + 1,
                "code": match.group()[:200],
            })

        return context

    def _generate_hypotheses(self, facts: list, signals: list,
                             rtl_context: dict) -> list[RootCauseHypothesis]:
        """Generate hypotheses based on facts and evidence."""
        hypotheses = []

        fact_texts = [f.fact.lower() for f in facts]

        # Hypothesis: FSM stuck in wrong state
        if any("state" in f or "fsm" in f for f in fact_texts):
            hypotheses.append(RootCauseHypothesis(
                hypothesis="FSM may be stuck in an incorrect state or making an illegal transition",
                confidence="medium",
                evidence=[f.fact for f in facts if "state" in f.fact.lower()][:3],
                suggested_investigation=[
                    "Check FSM state register value at time of failure",
                    "Verify all state transition conditions in RTL",
                    "Check for one-hot encoding violations",
                ],
                potential_fix="Review FSM transition logic and add default case handling",
            ))

        # Hypothesis: Reset not properly handled
        if any("reset" in f or "rst" in f for f in fact_texts):
            hypotheses.append(RootCauseHypothesis(
                hypothesis="Reset may not be properly asserting or de-asserting",
                confidence="medium",
                evidence=[f.fact for f in facts if "reset" in f.fact.lower() or "rst" in f.fact.lower()][:3],
                suggested_investigation=[
                    "Verify reset timing and polarity",
                    "Check async reset de-assertion timing relative to clock edge",
                    "Verify all registers have proper reset values",
                ],
                potential_fix="Ensure reset meets timing requirements and covers all registers",
            ))

        # Hypothesis: Handshake protocol violation
        if any("valid" in f or "ready" in f or "handshake" in f for f in fact_texts):
            hypotheses.append(RootCauseHypothesis(
                hypothesis="Valid/ready handshake protocol violation detected",
                confidence="medium",
                evidence=[f.fact for f in facts if any(kw in f.fact.lower() for kw in ["valid", "ready"])][:3],
                suggested_investigation=[
                    "Check valid/ready timing relationship",
                    "Verify data stability while valid is high",
                    "Check for backpressure handling",
                ],
                potential_fix="Review handshake protocol compliance in RTL",
            ))

        # Hypothesis: X-propagation
        if any("x" in f or "unknown" in f or "z" in f for f in fact_texts):
            hypotheses.append(RootCauseHypothesis(
                hypothesis="X-propagation or unknown state detected",
                confidence="low",
                evidence=[f.fact for f in facts if "x" in f.fact.lower() or "unknown" in f.fact.lower()][:3],
                suggested_investigation=[
                    "Find source of X values in waveform",
                    "Check for uninitialized registers",
                    "Look for combinational loops causing X",
                ],
                potential_fix="Add proper initialization to all registers",
            ))

        # Hypothesis: Combinational loop
        if any("loop" in f or "hang" in f or "timeout" in f for f in fact_texts):
            hypotheses.append(RootCauseHypothesis(
                hypothesis="Possible combinational loop or deadlock",
                confidence="low",
                evidence=[f.fact for f in facts if any(kw in f.fact.lower() for kw in ["loop", "hang", "timeout"])][:3],
                suggested_investigation=[
                    "Check for combinational feedback loops",
                    "Look for circular dependencies in always blocks",
                    "Verify no deadlock in handshake protocols",
                ],
                potential_fix="Break combinational loops by adding register stages",
            ))

        # Generic hypothesis if nothing specific found
        if not hypotheses:
            hypotheses.append(RootCauseHypothesis(
                hypothesis="RTL behavior does not match expected protocol or functionality",
                confidence="low",
                evidence=[f.fact for f in facts[:3]],
                suggested_investigation=[
                    "Review assertion condition against RTL implementation",
                    "Check signal values at time of failure in waveform",
                    "Verify testbench stimulus correctness",
                ],
                potential_fix="Debug with waveform viewer to identify root cause",
            ))

        return hypotheses

    def _suggest_investigation(self, facts: list,
                               hypotheses: list) -> list[str]:
        """Generate investigation steps."""
        steps = []

        steps.append("1. Review the first failing assertion or error message")
        steps.append("2. Examine signal values at the time of failure")

        if any("fsm" in h.hypothesis.lower() for h in hypotheses):
            steps.append("3. Trace FSM state transitions leading to failure")

        if any("reset" in h.hypothesis.lower() for h in hypotheses):
            steps.append("3. Check reset timing and de-assertion relative to clock")

        if any("handshake" in h.hypothesis.lower() for h in hypotheses):
            steps.append("3. Trace valid/ready timing diagram around failure point")

        steps.append("4. Check RTL code for the identified issue")
        steps.append("5. Apply fix and re-run simulation")

        return steps

    def _summarize_failure(self, failure_info: dict) -> str:
        """Create a concise failure summary."""
        parts = []
        if failure_info.get("assertion_name"):
            parts.append(f"Assertion '{failure_info['assertion_name']}' failed")
        if failure_info.get("error_message"):
            parts.append(f"Error: {failure_info['error_message'][:100]}")
        if failure_info.get("module_name"):
            parts.append(f"in module '{failure_info['module_name']}'")

        return ". ".join(parts) if parts else "Unknown failure"

    def _overall_confidence(self, hypotheses: list) -> str:
        """Determine overall confidence level."""
        if not hypotheses:
            return "low"
        confidences = [h.confidence for h in hypotheses]
        if "high" in confidences:
            return "medium-high"
        if confidences.count("medium") >= 2:
            return "medium"
        return "low"
