"""Coverage Analysis API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.engines.coverage_engine.analyzer import CoverageAnalyzer, CoverageData
from app.engines.test_generator.generator import TestGenerator
from app.engines.rtl_parser.parser import RTLParser

router = APIRouter(prefix="/coverage")


class CoverageAnalysisRequest(BaseModel):
    coverage_report: str
    rtl_content: Optional[str] = ""
    module_name: Optional[str] = ""


class CoverageGapRequest(BaseModel):
    coverage_report: str
    rtl_content: str
    module_name: str


class CoverageComparisonRequest(BaseModel):
    coverage_before: dict
    coverage_after: dict


@router.post("/analyze")
async def analyze_coverage(request: CoverageAnalysisRequest):
    """Analyze a coverage report and identify gaps."""
    analyzer = CoverageAnalyzer()

    # Try to parse as Verilator XML first
    coverage = analyzer.parse_verilator_xml(request.coverage_report)
    
    # If XML parsing didn't yield results, try text format
    if not any(d.overall > 0 for d in coverage.values()):
        coverage = analyzer.parse_verilator_coverage(request.coverage_report)
    
    # If still no results, try generic
    if not any(d.overall > 0 for d in coverage.values()):
        coverage = analyzer.parse_ucov_report(request.coverage_report)

    # Identify gaps
    gaps = analyzer.identify_gaps(coverage, request.rtl_content, request.module_name)

    # Generate report
    report = analyzer.generate_coverage_report(coverage, gaps, request.module_name)

    return {
        "report": report,
        "coverage": {
            ct: {"overall": d.overall, "covered": d.covered, "total": d.total}
            for ct, d in coverage.items()
        },
        "gaps": gaps,
    }


@router.post("/gaps")
async def identify_coverage_gaps(request: CoverageGapRequest):
    """Identify specific coverage gaps from RTL and coverage data."""
    analyzer = CoverageAnalyzer()

    # Try XML first
    coverage = analyzer.parse_verilator_xml(request.coverage_report)
    if not any(d.overall > 0 for d in coverage.values()):
        coverage = analyzer.parse_verilator_coverage(request.coverage_report)
    if not any(d.overall > 0 for d in coverage.values()):
        coverage = analyzer.parse_ucov_report(request.coverage_report)

    gaps = analyzer.identify_gaps(coverage, request.rtl_content, request.module_name)

    return {
        "total_gaps": len(gaps),
        "gaps": gaps,
        "gap_types": {
            "reachable_untested": len([g for g in gaps if g["gap_type"] == "reachable_untested"]),
            "potentially_unreachable": len([g for g in gaps if g["gap_type"] == "potentially_unreachable"]),
            "unreachable": len([g for g in gaps if g["gap_type"] == "unreachable"]),
        },
    }


@router.post("/generate-targeted-tests")
async def generate_targeted_tests(request: CoverageGapRequest):
    """Generate tests specifically targeting coverage gaps."""
    analyzer = CoverageAnalyzer()
    parser = RTLParser()
    test_gen = TestGenerator()

    # Parse RTL
    modules = parser.parse(request.rtl_content)
    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    # Parse coverage and find gaps
    coverage = analyzer.parse_verilator_xml(request.coverage_report)
    if not any(d.overall > 0 for d in coverage.values()):
        coverage = analyzer.parse_verilator_coverage(request.coverage_report)
    if not any(d.overall > 0 for d in coverage.values()):
        coverage = analyzer.parse_ucov_report(request.coverage_report)

    gaps = analyzer.identify_gaps(coverage, request.rtl_content, request.module_name)

    # Generate targeted tests
    tests = test_gen.generate(modules, gaps)

    return {
        "total_tests_generated": len(tests),
        "tests": [
            {
                "name": t["name"],
                "type": t["test_type"],
                "objective": t["verification_objective"],
                "target_coverage": t["target_coverage"],
                "code": t["code"],
            }
            for t in tests
        ],
        "gaps_addressed": len(gaps),
        "estimated_coverage_improvement": f"{min(100, len(gaps) * 2)}%",
    }


@router.post("/compare")
async def compare_coverage(request: CoverageComparisonRequest):
    """Compare before/after coverage reports."""
    analyzer = CoverageAnalyzer()

    # Convert dicts to CoverageData
    before = {}
    for ct, data in request.coverage_before.items():
        before[ct] = CoverageData(
            report_type=ct,
            overall=data.get("overall", 0),
            covered=data.get("covered", 0),
            total=data.get("total", 0),
        )

    after = {}
    for ct, data in request.coverage_after.items():
        after[ct] = CoverageData(
            report_type=ct,
            overall=data.get("overall", 0),
            covered=data.get("covered", 0),
            total=data.get("total", 0),
        )

    comparison = analyzer.compare_coverage(before, after)

    return {
        "comparison": comparison,
        "overall_improved": any(
            c["improved"] for c in comparison.values()
        ),
        "total_delta": sum(c["delta"] for c in comparison.values()),
    }
