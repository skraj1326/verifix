"""API-level tests that do not require a database.

These exercise the real FastAPI application: route registration, OpenAPI
generation, the in-memory waveform pipeline end-to-end, RTL analysis without
persistence, and the pure report/diagram section builders.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import rtl_hierarchy
from app.api.v1.reports import (
    generate_coverage_section,
    generate_conclusions,
    generate_executive_summary,
    generate_traceability_matrix,
    generate_verification_plan_section,
    render_html_document,
)
from app.main import app

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

SAMPLE_VCD = """$date today $end
$version verifiX $end
$timescale 1ns $end
$scope module fifo_sync $end
$var wire 1 ! clk $end
$var wire 1 " rst_n $end
$var wire 1 # full $end
$var wire 1 $ empty $end
$var reg 4 % count $end
$upscope $end
$enddefinitions $end
#0
0!
0"
b0 %
#10
1!
b1 %
#20
1"
b11 %
#30
b0 %
#40
0!
b00 %
"""


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_waveform_store():
    from app.api.v1.waveform import waveform_store

    waveform_store.clear()
    yield
    waveform_store.clear()


class TestApplicationBoot:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_lists_waveform_endpoint(self, client):
        payload = client.get("/").json()
        assert "waveform" in payload["endpoints"]

    def test_openapi_schema_generates(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "/api/v1/waveform/upload" in response.json()["paths"]

    def test_no_duplicate_coverage_compare_route(self, client):
        paths = client.get("/openapi.json").json()["paths"]
        assert list(paths["/api/v1/coverage/compare"].keys()) == ["post"]

    def test_sqlalchemy_models_are_importable(self):
        """`metadata` is reserved by SQLAlchemy and must not be a mapped attribute."""
        from sqlalchemy import MetaData

        from app.models.database import DesignModule, Simulation

        # The declarative MetaData must remain reachable under its reserved name.
        assert isinstance(DesignModule.metadata, MetaData)
        assert isinstance(Simulation.metadata, MetaData)
        # The JSON payload column is exposed as extra_metadata, keeping the
        # on-disk column name unchanged.
        assert "extra_metadata" in DesignModule.__mapper__.attrs.keys()
        assert "extra_metadata" in Simulation.__mapper__.attrs.keys()


class TestWaveformPipeline:
    def test_upload_parses_vcd(self, client):
        response = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["format"] == "VCD"
        assert body["signals_count"] == 5
        assert body["time_range"]["max"] == 40

    def test_upload_then_fetch_analysis(self, client):
        upload = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()
        waveform_id = upload["waveform_id"]

        analysis = client.get(f"/api/v1/waveform/{waveform_id}")
        assert analysis.status_code == 200
        data = analysis.json()
        assert data["total_signals"] == 5
        names = {s["name"] for s in data["signals"]}
        assert {"clk", "rst_n", "full", "empty", "count"} == names

    def test_signal_transitions_are_ordered(self, client):
        upload = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()

        signal = client.get(
            f"/api/v1/waveform/{upload['waveform_id']}/signal/clk"
        ).json()
        assert [t["value"] for t in signal["transitions"]] == ["0", "1", "0"]
        assert [t["time"] for t in signal["transitions"]] == [0.0, 10.0, 40.0]

    def test_signal_listing_supports_wildcard_pattern(self, client):
        upload = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()

        matched = client.get(
            f"/api/v1/waveform/{upload['waveform_id']}/signals", params={"pattern": "*en*"}
        ).json()
        names = {s["name"] for s in matched}
        assert "full" not in names
        assert "rst_n" not in names

    def test_multibit_signal_statistics(self, client):
        upload = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()

        count = client.get(
            f"/api/v1/waveform/{upload['waveform_id']}/signal/count"
        ).json()
        assert count["width"] == 4
        assert count["min_value"] == "0"
        assert count["max_value"] == "3"

    def test_signal_context_around_failure_time(self, client):
        upload = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()

        context = client.post(
            f"/api/v1/waveform/{upload['waveform_id']}/signal-context",
            json={
                "waveform_id": upload["waveform_id"],
                "failure_time": 20,
                "window": 15,
            },
        )
        assert context.status_code == 200
        signals = context.json()["signals"]
        # rst_n is 1 at t=20 (asserted at t=20 after being 0 at t=0).
        assert signals["rst_n"]["value_at_failure"] == "1"
        assert signals["count"]["value_at_failure"] == "11"

    def test_identical_waveforms_compare_as_matching(self, client):
        first = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("a.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()
        second = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("b.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()

        result = client.post(
            "/api/v1/waveform/compare",
            json={"waveform_id_1": first["waveform_id"], "waveform_id_2": second["waveform_id"]},
        )
        assert result.status_code == 200
        body = result.json()
        assert set(body["matching_signals"]) == {"clk", "rst_n", "full", "empty", "count"}
        assert body["different_signals"] == []

    def test_changed_waveform_is_reported_as_different(self, client):
        first = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("a.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()
        modified = SAMPLE_VCD.replace("#10\n1!\nb1 %", "#10\n1!\nb10 %")
        second = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("b.vcd", io.BytesIO(modified.encode()), "text/plain")},
        ).json()

        body = client.post(
            "/api/v1/waveform/compare",
            json={"waveform_id_1": first["waveform_id"], "waveform_id_2": second["waveform_id"]},
        ).json()
        assert "count" in [d["signal"] for d in body["different_signals"]]

    def test_unknown_waveform_returns_404(self, client):
        assert client.get("/api/v1/waveform/wave_missing").status_code == 404

    def test_missing_signal_returns_404(self, client):
        upload = client.post(
            "/api/v1/waveform/upload",
            files={"file": ("dump.vcd", io.BytesIO(SAMPLE_VCD.encode()), "text/plain")},
        ).json()
        response = client.get(
            f"/api/v1/waveform/{upload['waveform_id']}/signal/does_not_exist"
        )
        assert response.status_code == 404


class TestRTLAnalysis:
    def test_analyze_parses_fifo(self, client):
        response = client.post(
            "/api/v1/rtl/analyze",
            json={"content": FIFO_SV, "filename": "fifo_sync.sv"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["num_modules"] == 1
        assert body["modules"][0]["name"] == "fifo_sync"

    def test_analyze_without_project_does_not_persist(self, client):
        body = client.post(
            "/api/v1/rtl/analyze",
            json={"content": FIFO_SV, "filename": "fifo_sync.sv"},
        ).json()
        assert body["persisted"] is False
        assert body["design_id"] is None

    def test_empty_rtl_is_rejected(self, client):
        response = client.post(
            "/api/v1/rtl/analyze", json={"content": "", "filename": "empty.sv"}
        )
        assert response.status_code == 400

    def test_recursive_instantiation_does_not_hang_diagram(self, client):
        """Cycle-safe hierarchy generation."""
        from app.engines.rtl_parser.parser import RTLParser

        recursive = """
        module leaf(input logic a, output logic b);
            assign b = a;
        endmodule

        module recursive_top(input logic a, output logic b);
            leaf inner (.a(a), .b(b));
            recursive_top self (.a(a), .b());
        endmodule
        """
        modules = RTLParser().parse(recursive, "recursive_top.sv")
        mermaid = rtl_hierarchy.generate_mermaid_diagram(modules)
        graphviz = rtl_hierarchy.generate_graphviz_diagram(modules)
        assert "graph TD" in mermaid
        assert "recursive_top" in mermaid
        assert graphviz.startswith("digraph hierarchy {")
        assert graphviz.rstrip().endswith("}")

    def test_mermaid_ids_are_unique_for_similar_names(self):
        class FakeModule:
            def __init__(self, name):
                self.name = name
                self.module_type = type("T", (), {"value": "module"})()
                self.instances = []

        modules = [FakeModule("a_b"), FakeModule("a__b"), FakeModule("a-b")]
        diagram = rtl_hierarchy.generate_mermaid_diagram(modules)
        ids = [line.strip().split(" ")[0] for line in diagram.splitlines() if "[" in line]
        assert len(ids) == len(set(ids)) == 3


class TestReportSectionsAreEvidenceDriven:
    def test_no_coverage_evidence_reports_unknown(self):
        html = generate_coverage_section([])
        assert "[UNKNOWN]" in html
        assert "No persisted coverage evidence" in html

    def test_coverage_section_uses_stored_values(self):
        html = generate_coverage_section(
            [
                {
                    "report_type": "line",
                    "overall_coverage": 87.5,
                    "details": {"covered": 70, "total": 80, "module": "fifo_sync"},
                    "gaps": [],
                }
            ]
        )
        assert "87.5%" in html
        assert "fifo_sync" in html
        assert "70" in html and "80" in html

    def test_coverage_section_never_invents_bins(self):
        html = generate_coverage_section(
            [
                {
                    "report_type": "line",
                    "overall_coverage": 50.0,
                    "details": {"covered": 5, "total": 10},
                    "gaps": [],
                }
            ]
        )
        assert "[UNKNOWN] No coverage gaps recorded." in html

    def test_missing_plan_is_unknown_not_fabricated(self):
        html = generate_verification_plan_section([])
        assert "[UNKNOWN]" in html
        assert "<tr>" not in html

    def test_plan_section_lists_persisted_plan(self):
        html = generate_verification_plan_section(
            [
                {
                    "name": "FIFO plan",
                    "status": "completed",
                    "item_count": 3,
                    "categories": ["functional"],
                }
            ]
        )
        assert "FIFO plan" in html
        assert "functional" in html

    def test_traceability_is_unknown_without_requirement_store(self):
        html = generate_traceability_matrix()
        assert "[UNKNOWN]" in html
        assert "REQ-001" not in html

    def test_executive_summary_has_no_fabricated_signoff(self):
        html = generate_executive_summary("proj", [], None, [], [])
        assert "[UNKNOWN]" in html
        assert "sign-off" in html.lower()
        # Hard-coded demo numbers from the previous implementation are gone.
        assert "92.5" not in html
        assert "fifo_cg" not in html

    def test_conclusions_do_not_claim_verification_met(self):
        html = generate_conclusions([], [], [])
        assert "does not assert sign-off" in html
        assert "successfully met" not in html

    def test_conclusions_recommend_running_tests_when_none_executed(self):
        html = generate_conclusions([], [{"status": "generated"}], [])
        assert "not executed" in html

    def test_html_escaping_prevents_markup_injection(self):
        html = generate_executive_summary(
            "<script>alert(1)</script>", [], None, [], []
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_html_document_produces_standalone_html(self):
        from app.api.v1.reports import ReportSection, VerificationReport
        from datetime import datetime

        report = VerificationReport(
            id="report_test",
            project_id="p1",
            title="Verification Report - demo",
            generated_at=datetime(2026, 1, 1, 12, 0, 0),
            format="html",
            sections=[
                ReportSection(
                    id="coverage",
                    title="Coverage Analysis",
                    content="<p>body</p>",
                    order=1,
                    type="chart",
                )
            ],
            metadata={"template": "standard"},
        )
        document = render_html_document(report)
        assert document.startswith("<!DOCTYPE html>")
        assert "Coverage Analysis" in document
        assert document.rstrip().endswith("</html>")