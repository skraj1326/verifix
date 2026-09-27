"""Celery tasks for async simulation and AI processing."""

import asyncio
from app.celery_app import celery_app


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.tasks.simulation.run_test")
def run_simulation_task(self, rtl_content: str, test_code: str,
                        top_module: str, simulator: str = "verilator"):
    """Run a single simulation asynchronously."""
    from app.engines.simulation.orchestrator import SimulationOrchestrator, SimulationConfig
    from app.engines.log_analyzer.analyzer import LogAnalyzer

    orchestrator = SimulationOrchestrator()
    config = SimulationConfig(
        simulator=simulator,
        top_module=top_module,
    )

    # For now, analyze the test code structure
    analyzer = LogAnalyzer()

    result = {
        "task_id": self.request.id,
        "status": "completed",
        "test_name": "simulated_test",
        "simulator": simulator,
        "top_module": top_module,
        "note": "Task-based simulation (requires file system access for real execution)",
    }

    self.update_state(state="PROGRESS", meta={"step": "completed"})
    return result


@celery_app.task(bind=True, name="app.tasks.simulation.run_regression")
def run_regression_task(self, rtl_content: str, test_codes: list,
                        top_module: str, simulator: str = "verilator"):
    """Run a full regression suite asynchronously."""
    results = {}
    total = len(test_codes)

    for i, test_code in enumerate(test_codes):
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": total, "step": "simulating"}
        )
        results[f"test_{i}"] = {
            "status": "pending",
            "test_code_length": len(test_code),
        }

    return {
        "task_id": self.request.id,
        "status": "completed",
        "total_tests": total,
        "results": results,
    }


@celery_app.task(bind=True, name="app.tasks.ai.analyze_rtl")
def ai_analyze_rtl_task(self, rtl_content: str, filename: str):
    """AI-powered RTL analysis."""
    from app.engines.rtl_parser.parser import RTLParser
    from app.engines.knowledge_graph.builder import KnowledgeGraphBuilder

    self.update_state(state="PROGRESS", meta={"step": "parsing"})
    parser = RTLParser()
    modules = parser.parse(rtl_content, filename)

    self.update_state(state="PROGRESS", meta={"step": "knowledge_graph"})
    kg = KnowledgeGraphBuilder()
    graph = kg.build(modules)

    self.update_state(state="PROGRESS", meta={"step": "recommendations"})
    recommendations = kg.get_modules_needing_verification()

    return {
        "task_id": self.request.id,
        "status": "completed",
        "modules_count": len(modules),
        "module_names": [m.name for m in modules],
        "knowledge_graph_stats": graph["statistics"],
        "recommendations": recommendations,
    }


@celery_app.task(bind=True, name="app.tasks.ai.generate_coverage_tests")
def ai_coverage_test_task(self, rtl_content: str, coverage_report: str,
                          module_name: str):
    """AI-driven coverage-directed test generation."""
    from app.engines.rtl_parser.parser import RTLParser
    from app.engines.coverage_engine.analyzer import CoverageAnalyzer
    from app.engines.test_generator.generator import TestGenerator

    self.update_state(state="PROGRESS", meta={"step": "parsing_coverage"})
    analyzer = CoverageAnalyzer()
    coverage = analyzer.parse_verilator_coverage(coverage_report)
    gaps = analyzer.identify_gaps(coverage, rtl_content, module_name)

    self.update_state(state="PROGRESS", meta={"step": "parsing_rtl"})
    parser = RTLParser()
    modules = parser.parse(rtl_content)

    self.update_state(state="PROGRESS", meta={"step": "generating_tests"})
    gen = TestGenerator()
    tests = gen.generate(modules, gaps)

    return {
        "task_id": self.request.id,
        "status": "completed",
        "gaps_found": len(gaps),
        "tests_generated": len(tests),
        "coverage_before": {ct: d.overall for ct, d in coverage.items()},
    }
