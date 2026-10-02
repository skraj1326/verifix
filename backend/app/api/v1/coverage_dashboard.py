"""Coverage Dashboard API - serves only persisted, real coverage evidence.

Every value returned here originates from a CoverageReport/CoverageGap row that
was written from actual simulator output by POST /coverage/analyze. No metric,
bin, coverpoint or trend is ever synthesized.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/coverage", tags=["Coverage Dashboard"])

NO_EVIDENCE = {
    "summary": None,
    "covergroups": [],
    "coverpoints": [],
    "bins": [],
    "trends": [],
    "gaps": [],
    "evidence": "UNKNOWN",
    "note": "No persisted coverage evidence available for this project.",
}


class CoverageSummary(BaseModel):
    overall: Optional[float] = None
    line: Optional[float] = None
    branch: Optional[float] = None
    toggle: Optional[float] = None
    fsm: Optional[float] = None
    functional: Optional[float] = None
    assertion: Optional[float] = None


class BinSummary(BaseModel):
    name: str
    covered: Optional[bool] = None
    hits: Optional[int] = None
    expression: str = ""


class CoverageDrillDown(BaseModel):
    module: Optional[str] = None
    covergroup: Optional[str] = None
    coverpoints: List[Dict[str, Any]] = []
    evidence: str = "UNKNOWN"


class CoverageTrendPoint(BaseModel):
    simulation_id: str
    timestamp: Optional[str] = None
    line: Optional[float] = None
    branch: Optional[float] = None
    toggle: Optional[float] = None
    functional: Optional[float] = None
    overall: Optional[float] = None


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _overall_of(reports: List[Any]) -> Optional[float]:
    """Mean overall_coverage across the supplied real reports."""
    values = [r.overall_coverage for r in reports if r.overall_coverage is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


@router.get("/dashboard/{project_id}")
async def get_coverage_dashboard(project_id: str):
    """Coverage dashboard built strictly from persisted coverage reports."""
    from sqlalchemy import desc, select

    from app.core.database import AsyncSessionLocal
    from app.models.database import CoverageReport, Project, Simulation

    async with AsyncSessionLocal() as db:
        project = await db.execute(select(Project).where(Project.id == project_id))
        if project.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Latest simulation that actually produced coverage evidence.
        sim_result = await db.execute(
            select(Simulation)
            .where(Simulation.project_id == project_id)
            .order_by(desc(Simulation.completed_at), desc(Simulation.started_at))
        )
        simulations = sim_result.scalars().all()

        if not simulations:
            return {"project_id": project_id, "latest_simulation_id": None, **NO_EVIDENCE}

        latest_sim = simulations[0]

        latest_result = await db.execute(
            select(CoverageReport).where(CoverageReport.simulation_id == latest_sim.id)
        )
        latest_reports = latest_result.scalars().all()

        if not latest_reports:
            return {
                "project_id": project_id,
                "latest_simulation_id": str(latest_sim.id),
                "simulator": latest_sim.simulator,
                **NO_EVIDENCE,
            }

        by_type: Dict[str, float] = {r.report_type: _as_float(r.overall_coverage) for r in latest_reports}
        summary = CoverageSummary(
            overall=_overall_of(latest_reports),
            line=by_type.get("line"),
            branch=by_type.get("branch"),
            toggle=by_type.get("toggle"),
            fsm=by_type.get("fsm"),
            functional=by_type.get("functional"),
            assertion=by_type.get("assertion"),
        )

        # Covergroups are only present when the simulator produced them.
        covergroups = []
        for report in latest_reports:
            details = report.details if isinstance(report.details, dict) else {}
            for group in details.get("covergroups", []) or []:
                if isinstance(group, dict):
                    covergroups.append(group)

        gaps: List[Dict[str, Any]] = []
        for report in latest_reports:
            for gap in report.gaps or []:
                if isinstance(gap, dict):
                    gaps.append(gap)

        gaps_by_type: Dict[str, int] = {}
        for gap in gaps:
            key = gap.get("gap_type", "unknown")
            gaps_by_type[key] = gaps_by_type.get(key, 0) + 1

        return {
            "project_id": project_id,
            "latest_simulation_id": str(latest_sim.id),
            "simulator": latest_sim.simulator,
            "simulation_date": latest_sim.completed_at.isoformat() if latest_sim.completed_at else None,
            "summary": summary.model_dump(),
            "covergroups": covergroups,
            "gaps": gaps[:50],
            "gaps_by_type": gaps_by_type,
            "total_gaps": len(gaps),
            "evidence": "FACT",
            "source": "persisted CoverageReport rows",
        }


@router.get("/drilldown/{project_id}/{module_name}")
async def get_coverage_drilldown(project_id: str, module_name: str, covergroup: Optional[str] = None):
    """Drill into persisted covergroup/coverpoint evidence for a module."""
    from sqlalchemy import desc, select

    from app.core.database import AsyncSessionLocal
    from app.models.database import CoverageReport, Project, Simulation

    async with AsyncSessionLocal() as db:
        project = await db.execute(select(Project).where(Project.id == project_id))
        if project.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        sim_result = await db.execute(
            select(Simulation)
            .where(Simulation.project_id == project_id)
            .order_by(desc(Simulation.completed_at), desc(Simulation.started_at))
        )
        simulations = sim_result.scalars().all()
        if not simulations:
            return {**NO_EVIDENCE, "module": module_name, "covergroup": covergroup}

        cov_result = await db.execute(
            select(CoverageReport).where(CoverageReport.simulation_id.in_([s.id for s in simulations]))
        )
        reports = cov_result.scalars().all()

        coverpoints: List[Dict[str, Any]] = []
        matched = False
        for report in reports:
            details = report.details if isinstance(report.details, dict) else {}
            if details.get("module") and details["module"] != module_name:
                continue
            for group in details.get("covergroups", []) or []:
                if not isinstance(group, dict):
                    continue
                if covergroup and group.get("name") != covergroup:
                    continue
                matched = True
                coverpoints.extend(group.get("coverpoints", []) or [])

        return {
            "module": module_name,
            "covergroup": covergroup,
            "coverpoints": coverpoints,
            "evidence": "FACT" if matched else "UNKNOWN",
            "note": None if matched else "No persisted covergroup evidence for this module.",
        }


@router.get("/bins/{project_id}/{module_name}/{covergroup_name}/{coverpoint_name}")
async def get_bin_details(project_id: str, module_name: str, covergroup_name: str, coverpoint_name: str):
    """Return persisted bin-level evidence for a coverpoint."""
    from sqlalchemy import desc, select

    from app.core.database import AsyncSessionLocal
    from app.models.database import CoverageReport, Project, Simulation

    async with AsyncSessionLocal() as db:
        project = await db.execute(select(Project).where(Project.id == project_id))
        if project.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        sim_result = await db.execute(
            select(Simulation)
            .where(Simulation.project_id == project_id)
            .order_by(desc(Simulation.completed_at), desc(Simulation.started_at))
        )
        simulations = sim_result.scalars().all()
        if not simulations:
            return {**NO_EVIDENCE, "coverpoint": coverpoint_name}

        cov_result = await db.execute(
            select(CoverageReport).where(CoverageReport.simulation_id.in_([s.id for s in simulations]))
        )
        reports = cov_result.scalars().all()

        for report in reports:
            details = report.details if isinstance(report.details, dict) else {}
            for group in details.get("covergroups", []) or []:
                if not isinstance(group, dict) or group.get("name") != covergroup_name:
                    continue
                for point in group.get("coverpoints", []) or []:
                    if not isinstance(point, dict) or point.get("name") != coverpoint_name:
                        continue
                    return {
                        "module": module_name,
                        "covergroup": covergroup_name,
                        "coverpoint": coverpoint_name,
                        "bins": point.get("bins", []) or [],
                        "evidence": "FACT",
                    }

        return {
            "module": module_name,
            "covergroup": covergroup_name,
            "coverpoint": coverpoint_name,
            "bins": [],
            "evidence": "UNKNOWN",
            "note": "No persisted bin evidence for this coverpoint.",
        }


@router.get("/trends/{project_id}")
async def get_coverage_trends(project_id: str, days: int = 30):
    """Coverage trend derived from real historical coverage reports."""
    from datetime import timedelta

    from sqlalchemy import desc, select

    from app.core.database import AsyncSessionLocal
    from app.models.database import CoverageReport, Project, Simulation

    cutoff = datetime.utcnow() - timedelta(days=days)

    async with AsyncSessionLocal() as db:
        project = await db.execute(select(Project).where(Project.id == project_id))
        if project.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        sim_result = await db.execute(
            select(Simulation)
            .where(Simulation.project_id == project_id)
            .where(Simulation.completed_at.isnot(None))
            .where(Simulation.completed_at >= cutoff)
            .order_by(desc(Simulation.completed_at))
        )
        simulations = sim_result.scalars().all()

        if not simulations:
            return {"project_id": project_id, "trends": [], "evidence": "UNKNOWN",
                    "note": "No completed simulations in the requested window."}

        cov_result = await db.execute(
            select(CoverageReport).where(CoverageReport.simulation_id.in_([s.id for s in simulations]))
        )
        reports = cov_result.scalars().all()

        grouped: Dict[str, List[Any]] = {}
        for report in reports:
            grouped.setdefault(str(report.simulation_id), []).append(report)

        points: List[CoverageTrendPoint] = []
        for sim in simulations:
            sim_reports = grouped.get(str(sim.id), [])
            if not sim_reports:
                continue
            by_type = {r.report_type: _as_float(r.overall_coverage) for r in sim_reports}
            points.append(
                CoverageTrendPoint(
                    simulation_id=str(sim.id),
                    timestamp=sim.completed_at.isoformat() if sim.completed_at else None,
                    overall=_overall_of(sim_reports),
                    line=by_type.get("line"),
                    branch=by_type.get("branch"),
                    toggle=by_type.get("toggle"),
                    functional=by_type.get("functional"),
                )
            )

        points.sort(key=lambda p: p.timestamp or "")

        return {
            "project_id": project_id,
            "days": days,
            "trends": [p.model_dump() for p in points],
            "evidence": "FACT" if points else "UNKNOWN",
        }