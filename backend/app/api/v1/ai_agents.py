"""AI Agents API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.ai.agents.agents import (
    RTLAnalyzerAgent,
    TestGenAgent,
    CoverageAgent,
    DebugAgent,
    VerificationPlanAgent,
)
from app.ai.llm_client import get_llm_client

router = APIRouter(prefix="/ai")


class RTLInsightRequest(BaseModel):
    rtl_content: str
    parsed_modules: Optional[list[dict]] = None


class TestImprovementRequest(BaseModel):
    test_code: str
    failure_info: str
    rtl_content: str


class GapAnalysisRequest(BaseModel):
    gap_info: dict
    rtl_content: str


class AIConfigRequest(BaseModel):
    use_ai: bool = False


@router.get("/status")
async def ai_status():
    """Check AI configuration status."""
    client = get_llm_client()
    return {
        "ai_enabled": client.is_available,
        "provider": client.provider,
        "model": client.model,
        "base_url": client.base_url or "default",
        "mode": "online" if client.is_available else "offline"
    }


@router.post("/analyze-design")
async def analyze_design(request: RTLInsightRequest):
    """Get AI insights about a design's purpose and verification approach."""
    agent = RTLAnalyzerAgent()

    if not get_llm_client().is_available:
        # Return deterministic analysis when LLM is offline
        return {
            "analysis": (
                "LLM API not configured. Running in offline mode.\n"
                "To enable AI-powered design analysis, set LLM_API_KEY in .env"
            ),
            "is_ai_generated": False,
            "ai_status": "offline",
        }

    result = await agent.analyze_design_intent(
        request.rtl_content, request.parsed_modules or []
    )
    result["ai_status"] = "online"
    return result


@router.post("/improve-test")
async def improve_test(request: TestImprovementRequest):
    """Use AI to improve a failing test."""
    agent = TestGenAgent()

    if not get_llm_client().is_available:
        return {
            "improvement": "LLM API not configured. Running in offline mode.",
            "is_ai_generated": False,
            "ai_status": "offline",
        }

    result = await agent.improve_test(
        request.test_code, request.failure_info, request.rtl_content
    )
    result["ai_status"] = "online"
    return result


@router.post("/analyze-gap")
async def analyze_gap(request: GapAnalysisRequest):
    """Use AI to analyze a coverage gap and suggest targeted tests."""
    agent = CoverageAgent()

    if not get_llm_client().is_available:
        return {
            "analysis": "LLM API not configured. Running in offline mode.",
            "is_ai_generated": False,
            "ai_status": "offline",
        }

    result = await agent.analyze_gap(request.gap_info, request.rtl_content)
    result["ai_status"] = "online"
    return result


@router.post("/assess-reachability")
async def assess_reachability(request: GapAnalysisRequest):
    """Use AI to assess whether a coverage gap is reachable."""
    agent = CoverageAgent()

    if not get_llm_client().is_available:
        return {
            "assessment": "LLM API not configured. Running in offline mode.",
            "is_ai_generated": False,
            "ai_status": "offline",
        }

    result = await agent.assess_unreachability(request.gap_info, request.rtl_content)
    result["ai_status"] = "online"
    return result


@router.post("/debug-failure")
async def debug_failure(request: AIConfigRequest):
    """Run AI-powered debugging (compatible endpoint)."""
    return {"error": "Use /api/v1/failure-analysis with use_ai=true for full analysis"}