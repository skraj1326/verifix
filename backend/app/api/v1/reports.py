"""Professional Verification Report Generator API endpoints.

Every metric emitted by this module is derived from persisted database rows.
When evidence is missing the section reports UNKNOWN instead of inventing a
number, and no sign-off or pass/fail claim is ever made without stored proof.
"""

import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.models.database import TestStatus, Report

# PDF generation
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


router = APIRouter(prefix="/reports", tags=["Verification Reports"])

# Coverage targets are policy, not evidence, so they are surfaced explicitly.
DEFAULT_COVERAGE_TARGET = 90.0


def esc(value: Any) -> str:
    """HTML-escape any value before embedding it in report markup."""
    return html.escape("" if value is None else str(value), quote=True)


class ReportRequest(BaseModel):
    project_id: str
    simulation_id: Optional[str] = None
    format: str = "html"
    include_sections: Optional[List[str]] = None
    template: str = "standard"
    persist: bool = True  # Whether to persist the report to database


class ReportSection(BaseModel):
    id: str
    title: str
    content: str
    order: int
    type: str


class VerificationReport(BaseModel):
    id: str
    project_id: str
    title: str
    generated_at: datetime
    format: str
    sections: List[ReportSection]
    metadata: Dict[str, Any]


def _status_value(status: Any) -> str:
    return getattr(status, "value", status) if status is not None else "unknown"


def _mean(values: List[Optional[float]]) -> Optional[float]:
    real = [v for v in values if v is not None]
    if not real:
        return None
    return round(sum(real) / len(real), 2)


