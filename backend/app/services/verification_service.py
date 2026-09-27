"""Verification service layer - orchestrates engines."""

import logging
from typing import Optional

from app.engines.rtl_parser.parser import RTLParser
from app.engines.knowledge_graph.builder import KnowledgeGraphBuilder
from app.engines.verification_planner.planner import VerificationPlanGenerator
from app.engines.assertion_generator.generator import AssertionGenerator
from app.engines.test_generator.generator import TestGenerator
from app.engines.coverage_engine.analyzer import CoverageAnalyzer
from app.engines.log_analyzer.analyzer import LogAnalyzer
from app.engines.root_cause_engine.engine import RootCauseEngine
from app.engines.regression_engine.engine import RegressionEngine
from app.engines.waveform_analyzer.analyzer import WaveformAnalyzer

logger = logging.getLogger(__name__)


class VerificationService:
    """Coordinates all verification engines into a unified workflow."""

    def __init__(self):
        self.parser = RTLParser()
        self.knowledge_graph = KnowledgeGraphBuilder()
        self.planner = VerificationPlanGenerator()
        self.assertion_gen = AssertionGenerator()
        self.test_gen = TestGenerator()
        self.coverage = CoverageAnalyzer()
        self.logs = LogAnalyzer()
        self.root_cause = RootCauseEngine()
        self.regression = RegressionEngine()
        self.waveform = WaveformAnalyzer()

    def analyze_rtl(self, content: str, filename: str = "design.sv") -> dict:
        """Complete RTL analysis pipeline."""
        modules = self.parser.parse(content, filename)
        graph = self.knowledge_graph.build(modules)

        return {
            "modules": modules,
            "summary": self.parser.get_design_summary(),
            "knowledge_graph": graph,
            "recommendations": self.knowledge_graph.get_modules_needing_verification(),
            "modules_without_assertions": self.knowledge_graph.get_modules_with_no_assertions(),
        }

    def generate_plan(self, content: str, specification: str = "") -> dict:
        """Generate a verification plan."""
        modules = self.parser.parse(content)
        return self.planner.generate(modules, specification)

    def generate_assertions(self, content: str) -> dict:
        """Generate SVA assertions."""
        modules = self.parser.parse(content)
        assertions = self.assertion_gen.generate(modules)
        return {
            "assertions": assertions,
            "total": len(assertions),
            "modules": [m.name for m in modules],
        }

    def generate_tests(self, content: str,
                       coverage_gaps: list = None,
                       test_types: list = None) -> dict:
        """Generate tests."""
        modules = self.parser.parse(content)
        tests = self.test_gen.generate(modules, coverage_gaps)
        if test_types:
            tests = [t for t in tests if t["test_type"] in test_types]
        return {"tests": tests, "total": len(tests)}

    def analyze_coverage(self, report: str, rtl: str = "",
                         module_name: str = "") -> dict:
        """Analyze coverage and identify gaps."""
        coverage = self.coverage.parse_verilator_coverage(report)
        if not any(d.overall > 0 for d in coverage.values()):
            coverage = self.coverage.parse_ucov_report(report)
        gaps = self.coverage.identify_gaps(coverage, rtl, module_name)
        report_out = self.coverage.generate_coverage_report(coverage, gaps, module_name)
        return {"coverage": coverage, "gaps": gaps, "report": report_out}

    def analyze_log(self, log_content: str) -> dict:
        """Analyze a simulation log."""
        return self.logs.parse_log(log_content)

    def root_cause_failure(self, failure_info: dict, rtl: str = "",
                           log_analysis: dict = None) -> dict:
        """Perform root cause analysis."""
        return self.root_cause.analyze(failure_info, rtl, log_analysis)

    def analyze_waveform_vcd(self, vcd_content: str) -> dict:
        """Analyze a VCD waveform."""
        return self.waveform.parse_vcd(vcd_content)

    def full_verification_flow(self, content: str,
                               specification: str = "") -> dict:
        """Run the complete verification pipeline."""
        result = {}

        # 1. Analyze RTL
        analysis = self.analyze_rtl(content)
        result["analysis"] = {
            "summary": analysis["summary"],
            "recommendations": analysis["recommendations"],
        }

        # 2. Generate plan
        plan = self.planner.generate(analysis["modules"], specification)
        result["plan"] = {
            "summary": plan["summary"],
            "items_preview": plan["items"][:10],
        }

        # 3. Generate assertions
        assertions = self.assertion_gen.generate(analysis["modules"])
        result["assertions"] = {
            "total": len(assertions),
            "preview": assertions[:10],
        }

        # 4. Generate tests
        tests = self.test_gen.generate(analysis["modules"])
        result["tests"] = {
            "total": len(tests),
            "types": {
                tt: len([t for t in tests if t["test_type"] == tt])
                for tt in set(t["test_type"] for t in tests)
            },
        }

        return result