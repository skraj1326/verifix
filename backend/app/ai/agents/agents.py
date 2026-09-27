"""AI Agents - Specialized agents for verification tasks."""

import logging
from typing import Optional
from app.ai.llm_client import get_llm_client, LLMResponse

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for AI agents."""

    def __init__(self, name: str):
        self.name = name
        self.llm = get_llm_client()

    async def run(self, **kwargs) -> dict:
        raise NotImplementedError

    def _format_response(self, response: LLMResponse) -> dict:
        return {
            "content": response.content,
            "model": response.model,
            "tokens_used": response.tokens_used,
            "is_ai_generated": self.llm.is_available,
            "agent": self.name,
        }


class RTLAnalyzerAgent(BaseAgent):
    """Analyzes RTL design intent and generates insights."""

    def __init__(self):
        super().__init__("rtl_analyzer")

    async def analyze_design_intent(self, rtl_content: str,
                                     parsed_modules: list) -> dict:
        """Analyze design intent using AI."""
        if not self.llm.is_available:
            return {
                "analysis": "LLM not available. Using structural analysis only.",
                "is_ai_generated": False,
            }

        modules_summary = "\n".join(
            f"- {m.name}: {len(m.ports)} ports, {len(m.signals)} signals, "
            f"{len(m.fsm_info)} FSMs"
            for m in parsed_modules
        )

        prompt = (
            f"Analyze this RTL design and describe its purpose, key features, "
            f"and verification challenges:\n\n"
            f"Modules:\n{modules_summary}\n\n"
            f"RTL Code (first 3000 chars):\n```\n{rtl_content[:3000]}\n```\n\n"
            f"Provide:\n"
            f"1. Design purpose and functionality\n"
            f"2. Key verification challenges\n"
            f"3. Recommended verification approach"
        )

        response = await self.llm.complete(prompt)
        return self._format_response(response)


class TestGenAgent(BaseAgent):
    """AI agent for intelligent test generation."""

    def __init__(self):
        super().__init__("test_generator")

    async def improve_test(self, test_code: str, failure_info: str,
                            rtl_context: str) -> dict:
        """Improve a failing test based on simulation feedback."""
        if not self.llm.is_available:
            return {
                "improvement": "LLM not available. Manual review required.",
                "is_ai_generated": False,
            }

        prompt = (
            f"This test failed during simulation:\n\n"
            f"Test Code:\n```\n{test_code}\n```\n\n"
            f"Failure Information:\n{failure_info}\n\n"
            f"RTL Context:\n```\n{rtl_context[:2000]}\n```\n\n"
            f"Improve the test to fix the failure while maintaining its "
            f"verification objective. Generate the corrected test code."
        )

        response = await self.llm.generate_systemverilog(prompt, rtl_context)
        return self._format_response(response)


class CoverageAgent(BaseAgent):
    """AI agent for coverage gap analysis."""

    def __init__(self):
        super().__init__("coverage_analyzer")

    async def analyze_gap(self, gap_info: dict, rtl_content: str) -> dict:
        """Analyze a coverage gap and suggest targeted tests."""
        if not self.llm.is_available:
            return {
                "analysis": "LLM not available. Using deterministic analysis.",
                "is_ai_generated": False,
            }

        prompt = (
            f"Analyze this coverage gap and generate a targeted test:\n\n"
            f"Gap Type: {gap_info.get('gap_type', 'unknown')}\n"
            f"Description: {gap_info.get('description', '')}\n"
            f"Coverage Type: {gap_info.get('coverage_type', '')}\n"
            f"RTL Location: {gap_info.get('rtl_location', {})}\n\n"
            f"RTL Code (relevant section):\n```\n{rtl_content[:2000]}\n```\n\n"
            f"Generate a SystemVerilog test that specifically targets this gap. "
            f"Explain the verification objective."
        )

        response = await self.llm.generate_systemverilog(prompt, rtl_content)
        return self._format_response(response)

    async def assess_unreachability(self, gap_info: dict,
                                     rtl_content: str) -> dict:
        """Assess whether a coverage gap is potentially unreachable."""
        if not self.llm.is_available:
            return {
                "assessment": "LLM not available. Cannot assess reachability.",
                "is_ai_generated": False,
            }

        prompt = (
            f"Assess whether this coverage gap represents genuinely "
            f"unreachable logic or is simply untested:\n\n"
            f"Gap: {gap_info.get('description', '')}\n"
            f"Conditions: {gap_info.get('conditions', [])}\n\n"
            f"RTL:\n```\n{rtl_content[:2000]}\n```\n\n"
            f"Provide:\n"
            f"1. Reachability assessment (reachable/unreachable/uncertain)\n"
            f"2. Reasoning\n"
            f"3. If reachable, what stimulus is needed"
        )

        response = await self.llm.complete(prompt)
        return self._format_response(response)


class DebugAgent(BaseAgent):
    """AI agent for debugging and root cause analysis."""

    def __init__(self):
        super().__init__("debug_agent")

    async def analyze_failure(self, failure_info: dict,
                               rtl_content: str = "",
                               log_analysis: dict = None) -> dict:
        """Perform AI-powered failure analysis."""
        if not self.llm.is_available:
            return {
                "analysis": "LLM not available. Using rule-based analysis only.",
                "is_ai_generated": False,
            }

        prompt = (
            f"Analyze this simulation failure and provide root cause analysis:\n\n"
            f"Failure Info:\n{self._format_failure(failure_info)}\n\n"
        )

        if log_analysis:
            prompt += f"Log Analysis:\n{self._format_log(log_analysis)}\n\n"

        if rtl_content:
            prompt += f"RTL Code:\n```\n{rtl_content[:3000]}\n```\n\n"

        prompt += (
            "Provide:\n"
            "1. FACTS (directly observed from logs/waveforms)\n"
            "2. ROOT CAUSE HYPOTHESIS (with confidence level)\n"
            "3. EVIDENCE supporting the hypothesis\n"
            "4. SUGGESTED INVESTIGATION steps\n"
            "5. POTENTIAL FIX"
        )

        response = await self.llm.analyze_failure(prompt, rtl_content)
        return self._format_response(response)

    def _format_failure(self, info: dict) -> str:
        lines = []
        for key, value in info.items():
            if isinstance(value, (str, int, float)):
                lines.append(f"{key}: {value}")
            elif isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value[:5])}")
        return "\n".join(lines)

    def _format_log(self, log: dict) -> str:
        lines = []
        for key in ["first_failure", "failure_clusters", "root_cause_analysis"]:
            if key in log:
                lines.append(f"{key}: {str(log[key])[:500]}")
        return "\n".join(lines)


class VerificationPlanAgent(BaseAgent):
    """AI agent for verification plan enhancement."""

    def __init__(self):
        super().__init__("vplan_agent")

    async def enhance_plan(self, plan_items: list, rtl_content: str) -> dict:
        """Enhance a verification plan with AI insights."""
        if not self.llm.is_available:
            return {
                "enhancement": "LLM not available. Using RTL-derived plan.",
                "is_ai_generated": False,
            }

        items_summary = "\n".join(
            f"- [{item.get('source_type', 'unknown')}] {item.get('title', '')}"
            for item in plan_items[:20]
        )

        prompt = (
            f"Review this verification plan for a SystemVerilog design and "
            f"suggest additional verification items that may be missing:\n\n"
            f"Current Plan Items:\n{items_summary}\n\n"
            f"RTL Code (first 2000 chars):\n```\n{rtl_content[:2000]}\n```\n\n"
            f"Suggest additional verification items, especially:\n"
            f"- Corner cases not covered\n"
            f"- Error conditions\n"
            f"- Protocol compliance\n"
            f"- Safety properties"
        )

        response = await self.llm.complete(prompt)
        return self._format_response(response)