@router.post("/generate", response_model=VerificationReport)
async def generate_verification_report(request: ReportRequest):
    """Generate a verification report from persisted evidence only."""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.database import (
        Assertion,
        CoverageReport,
        Design,
        FailureAnalysis,
        Project,
        Simulation,
        Test,
        VerificationPlan,
    )

    async with AsyncSessionLocal() as db:
        project = (
            await db.execute(select(Project).where(Project.id == request.project_id))
        ).scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        designs = (
            await db.execute(select(Design).where(Design.project_id == request.project_id))
        ).scalars().all()

        simulation = None
        if request.simulation_id:
            simulation = (
                await db.execute(select(Simulation).where(Simulation.id == request.simulation_id))
            ).scalar_one_or_none()
            if not simulation:
                raise HTTPException(status_code=404, detail="Simulation not found")

        coverage_reports: List[Any] = []
        if simulation:
            coverage_reports = (
                await db.execute(
                    select(CoverageReport).where(CoverageReport.simulation_id == simulation.id)
                )
            ).scalars().all()

        tests = (
            await db.execute(select(Test).where(Test.project_id == request.project_id))
        ).scalars().all()

        assertions: List[Any] = []
        for design in designs:
            assertions.extend(
                (
                    await db.execute(select(Assertion).where(Assertion.design_id == design.id))
                ).scalars().all()
            )

        failures: List[Any] = []
        if simulation:
            failures = (
                await db.execute(
                    select(FailureAnalysis).where(FailureAnalysis.simulation_id == simulation.id)
                )
            ).scalars().all()

        plans = (
            await db.execute(
                select(VerificationPlan).where(VerificationPlan.project_id == request.project_id)
            )
        ).scalars().all()

        # Detach plain values so the section builders cannot touch the session.
        project_name = project.name
        design_rows = [
            {"name": d.name, "language": d.language, "status": _status_value(d.analysis_status)}
            for d in designs
        ]
        test_rows = [
            {
                "name": t.name,
                "type": t.test_type or "unknown",
                "status": _status_value(t.status),
                "objective": t.verification_objective or "",
            }
            for t in tests
        ]
        assertion_rows = [
            {
                "name": a.name,
                "type": a.assertion_type or "unknown",
                "confidence": _status_value(a.confidence),
                "is_verified": bool(a.is_verified),
            }
            for a in assertions
        ]
        failure_rows = [
            {
                "failure_type": f.failure_type or "unknown",
                "summary": f.summary or "",
                "confidence": _status_value(f.confidence),
                "is_confirmed": bool(f.is_confirmed),
            }
            for f in failures
        ]
        coverage_rows = [
            {
                "report_type": c.report_type or "unknown",
                "overall_coverage": c.overall_coverage,
                "details": c.details if isinstance(c.details, dict) else {},
                "gaps": c.gaps if isinstance(c.gaps, list) else [],
            }
            for c in coverage_reports
        ]
        plan_rows = [
            {
                "name": p.name,
                "status": _status_value(p.status),
                "item_count": len(p.items) if isinstance(p.items, list) else 0,
                "categories": sorted(
                    {
                        str(i.get("category"))
                        for i in (p.items or [])
                        if isinstance(i, dict) and i.get("category")
                    }
                )
                if isinstance(p.items, list)
                else [],
            }
            for p in plans
        ]
        sim_info = (
            {
                "simulator": simulation.simulator,
                "status": _status_value(simulation.status),
                "started_at": simulation.started_at.isoformat() if simulation.started_at else None,
                "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
            }
            if simulation
            else None
        )

    sections: List[ReportSection] = []
    wanted = request.include_sections

    def include(section_id: str) -> bool:
        return wanted is None or section_id in wanted

    if include("executive_summary"):
        sections.append(
            ReportSection(
                id="executive_summary",
                title="Executive Summary",
                content=generate_executive_summary(
                    project_name, design_rows, sim_info, coverage_rows, test_rows
                ),
                order=1,
                type="text",
            )
        )

    if include("design_overview"):
        sections.append(
            ReportSection(
                id="design_overview",
                title="Design Overview",
                content=generate_design_overview(design_rows),
                order=2,
                type="table",
            )
        )

    if include("verification_plan"):
        sections.append(
            ReportSection(
                id="verification_plan",
                title="Verification Plan",
                content=generate_verification_plan_section(plan_rows),
                order=3,
                type="list",
            )
        )

    if include("assertions"):
        sections.append(
            ReportSection(
                id="assertions",
                title="Assertions",
                content=generate_assertions_section(assertion_rows),
                order=4,
                type="table",
            )
        )

    if include("tests"):
        sections.append(
            ReportSection(
                id="tests",
                title="Tests",
                content=generate_tests_section(test_rows),
                order=5,
                type="table",
            )
        )

    if include("coverage"):
        sections.append(
            ReportSection(
                id="coverage",
                title="Coverage Analysis",
                content=generate_coverage_section(coverage_rows),
                order=6,
                type="chart",
            )
        )

    if include("failures"):
        sections.append(
            ReportSection(
                id="failures",
                title="Failures & Issues",
                content=generate_failures_section(failure_rows),
                order=7,
                type="list",
            )
        )

    if include("traceability"):
        sections.append(
            ReportSection(
                id="traceability",
                title="Requirement Traceability Matrix",
                content=generate_traceability_matrix(),
                order=8,
                type="table",
            )
        )

    if include("conclusions"):
        sections.append(
            ReportSection(
                id="conclusions",
                title="Conclusions & Recommendations",
                content=generate_conclusions(coverage_rows, test_rows, failure_rows),
                order=9,
                type="text",
            )
        )

    if include("appendices"):
        sections.append(
            ReportSection(
                id="appendices",
                title="Appendices",
                content=generate_appendices(design_rows, sim_info, test_rows),
                order=10,
                type="list",
            )
        )

    report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    generated_at = datetime.utcnow()
    report = VerificationReport(
        id=report_id,
        project_id=request.project_id,
        title=f"Verification Report - {project_name}",
        generated_at=generated_at,
        format=request.format,
        sections=sections,
        metadata={
            "project_name": project_name,
            "simulation_id": request.simulation_id,
            "template": request.template,
            "total_sections": len(sections),
            "evidence_policy": "All metrics derived from persisted rows; gaps reported as UNKNOWN.",
            "coverage_target": DEFAULT_COVERAGE_TARGET,
        },
    )

    # Persist to database if requested
    if request.persist:
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.database import Report as ReportModel
            from uuid import UUID
            async with AsyncSessionLocal() as db:
                db_report = ReportModel(
                    id=UUID(report_id.replace("report_", "").replace("_", "-")[:36]) if len(report_id) > 36 else UUID(int=0),
                    project_id=UUID(request.project_id),
                    simulation_id=UUID(request.simulation_id) if request.simulation_id else None,
                    title=f"Verification Report - {project_name}",
                    format=request.format,
                    template=request.template,
                    sections=[s.model_dump() for s in sections],
                    metadata={
                        "project_name": project_name,
                        "simulation_id": request.simulation_id,
                        "template": request.template,
                        "total_sections": len(sections),
                        "evidence_policy": "All metrics derived from persisted rows; gaps reported as UNKNOWN.",
                        "coverage_target": DEFAULT_COVERAGE_TARGET,
                    },
                    generated_by="api",
                    created_at=generated_at,
                )
                db.add(db_report)
                await db.commit()
        except Exception:
            # Don't fail generation if persistence fails
            pass

    return report


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get a persisted report by ID."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.database import Report as ReportModel
    from uuid import UUID

    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    async with AsyncSessionLocal() as db:
        report = (
            await db.execute(select(ReportModel).where(ReportModel.id == report_uuid))
        ).scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

    # Convert to VerificationReport format
    return VerificationReport(
        id=str(report.id),
        project_id=str(report.project_id),
        title=report.title,
        generated_at=report.created_at,
        format=report.format,
        sections=[ReportSection(**s) for s in report.sections],
        metadata=report.metadata,
    )


