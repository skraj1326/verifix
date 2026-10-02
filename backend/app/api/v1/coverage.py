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
    # Optional persistence target. When both are supplied, the analysis is
    # stored so the dashboard/trends endpoints can serve real evidence.
    project_id: Optional[str] = None
    simulation_id: Optional[str] = None


class PersistedCoverageResult(BaseModel):
    simulation_id: str
    reports_created: int
    gaps_created: int
    evidence: str = "FACT"
    note: str = "Coverage results persisted from the supplied simulator report."


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

    response = {
        "report": report,
        "coverage": {
            ct: {"overall": d.overall, "covered": d.covered, "total": d.total}
            for ct, d in coverage.items()
        },
        "gaps": gaps,
    }

    # Persist real evidence when a simulation is identified.
    if request.project_id and request.simulation_id:
        persisted = await _persist_coverage_results(
            request.project_id, request.simulation_id, coverage, gaps, request.module_name
        )
        response["persisted"] = persisted.model_dump()

    return response


async def _persist_coverage_results(project_id, simulation_id, coverage: dict, gaps: list, module_name: str = ""):
    """Store analyzed coverage results as database rows.

    Only real analyzer output is written. Nothing is synthesized here.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.database import CoverageGap, CoverageReport, Simulation
    from app.models.database import SeverityLevel
    from sqlalchemy import select

    created_reports = 0
    created_gaps = 0

    async with AsyncSessionLocal() as db:
        sim = await db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        sim_row = sim.scalar_one_or_none()
        if not sim_row:
            raise HTTPException(
                status_code=404, detail="Simulation not found; coverage was analyzed but not persisted"
            )

        saved_reports: list = []
        for cov_type, data in coverage.items():
            # Skip empty coverage types - storing zeros would fabricate evidence.
            if not data.total:
                continue
            row = CoverageReport(
                simulation_id=sim_row.id,
                report_type=cov_type,
                overall_coverage=float(data.overall),
                details={
                    "covered": int(data.covered),
                    "total": int(data.total),
                    "module": module_name,
                },
                gaps=[g for g in gaps if g.get("coverage_type") == cov_type],
            )
            saved_reports.append(row)
            db.add(row)
            created_reports += 1

        await db.flush()

        # CoverageGap.report_id is non-nullable, so gaps are only stored when at
        # least one real coverage report was persisted for this simulation.
        if saved_reports:
            for gap in gaps:
                impact = gap.get("estimated_impact") or 0.0
                if impact >= 70:
                    severity = SeverityLevel.ERROR
                elif impact >= 30:
                    severity = SeverityLevel.WARNING
                else:
                    severity = SeverityLevel.INFO
                db.add(
                    CoverageGap(
                        report_id=saved_reports[0].id,
                        gap_type=gap.get("gap_type", "unknown"),
                        description=gap.get("description", ""),
                        rtl_location=gap.get("rtl_location", {}),
                        conditions=gap.get("conditions", []),
                        suggested_test=gap.get("suggested_test", ""),
                        severity=severity,
                    )
                )
                created_gaps += 1

        await db.commit()

    return PersistedCoverageResult(
        simulation_id=str(simulation_id),
        reports_created=created_reports,
        gaps_created=created_gaps,
    )


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
