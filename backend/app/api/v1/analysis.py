"""Failure Analysis, Regression, and Waveform API endpoints."""

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.engines.root_cause_engine.engine import RootCauseEngine
from app.engines.regression_engine.engine import RegressionEngine, TestResult
from app.engines.waveform_analyzer.analyzer import WaveformAnalyzer
from app.ai.agents.agents import DebugAgent

router = APIRouter()


# ─── Root Cause Analysis ──────────────────────────────────────────────

class FailureAnalysisRequest(BaseModel):
    failure_info: dict
    rtl_content: Optional[str] = ""
    log_analysis: Optional[dict] = None
    use_ai: bool = False


@router.post("/failure-analysis")
async def analyze_failure(request: FailureAnalysisRequest):
    """Perform root cause analysis on a simulation failure."""
    engine = RootCauseEngine()
    result = engine.analyze(request.failure_info, request.rtl_content,
                             request.log_analysis)

    # Add AI analysis if requested and available
    if request.use_ai:
        try:
            agent = DebugAgent()
            ai_analysis = await agent.analyze_failure(
                request.failure_info,
                request.rtl_content,
                request.log_analysis
            )
            result["ai_analysis"] = ai_analysis
        except Exception as e:
            result["ai_analysis"] = {"error": str(e)}

    return result


# ─── Regression ───────────────────────────────────────────────────────

class RegressionRequest(BaseModel):
    results: list[dict]
    changed_modules: Optional[list[str]] = None
    budget_minutes: float = 60.0


@router.post("/regression/analyze")
async def analyze_regression(request: RegressionRequest):
    """Analyze regression results: rank tests, detect issues."""
    engine = RegressionEngine()

    results = [
        TestResult(**{k: v for k, v in r.items() if k in
                     ["name", "status", "runtime_seconds", "coverage_delta",
                      "bugs_found", "is_flaky", "affected_modules"]})
        for r in request.results
    ]

    # Record in test history
    for r in results:
        if r.name not in engine.test_history:
            engine.test_history[r.name] = []
        engine.test_history[r.name].append(r)

    output = {
        "ranked_tests": engine.rank_tests(results),
        "flaky_tests": engine.detect_flaky_tests(results),
        "redundant_tests": engine.detect_redundant_tests(results),
    }

    if request.changed_modules:
        output["affected_tests"] = engine.identify_affected_tests(
            request.changed_modules, results
        )

    output["minimal_regression"] = engine.recommend_minimal_regression(
        results, request.budget_minutes
    )
    output["summary"] = engine.compute_regression_summary(results)

    return output


# ─── Waveform ─────────────────────────────────────────────────────────

class WaveformRequest(BaseModel):
    vcd_content: str


@router.post("/waveform/analyze")
async def analyze_waveform(request: WaveformRequest):
    """Analyze a VCD waveform file."""
    analyzer = WaveformAnalyzer()
    try:
        result = analyzer.parse_vcd(request.vcd_content)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Waveform parse error: {str(e)}")


class SignalContextRequest(BaseModel):
    vcd_content: str
    failure_time: float
    window: float = 100.0


@router.post("/waveform/signal-context")
async def signal_context(request: SignalContextRequest):
    """Get signal context around a failure time."""
    analyzer = WaveformAnalyzer()
    parsed = analyzer.parse_vcd(request.vcd_content)

    # Convert back to WaveformAnalysis objects
    signals = {}
    for name in parsed["signals"]:
        from app.engines.waveform_analyzer.analyzer import WaveformAnalysis
        signals[name] = WaveformAnalysis(signal_name=name)

    context = analyzer.analyze_signal_around_failure(
        signals, request.failure_time, request.window
    )
    return {"signals": context}