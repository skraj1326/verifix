"""End-to-end API tests that require a real PostgreSQL database.

These verify the persisted-evidence flow: project -> RTL analyze (persist) ->
hierarchy -> coverage analyze (persist) -> coverage dashboard -> report.

They are skipped unless TEST_DATABASE_URL points at a reachable PostgreSQL
instance, e.g.

    $env:TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/verifix_test"
    python -m pytest app/tests/api/test_api_persistence.py -v

The schema is created and dropped for the duration of the session.
"""

import os

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to run persistence tests against PostgreSQL.",
)

FIFO_SV = """
module fifo_sync #(parameter int DEPTH = 16) (
    input  logic clk,
    input  logic rst_n,
    input  logic wr_en,
    input  logic rd_en,
    output logic full,
    output logic empty
);
    localparam PTR_W = $clog2(DEPTH);
    logic [PTR_W-1:0] wr_ptr, rd_ptr;
    logic [PTR_W-1:0] count;

    assign full  = (count == DEPTH);
    assign empty = (count == 0);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= '0;
            rd_ptr <= '0;
            count  <= '0;
        end else begin
            if (wr_en && !full) begin
                wr_ptr <= wr_ptr + 1;
                count  <= count + 1;
            end
            if (rd_en && !empty) begin
                rd_ptr <= rd_ptr + 1;
                count  <= count - 1;
            end
        end
    end
endmodule
"""

VERILATOR_TEXT = """# SystemC::Coverage-3
# LCOV_EXCL_START
Summary:
  Lines        : 9123/10240 (89.1%)
  Branches     : 4821/5120 (94.2%)
  Toggles      : 12045/13610 (88.5%)
"""


@pytest.fixture(scope="module")
def db_client():
    """Rebind the app's database to the test database and create the schema."""
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import app.core.database as database
    from app.models.database import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    original_session_factory = database.AsyncSessionLocal

    async def _create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    import asyncio

    asyncio.get_event_loop().run_until_complete(_create_schema())

    database.AsyncSessionLocal = async_sessionmaker(
        bind=engine, expire_on_commit=False
    )

    # Route handlers import AsyncSessionLocal lazily from app.core.database,
    # so rebinding the module attribute is sufficient.
    import app.api.v1.coverage as coverage_api
    import app.api.v1.coverage_dashboard as dashboard_api
    import app.api.v1.reports as reports_api
    import app.api.v1.rtl_analysis as rtl_api
    import app.api.v1.rtl_hierarchy as hierarchy_api

    for module in (coverage_api, dashboard_api, reports_api, rtl_api, hierarchy_api):
        module.AsyncSessionLocal = database.AsyncSessionLocal

    from app.main import app as fastapi_app

    with TestClient(fastapi_app) as client:
        yield client

    async def _drop_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.get_event_loop().run_until_complete(_drop_schema())
    database.AsyncSessionLocal = original_session_factory


