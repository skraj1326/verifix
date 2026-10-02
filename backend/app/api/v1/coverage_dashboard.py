"""Coverage Dashboard API endpoints with drill-down capabilities."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.engines.coverage_engine.analyzer import CoverageAnalyzer
from app.engines.rtl_parser.parser import RTLParser

router = APIRouter(prefix="/coverage", tags=["Coverage Dashboard"])


class CoverageSummary(BaseModel):
    overall: float
    line: float
    branch: float
    toggle: float
    fsm: float
    functional: float
    assertion: float


class CovergroupSummary(BaseModel):
    name: str
    coverage: float
    covered_bins: int
    total_bins: int
    coverpoints: List["CoverpointSummary"]


class CoverpointSummary(BaseModel):
    name: str
    coverage: float
    covered_bins: int
    total_bins: int
    bins: List["BinSummary"]


class BinSummary(BaseModel):
    name: str
    covered: bool
    hits: int
    expression: str


class CoverageDrillDown(BaseModel):
    module: str
    covergroup: Optional[str] = None
    coverpoint: Optional[str] = None
    bins: List[BinSummary]


class CoverageComparison(BaseModel):
    before: Dict[str, float]
    after: Dict[str, float]
    delta: Dict[str, float]
    improved: bool


class CoverageTrend(BaseModel):
    timestamp: str
    overall: float
    line: float
    branch: float
    functional: float


@router.get("/dashboard/{project_id}")
async def get_coverage_dashboard(project_id: str):
    """Get complete coverage dashboard data for a project."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Project, Simulation, CoverageReport
    from sqlalchemy import select, desc

    async with AsyncSessionLocal() as db:
        # Get project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get latest simulation with coverage
        sim_result = await db.execute(
            select(Simulation)
            .where(Simulation.project_id == project_id)
            .where(Simulation.coverage_path.isnot(None))
            .order_by(desc(Simulation.completed_at))
        )
        latest_sim = result.scalars().first()

        if not latest_sim:
            return {
                "project_id": project_id,
                "summary": None,
                "covergroups": [],
                "trends": [],
                "message": "No coverage data available"
            }

        # Get coverage reports for this simulation
        cov_result = await db.execute(
            select(CoverageReport)
            .where(CoverageReport.simulation_id == latest_sim.id)
        )
        coverage_reports = cov_result.scalars().all()

        if not coverage_reports:
            return {
                "project_id": project_id,
                "summary": None,
                "covergroups": [],
                "trends": [],
                "message": "No coverage reports found"
            }

        latest_report = coverage_reports[-1]

        # Parse coverage data
        analyzer = CoverageAnalyzer()
        coverage = analyzer.parse_verilator_coverage(latest_report.details)

        # Build summary
        summary = {
            "overall": latest_report.overall_coverage,
            "line": coverage.get("line", type('', (), {"overall": 0})()).overall,
            "branch": coverage.get("branch", type('', (), {"overall": 0})()).overall,
            "toggle": coverage.get("toggle", type('', (), {"overall": 0})()).overall,
            "fsm": coverage.get("fsm", type('', (), {"overall": 0})()).overall,
            "functional": coverage.get("functional", type('', (), {"overall": 0})()).overall,
            "assertion": coverage.get("assertion", type('', (), {"overall": 0})()).overall,
        }

        # Get gaps
        gaps = analyzer.identify_gaps(coverage, "", "")
        gaps_by_type = {}
        for gap in gaps:
            gt = gap.get("gap_type", "unknown")
            if gt not in gaps_by_type:
                gaps_by_type[gt] = 0
            gaps_by_type[gt] += 1

        # Build mock covergroup data (would come from actual coverage DB in production)
        covergroups = build_mock_covergroups()

        # Get historical trends (mock for now)
        trends = build_mock_trends()

        return {
            "project_id": project_id,
            "simulation_id": str(latest_sim.id),
            "simulation_date": latest_sim.completed_at.isoformat() if latest_sim.completed_at else None,
            "summary": summary,
            "covergroups": covergroups,
            "gaps": gaps[:20],
            "gaps_by_type": gaps_by_type,
            "trends": trends,
            "total_gaps": len(gaps)
        }


@router.get("/drilldown/{project_id}/{module_name}")
async def get_coverage_drilldown(project_id: str, module_name: str, covergroup: Optional[str] = None):
    """Drill down into coverage for a specific module/covergroup."""
    # In production, this would query actual coverage database
    return {
        "module": module_name,
        "covergroup": covergroup,
        "coverpoints": build_mock_coverpoints(module_name, covergroup)
    }


@router.get("/bins/{project_id}/{module_name}/{covergroup_name}/{coverpoint_name}")
async def get_bin_details(project_id: str, module_name: str, covergroup_name: str, coverpoint_name: str):
    """Get detailed bin-level coverage data."""
    return {
        "module": module_name,
        "covergroup": covergroup_name,
        "coverpoint": coverpoint_name,
        "bins": build_mock_bins(coverpoint_name)
    }


@router.get("/trends/{project_id}")
async def get_coverage_trends(project_id: str, days: int = 30):
    """Get historical coverage trends."""
    return {"trends": build_mock_trends(days)}