@router.get("")
async def list_reports(project_id: Optional[str] = None, limit: int = 50, offset: int = 0):
    """List persisted reports, optionally filtered by project."""
    from sqlalchemy import select, desc
    from app.core.database import AsyncSessionLocal
    from app.models.database import Report as ReportModel
    from uuid import UUID

    async with AsyncSessionLocal() as db:
        query = select(ReportModel).order_by(desc(ReportModel.created_at))
        if project_id:
            try:
                query = query.where(ReportModel.project_id == UUID(project_id))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project ID format")
        query = query.limit(limit).offset(offset)
        reports = (await db.execute(query)).scalars().all()

    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "title": r.title,
            "format": r.format,
            "template": r.template,
            "created_at": r.created_at.isoformat(),
            "total_sections": r.report_metadata.get("total_sections", 0),
        }
        for r in reports
    ]


@router.post("/export/{report_id}", response_class=Response)
async def export_report(report_id: str, request: ReportRequest):
    """Export a freshly generated report as HTML, JSON, or PDF.

    Reports are not persisted, so the report_id is not a lookup key; the caller
    supplies the same ReportRequest used for generation and the rendered document
    is returned.
    """
    if request.format not in {"html", "json", "pdf"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format '{request.format}'. Supported: html, json, pdf",
        )

    if request.format == "pdf" and not PDF_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="PDF export requires fpdf2. Install with: pip install fpdf2",
        )

    report = await generate_verification_report(request)
    payload = report.model_dump(mode="json")

    if request.format == "json":
        return Response(
            content=json.dumps(payload, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{report.id}.json"'},
        )

    if request.format == "pdf":
        pdf_bytes = render_pdf_document(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{report.id}.pdf"'},
        )

    return Response(
        content=render_html_document(report),
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{report.id}.html"'},
    )


def render_html_document(report: VerificationReport) -> str:
    """Render a full standalone HTML document for a report."""
    sections_html = "\n".join(
        f'<section id="{esc(s.id)}"><h2>{esc(s.title)}</h2>{s.content}</section>'
        for s in report.sections
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{esc(report.title)}</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         margin: 2rem auto; max-width: 60rem; color: #1f2937; line-height: 1.55; }}
 h1 {{ border-bottom: 2px solid #111827; padding-bottom: .5rem; }}
 h2 {{ margin-top: 2rem; border-bottom: 1px solid #d1d5db; padding-bottom: .25rem; }}
 .report-table {{ border-collapse: collapse; width: 100%; margin: .75rem 0; }}
 .report-table th, .report-table td {{ border: 1px solid #d1d5db; padding: .4rem .6rem; text-align: left; }}
 .report-table th {{ background: #f3f4f6; }}
 .evidence-unknown {{ color: #b45309; font-style: italic; }}
 .meta {{ color: #6b7280; font-size: .875rem; }}
</style>
</head>
<body>
<h1>{esc(report.title)}</h1>
<p class="meta">Generated {esc(report.generated_at)} - template: {esc(report.metadata.get('template'))}</p>
{sections_html}
</body>
</html>
"""


def render_pdf_document(report: VerificationReport) -> bytes:
    """Render a full standalone PDF document for a report."""
    if not PDF_AVAILABLE:
        raise RuntimeError("fpdf2 not installed")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, report.title, ln=True)
    pdf.ln(5)

    # Meta
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(100, 100, 100)
    meta = f"Generated {report.generated_at} - template: {report.metadata.get('template', 'standard')}"
    pdf.cell(0, 5, meta, ln=True)
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    # Sections
    for section in report.sections:
        # Section title
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, section.title, ln=True)
        pdf.ln(2)

        # Section content - strip HTML tags for PDF
        pdf.set_font("Helvetica", size=10)
        clean_content = _strip_html(section.content)
        pdf.multi_cell(0, 5, clean_content)
        pdf.ln(4)

    return pdf.output(dest="S").encode("latin-1")


def _strip_html(html_text: str) -> str:
    """Remove HTML tags for PDF rendering."""
    text = re.sub(r"<[^>]+>", "", html_text)
    # Replace HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("<", "<")
    text = text.replace(">", ">")
    text = text.replace("&", "&")
    text = text.replace('"', '"')
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _evidence_note(condition: bool, message: str) -> str:
    if condition:
        return ""
    return f'<p class="evidence-unknown">[UNKNOWN] {esc(message)}</p>'


def generate_executive_summary(project_name, design_rows, sim_info, coverage_rows, test_rows) -> str:
    """Executive summary containing only stored facts."""
    overall_values = [c["overall_coverage"] for c in coverage_rows]
    overall = _mean(overall_values)

    status_counts: Dict[str, int] = {}
    for t in test_rows:
        status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1
    status_line = ", ".join(f"{k}: {v}" for k, v in sorted(status_counts.items())) or "none recorded"

    coverage_cell = f"{overall:.1f}%" if overall is not None else "UNKNOWN"
    target_met = (
        f"<p>Observed mean coverage {overall:.1f}% is at or above the configured target of "
        f"{DEFAULT_COVERAGE_TARGET:.0f}%.</p>"
        if overall is not None and overall >= DEFAULT_COVERAGE_TARGET
        else ""
    )

    return f"""
    <p>This report presents stored verification evidence for <strong>{esc(project_name)}</strong>.</p>
    <h3>Recorded Facts</h3>
    <ul>
        <li>Designs stored: {len(design_rows)}</li>
        <li>Tests stored: {len(test_rows)} (status breakdown - {esc(status_line)})</li>
        <li>Mean persisted coverage across {len(coverage_rows)} stored report(s): {coverage_cell}</li>
        <li>Simulation referenced: {esc(sim_info['simulator']) if sim_info else 'none supplied'}</li>
    </ul>
    {target_met}
    <h3>Evidence Limitations</h3>
    {_evidence_note(bool(coverage_rows), "No persisted coverage reports were supplied, so no coverage claim can be made.")}
    {_evidence_note(any(t['status'] in (TestStatus.PASSED.value, TestStatus.FAILED.value) for t in test_rows), "No executed test results are stored for this project; pass/fail status is UNKNOWN.")}
    <p class="evidence-unknown">[UNKNOWN] Sign-off status is not asserted by this report.</p>
    """


def generate_design_overview(design_rows) -> str:
    if not design_rows:
        return '<h2>Design Overview</h2><p class="evidence-unknown">[UNKNOWN] No designs stored.</p>'
    html_out = "<h2>Design Overview</h2><table class=\"report-table\">"
    html_out += "<tr><th>Design</th><th>Language</th><th>Analysis Status</th></tr>"
    for d in design_rows:
        html_out += (
            f"<tr><td>{esc(d['name'])}</td><td>{esc(d['language'])}</td>"
            f"<td>{esc(d['status'])}</td></tr>"
        )
    return html_out + "</table>"


def generate_verification_plan_section(plan_rows) -> str:
    """Render only plans that were actually persisted."""
    if not plan_rows:
        return (
            "<h2>Verification Plan</h2>"
            '<p class="evidence-unknown">[UNKNOWN] No verification plan has been persisted for this '
            "project, so no plan content is shown.</p>"
        )

    html_out = "<h2>Verification Plan</h2><table class=\"report-table\">"
    html_out += "<tr><th>Plan</th><th>Status</th><th>Items Stored</th><th>Categories</th></tr>"
    for p in plan_rows:
        cats = ", ".join(p["categories"]) if p["categories"] else "none recorded"
        html_out += (
            f"<tr><td>{esc(p['name'])}</td><td>{esc(p['status'])}</td>"
            f"<td>{p['item_count']}</td><td>{esc(cats)}</td></tr>"
        )
    html_out += "</table>"
    return html_out


def generate_assertions_section(assertion_rows) -> str:
    if not assertion_rows:
        return '<h2>Assertions</h2><p class="evidence-unknown">[UNKNOWN] No assertions stored.</p>'
    html_out = (
        "<h2>Assertions</h2><table class=\"report-table\">"
        "<tr><th>Name</th><th>Type</th><th>Confidence</th><th>Verified</th></tr>"
    )
    for a in assertion_rows:
        html_out += (
            f"<tr><td>{esc(a['name'])}</td><td>{esc(a['type'])}</td>"
            f"<td>{esc(a['confidence'])}</td>"
            f"<td>{'yes' if a['is_verified'] else 'no'}</td></tr>"
        )
    return html_out + "</table>"


def generate_tests_section(test_rows) -> str:
    if not test_rows:
        return '<h2>Tests</h2><p class="evidence-unknown">[UNKNOWN] No tests stored.</p>'
    html_out = (
        "<h2>Tests</h2><table class=\"report-table\">"
        "<tr><th>Name</th><th>Type</th><th>Status</th><th>Objective</th></tr>"
    )
    for t in test_rows:
        objective = (t["objective"] or "")[:80]
        html_out += (
            f"<tr><td>{esc(t['name'])}</td><td>{esc(t['type'])}</td>"
            f"<td>{esc(t['status'])}</td><td>{esc(objective)}</td></tr>"
        )
    return html_out + "</table>"


def generate_coverage_section(coverage_rows) -> str:
    """Coverage section built strictly from persisted CoverageReport rows."""
    if not coverage_rows:
        return (
            "<h2>Coverage Analysis</h2>"
            '<p class="evidence-unknown">[UNKNOWN] No persisted coverage evidence.</p>'
        )

    overall_values = [c["overall_coverage"] for c in coverage_rows]
    overall = _mean(overall_values)

    html_out = "<h2>Coverage Analysis</h2>"
    html_out += f"<h3>Mean persisted coverage: {overall:.1f}%</h3>" if overall is not None else (
        '<h3 class="evidence-unknown">[UNKNOWN] Mean persisted coverage</h3>'
    )
    html_out += (
        "<table class=\"report-table\"><tr><th>Type</th><th>Coverage %</th>"
        "<th>Covered</th><th>Total</th><th>Module</th></tr>"
    )
    for c in coverage_rows:
        details = c["details"]
        html_out += (
            f"<tr><td>{esc(c['report_type'])}</td>"
            f"<td>{c['overall_coverage']:.1f}%</td>"
            f"<td>{esc(details.get('covered', 'UNKNOWN'))}</td>"
            f"<td>{esc(details.get('total', 'UNKNOWN'))}</td>"
            f"<td>{esc(details.get('module') or 'UNKNOWN')}</td></tr>"
        )
    html_out += "</table>"

    all_gaps = [g for c in coverage_rows for g in c["gaps"] if isinstance(g, dict)]
    if all_gaps:
        html_out += f"<h3>Coverage Gaps ({len(all_gaps)})</h3>"
        html_out += (
            "<table class=\"report-table\"><tr><th>Type</th><th>Description</th>"
            "<th>Location</th><th>Suggested Test</th></tr>"
        )
        for gap in all_gaps[:25]:
            loc = gap.get("rtl_location", {}) or {}
            location = ", ".join(f"{k}={esc(v)}" for k, v in loc.items()) or "UNKNOWN"
            html_out += (
                f"<tr><td>{esc(gap.get('gap_type', 'unknown'))}</td>"
                f"<td>{esc(gap.get('description', ''))}</td>"
                f"<td>{location}</td>"
                f"<td>{esc(gap.get('suggested_test', ''))}</td></tr>"
            )
        html_out += "</table>"
    else:
        html_out += '<p class="evidence-unknown">[UNKNOWN] No coverage gaps recorded.</p>'

    return html_out


def generate_failures_section(failure_rows) -> str:
    if not failure_rows:
        return (
            "<h2>Failures & Issues</h2>"
            '<p class="evidence-unknown">[UNKNOWN] No failure analyses stored for this simulation.</p>'
        )
    html_out = (
        "<h2>Failures & Issues</h2><table class=\"report-table\">"
        "<tr><th>Type</th><th>Summary</th><th>Confidence</th><th>Confirmed</th></tr>"
    )
    for f in failure_rows:
        html_out += (
            f"<tr><td>{esc(f['failure_type'])}</td>"
            f"<td>{esc((f['summary'] or '')[:100])}</td>"
            f"<td>{esc(f['confidence'])}</td>"
            f"<td>{'yes' if f['is_confirmed'] else 'no'}</td></tr>"
        )
    return html_out + "</table>"


def generate_traceability_matrix() -> str:
    """Traceability cannot be stated without a persisted requirement store.

    Requirements are parsed into transient engine output today and are never
    persisted, so this section explicitly reports UNKNOWN rather than inventing
    requirement/assertion/test/coverage rows.
    """
    return (
        "<h2>Requirement Traceability Matrix</h2>"
        '<p class="evidence-unknown">[UNKNOWN] Requirement traceability cannot be reported.</p>'
        "<p>Requirements parsed from specifications are not yet persisted to a requirement "
        "store, so no requirement-to-assertion-to-test mapping exists as evidence. "
        "Persist requirements before sign-off so this matrix can be generated from real data.</p>"
    )


def generate_conclusions(coverage_rows, test_rows, failure_rows) -> str:
    """Conclusions that state observations without asserting sign-off."""
    overall = _mean([c["overall_coverage"] for c in coverage_rows])

    passed = sum(1 for t in test_rows if t["status"] == TestStatus.PASSED.value)
    failed = sum(1 for t in test_rows if t["status"] == TestStatus.FAILED.value)
    executed = passed + failed

    summary = [
        f"Coverage evidence: {'mean %.1f%% across %d stored report(s)' % (overall, len(coverage_rows)) if overall is not None else 'UNKNOWN'}",
        f"Executed tests: {executed} of {len(test_rows)} stored (passed {passed}, failed {failed})",
        f"Stored failure analyses: {len(failure_rows)}",
    ]

    recommendations = []
    if overall is not None and overall < DEFAULT_COVERAGE_TARGET:
        recommendations.append(
            f"Persisted coverage ({overall:.1f}%) is below the configured target of "
            f"{DEFAULT_COVERAGE_TARGET:.0f}%; close the recorded gaps."
        )
    if executed == 0 and test_rows:
        recommendations.append(
            "Tests are generated but not executed; run the regression to obtain execution evidence."
        )
    if failure_rows:
        recommendations.append(
            f"Investigate {len(failure_rows)} stored failure analysis record(s)."
        )
    recommendations.append(
        "Persist requirements and verification plans to enable traceability reporting."
    )

    rec_html = "".join(f"<li>{esc(r)}</li>" for r in recommendations)

    return f"""
    <h2>Conclusions & Recommendations</h2>
    <h3>Observations</h3>
    <ul>{"".join(f"<li>{esc(s)}</li>" for s in summary)}</ul>
    <p class="evidence-unknown">[UNKNOWN] This report does not assert sign-off or verification
    completion; no formal sign-off evidence is stored.</p>
    <h3>Recommendations</h3>
    <ol>{rec_html}</ol>
    """


def generate_appendices(design_rows, sim_info, test_rows) -> str:
    design_items = "".join(
        f"<li>{esc(d['name'])} ({esc(d['language'])}) - {esc(d['status'])}</li>" for d in design_rows
    ) or "<li>UNKNOWN - no designs stored</li>"
    test_items = "".join(
        f"<li>{esc(t['name'])} ({esc(t['type'])}) - {esc(t['status'])}</li>" for t in test_rows
    ) or "<li>UNKNOWN - no tests stored</li>"

    if sim_info:
        sim_block = (
            f"<p>Simulator: {esc(sim_info['simulator'])}</p>"
            f"<p>Status: {esc(sim_info['status'])}</p>"
            f"<p>Started: {esc(sim_info['started_at'] or 'UNKNOWN')}</p>"
            f"<p>Completed: {esc(sim_info['completed_at'] or 'UNKNOWN')}</p>"
        )
    else:
        sim_block = '<p class="evidence-unknown">[UNKNOWN] No simulation supplied.</p>'

    html_parts = [
        "<h2>Appendices</h2>",
        "<h3>Appendix A: Design List</h3>",
        f"<ul>{design_items}</ul>",
        "<h3>Appendix B: Test List</h3>",
        f"<ul>{test_items}</ul>",
        "<h3>Appendix C: Simulation Details</h3>",
        sim_block,
    ]
    return "\n".join(html_parts)