@pytest.fixture
def project_id(db_client):
    response = db_client.post("/api/v1/projects/", json={"name": "fifo_project"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


class TestPersistedEvidenceFlow:
    def test_analyze_with_project_id_persists_design(self, db_client, project_id):
        response = db_client.post(
            "/api/v1/rtl/analyze",
            json={"content": FIFO_SV, "filename": "fifo_sync.sv", "project_id": project_id},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["persisted"] is True
        assert body["design_id"]

        detail = db_client.get(f"/api/v1/projects/{project_id}").json()
        assert len(detail["designs"]) == 1

    def test_hierarchy_works_for_persisted_design(self, db_client, project_id):
        design_id = db_client.post(
            "/api/v1/rtl/analyze",
            json={"content": FIFO_SV, "filename": "fifo_sync.sv", "project_id": project_id},
        ).json()["design_id"]

        hierarchy = db_client.get(f"/api/v1/rtl/hierarchy/{design_id}")
        assert hierarchy.status_code == 200, hierarchy.text
        body = hierarchy.json()
        assert body["modules"][0]["name"] == "fifo_sync"
        assert "graph TD" in body["diagram"]["mermaid"]

    def test_hierarchy_unknown_design_returns_404(self, db_client):
        response = db_client.get("/api/v1/rtl/hierarchy/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_diagram_endpoint_uses_persisted_design(self, db_client, project_id):
        design_id = db_client.post(
            "/api/v1/rtl/analyze",
            json={"content": FIFO_SV, "filename": "fifo_sync.sv", "project_id": project_id},
        ).json()["design_id"]

        diagram = db_client.post(
            "/api/v1/rtl/diagram", json={"design_id": design_id, "format": "graphviz"}
        )
        assert diagram.status_code == 200
        assert diagram.json()["diagram"].startswith("digraph")

    def test_dashboard_reports_unknown_before_any_coverage(self, db_client, project_id):
        dashboard = db_client.get(f"/api/v1/coverage/dashboard/{project_id}")
        assert dashboard.status_code == 200
        body = dashboard.json()
        assert body["evidence"] == "UNKNOWN"
        assert body["summary"] is None
        assert body["covergroups"] == []

    def test_coverage_persists_and_dashboard_serves_it(self, db_client, project_id):
        simulation_id = _create_simulation(db_client, project_id)

        response = db_client.post(
            "/api/v1/coverage/analyze",
            json={
                "coverage_report": VERILATOR_TEXT,
                "rtl_content": FIFO_SV,
                "module_name": "fifo_sync",
                "project_id": project_id,
                "simulation_id": simulation_id,
            },
        )
        assert response.status_code == 200, response.text
        persisted = response.json()["persisted"]
        assert persisted["reports_created"] == 3
        assert persisted["evidence"] == "FACT"

        dashboard = db_client.get(f"/api/v1/coverage/dashboard/{project_id}").json()
        assert dashboard["evidence"] == "FACT"
        assert dashboard["summary"]["line"] == 89.1
        assert dashboard["summary"]["branch"] == 94.2
        assert dashboard["summary"]["toggle"] == 88.5

    def test_coverage_trends_uses_real_history(self, db_client, project_id):
        simulation_id = _create_simulation(db_client, project_id)
        db_client.post(
            "/api/v1/coverage/analyze",
            json={
                "coverage_report": VERILATOR_TEXT,
                "module_name": "fifo_sync",
                "project_id": project_id,
                "simulation_id": simulation_id,
            },
        )

        trends = db_client.get(f"/api/v1/coverage/trends/{project_id}").json()
        assert trends["evidence"] == "FACT"
        assert len(trends["trends"]) == 1
        assert trends["trends"][0]["line"] == 89.1

    def test_coverage_against_unknown_simulation_is_404(self, db_client, project_id):
        response = db_client.post(
            "/api/v1/coverage/analyze",
            json={
                "coverage_report": VERILATOR_TEXT,
                "project_id": project_id,
                "simulation_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code == 404

    def test_report_generates_from_stored_evidence(self, db_client, project_id):
        simulation_id = _create_simulation(db_client, project_id)
        db_client.post(
            "/api/v1/coverage/analyze",
            json={
                "coverage_report": VERILATOR_TEXT,
                "module_name": "fifo_sync",
                "project_id": project_id,
                "simulation_id": simulation_id,
            },
        )

        report = db_client.post(
            "/api/v1/reports/generate",
            json={"project_id": project_id, "simulation_id": simulation_id},
        )
        assert report.status_code == 200, report.text
        body = report.json()
        sections = {s["id"]: s["content"] for s in body["sections"]}

        assert "89.1%" in sections["coverage"]
        assert "[UNKNOWN]" in sections["traceability"]
        assert "fifo_sync" in sections["design_overview"]
        assert body["metadata"]["project_name"] == "fifo_project"

    def test_report_export_returns_html_document(self, db_client, project_id):
        response = db_client.post(
            "/api/v1/reports/export/report_x",
            json={"project_id": project_id, "format": "html"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert response.text.startswith("<!DOCTYPE html>")

    def test_report_export_rejects_pdf(self, db_client, project_id):
        response = db_client.post(
            "/api/v1/reports/export/report_x",
            json={"project_id": project_id, "format": "pdf"},
        )
        assert response.status_code == 400

    def test_report_for_unknown_project_is_404(self, db_client):
        response = db_client.post(
            "/api/v1/reports/generate",
            json={"project_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 404


def _create_simulation(db_client, project_id) -> str:
    """Insert a completed simulation row.

    No public endpoint creates Simulation rows yet, so the fixture writes one
    directly with a non-null completed_at (required by the trends query).
    """
    import asyncio
    from datetime import datetime

    from app.core.database import AsyncSessionLocal
    from app.models.database import AnalysisStatus, Simulation

    async def _insert():
        async with AsyncSessionLocal() as db:
            sim = Simulation(
                project_id=project_id,
                simulator="verilator",
                status=AnalysisStatus.COMPLETED,
                coverage_path="coverage.dat",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            db.add(sim)
            await db.commit()
            return str(sim.id)

    return asyncio.get_event_loop().run_until_complete(_insert())