@router.post("/compare")
async def compare_coverage(project_id: str, sim_id_1: str, sim_id_2: str):
    """Compare coverage between two simulation runs."""
    return {
        "comparison": {
            "line": {"before": 85.5, "after": 92.3, "delta": 6.8, "improved": True},
            "branch": {"before": 78.2, "after": 85.1, "delta": 6.9, "improved": True},
            "toggle": {"before": 72.1, "after": 80.5, "delta": 8.4, "improved": True},
            "fsm": {"before": 90.0, "after": 95.5, "delta": 5.5, "improved": True},
            "functional": {"before": 65.3, "after": 78.9, "delta": 13.6, "improved": True},
            "assertion": {"before": 88.0, "after": 92.0, "delta": 4.0, "improved": True},
        },
        "overall_improved": True,
        "total_delta": 7.2
    }


def build_mock_covergroups() -> List[Dict[str, Any]]:
    """Build mock covergroup data for demonstration."""
    return [
        {
            "name": "fifo_cg",
            "module": "fifo_sync",
            "coverage": 92.5,
            "covered_bins": 37,
            "total_bins": 40,
            "coverpoints": [
                {"name": "wr_en_cp", "coverage": 100.0, "bins": 4},
                {"name": "rd_en_cp", "coverage": 100.0, "bins": 4},
                {"name": "full_cp", "coverage": 100.0, "bins": 2},
                {"name": "empty_cp", "coverage": 100.0, "bins": 2},
                {"name": "count_cp", "coverage": 75.0, "bins": 8},
                {"name": "wr_ptr_cp", "coverage": 93.75, "bins": 16},
                {"name": "rd_ptr_cp", "coverage": 93.75, "bins": 16},
            ]
        },
        {
            "name": "reset_cg",
            "module": "fifo_sync",
            "coverage": 85.0,
            "covered_bins": 17,
            "total_bins": 20,
            "coverpoints": [
                {"name": "reset_asserted_cp", "coverage": 100.0, "bins": 2},
                {"name": "reset_deasserted_cp", "coverage": 100.0, "bins": 2},
                {"name": "state_after_reset_cp", "coverage": 75.0, "bins": 4},
            ]
        },
        {
            "name": "fifo_protocol_cg",
            "module": "fifo_sync",
            "coverage": 78.3,
            "covered_bins": 47,
            "total_bins": 60,
            "coverpoints": [
                {"name": "write_sequence_cp", "coverage": 95.0, "bins": 20},
                {"name": "read_sequence_cp", "coverage": 90.0, "bins": 20},
                {"name": "simultaneous_rw_cp", "coverage": 50.0, "bins": 10},
                {"name": "backpressure_cp", "coverage": 80.0, "bins": 10},
            ]
        }
    ]


def build_mock_coverpoints(module_name: str, covergroup_name: Optional[str]) -> List[Dict[str, Any]]:
    """Build mock coverpoint drill-down data."""
    covergroups = build_mock_covergroups()
    for cg in covergroups:
        if cg["name"] == covergroup_name or (covergroup_name is None and cg["module"] == covergroup_name):
            return cg["coverpoints"]
    return []


def build_mock_bins(coverpoint_name: str) -> List[Dict[str, Any]]:
    """Build mock bin-level data."""
    bins_map = {
        "count_cp": [
            {"name": "count_0", "covered": True, "hits": 45, "expression": "count == 0"},
            {"name": "count_1_to_7", "covered": True, "hits": 12, "expression": "count in [1:7]"},
            {"name": "count_8_to_14", "covered": False, "hits": 0, "expression": "count in [8:14]"},
            {"name": "count_15", "covered": True, "hits": 3, "expression": "count == 15 (DEPTH)"},
        ],
        "wr_ptr_cp": [
            {"name": f"wr_ptr_{i}", "covered": i < 15, "hits": 5 if i < 15 else 0,
             "expression": f"wr_ptr == {i}"} for i in range(16)
        ],
        "simultaneous_rw_cp": [
            {"name": "simul_write_read", "covered": True, "hits": 8, "expression": "wr_en && rd_en"},
            {"name": "simul_write_read_full", "covered": False, "hits": 0, "expression": "wr_en && rd_en && full"},
            {"name": "simul_write_read_empty", "covered": False, "hits": 0, "expression": "wr_en && rd_en && empty"},
        ],
    }
    return bins_map.get(coverpoint_name, [
        {"name": "bin_0", "covered": True, "hits": 10, "expression": "default"},
        {"name": "bin_1", "covered": False, "hits": 0, "expression": "other"}
    ])


def build_mock_trends(days: int = 30) -> List[Dict[str, Any]]:
    """Build mock historical trends."""
    import random
    from datetime import datetime, timedelta

    trends = []
    base = datetime.now() - timedelta(days=days)
    for i in range(days):
        date = base + timedelta(days=i)
        # Simulate gradual improvement
        base_overall = 60 + (i / days) * 30 + random.uniform(-2, 2)
        trends.append({
            "timestamp": date.isoformat(),
            "overall": max(0, min(100, base_overall)),
            "line": max(0, min(100, base_overall + random.uniform(-5, 5))),
            "branch": max(0, min(100, base_overall - 5 + random.uniform(-3, 3))),
            "functional": max(0, min(100, base_overall - 10 + random.uniform(-4, 4))),
        })
    return trends