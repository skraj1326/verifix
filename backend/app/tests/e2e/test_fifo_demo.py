"""End-to-End Test for FIFO Verification Demo.

This test validates the complete verification flow:
1. RTL Analysis
2. Verification Plan Generation
3. Assertion Generation
4. Test Generation
5. Coverage Analysis
"""

import pytest
import asyncio
from pathlib import Path

from app.engines.rtl_parser.parser import RTLParser
from app.engines.knowledge_graph.builder import KnowledgeGraphBuilder
from app.engines.verification_planner.planner import VerificationPlanGenerator
from app.engines.assertion_generator.generator import AssertionGenerator
from app.engines.test_generator.generator import TestGenerator
from app.engines.coverage_engine.analyzer import CoverageAnalyzer


# Load FIFO RTL
FIFO_RTL_PATH = Path(__file__).parent.parent.parent.parent.parent / "examples" / "fifo" / "fifo.sv"


def load_fifo_rtl() -> str:
    """Load FIFO RTL from file."""
    if FIFO_RTL_PATH.exists():
        return FIFO_RTL_PATH.read_text()
    # Fallback to embedded RTL
    return """
module fifo_sync #(
    parameter int DEPTH = 16,
    parameter int DATA_WIDTH = 32
) (
    input  logic                  clk,
    input  logic                  reset,
    input  logic                  wr_en,
    input  logic                  rd_en,
    input  logic [DATA_WIDTH-1:0] din,
    output logic [DATA_WIDTH-1:0] dout,
    output logic                  full,
    output logic                  empty,
    output logic [$clog2(DEPTH):0] count
);

    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [$clog2(DEPTH):0] wr_ptr, rd_ptr;
    logic [$clog2(DEPTH):0] wr_ptr_next, rd_ptr_next;
    logic [$clog2(DEPTH):0] count_next;
    logic full_next, empty_next;

    assign wr_ptr_next = wr_ptr + (wr_en && !full);
    assign rd_ptr_next = rd_ptr + (rd_en && !empty);
    assign count_next  = wr_ptr_next - rd_ptr_next;
    assign full_next   = (count_next == DEPTH);
    assign empty_next  = (count_next == 0);

    always_ff @(posedge clk) begin
        if (wr_en && !full) begin
            mem[wr_ptr[$clog2(DEPTH)-1:0]] <= din;
        end
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            dout <= '0;
        end else if (rd_en && !empty) begin
            dout <= mem[rd_ptr[$clog2(DEPTH)-1:0]];
        end
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            wr_ptr  <= '0;
            rd_ptr  <= '0;
            count   <= '0;
            full    <= 1'b0;
            empty   <= 1'b1;
        end else begin
            wr_ptr  <= wr_ptr_next;
            rd_ptr  <= rd_ptr_next;
            count   <= count_next;
            full    <= full_next;
            empty   <= empty_next;
        end
    end

    property p_reset;
        @(posedge clk) reset |-> ##1 (!full && empty && count == 0 && wr_ptr == 0 && rd_ptr == 0);
    endproperty
    a_reset: assert property (p_reset);

    property p_no_write_when_full;
        @(posedge clk) disable iff (reset) full |-> !wr_en;
    endproperty
    a_no_write_when_full: assert property (p_no_write_when_full);

    property p_no_read_when_empty;
        @(posedge clk) disable iff (reset) empty |-> !rd_en;
    endproperty
    a_no_read_when_empty: assert property (p_no_read_when_empty);

    property p_wr_ptr_increments;
        @(posedge clk) disable iff (reset) (wr_en && !full) |=> (wr_ptr == $past(wr_ptr) + 1);
    endproperty
    a_wr_ptr_increments: assert property (p_wr_ptr_increments);

    property p_rd_ptr_increments;
        @(posedge clk) disable iff (reset) (rd_en && !empty) |=> (rd_ptr == $past(rd_ptr) + 1);
    endproperty
    a_rd_ptr_increments: assert property (p_rd_ptr_increments);

    property p_count_tracking;
        @(posedge clk) disable iff (reset) count == wr_ptr - rd_ptr;
    endproperty
    a_count_tracking: assert property (p_count_tracking);

    property p_full_empty_mutex;
        @(posedge clk) disable iff (reset) !(full && empty) || (DEPTH == 1);
    endproperty
    a_full_empty_mutex: assert property (p_full_empty_mutex);

    property p_cover_full;
        @(posedge clk) disable iff (reset) full;
    endproperty
    c_full: cover property (p_cover_full);

    property p_cover_empty;
        @(posedge clk) disable iff (reset) empty;
    endproperty
    c_empty: cover property (p_cover_empty);

    property p_cover_simultaneous_rw;
        @(posedge clk) disable iff (reset) wr_en && rd_en && !full && !empty;
    endproperty
    c_simultaneous_rw: cover property (p_cover_simultaneous_rw);

    property p_cover_wr_at_full;
        @(posedge clk) disable iff (reset) full && wr_en;
    endproperty
    c_wr_at_full: cover property (p_cover_wr_at_full);

    property p_cover_rd_at_empty;
        @(posedge clk) disable iff (reset) empty && rd_en;
    endproperty
    c_rd_at_empty: cover property (p_cover_rd_at_empty);

endmodule
"""


class TestFIFOVerificationFlow:
    """Test the complete FIFO verification flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rtl_content = load_fifo_rtl()
        self.parser = RTLParser()
        self.modules = self.parser.parse(self.rtl_content, "fifo.sv")

    def test_rtl_parsing(self):
        """Test that RTL is parsed correctly."""
        assert len(self.modules) == 1
        module = self.modules[0]
        assert module.name == "fifo_sync"
        assert module.module_type.value == "module"
        
        # Check ports
        port_names = [p.name for p in module.ports]
        assert "clk" in port_names
        assert "reset" in port_names
        assert "wr_en" in port_names
        assert "rd_en" in port_names
        assert "din" in port_names
        assert "dout" in port_names
        assert "full" in port_names
        assert "empty" in port_names
        assert "count" in port_names

        # Check parameters
        param_names = [p.name for p in module.parameters]
        assert "DEPTH" in param_names
        assert "DATA_WIDTH" in param_names

        # Check signals
        signal_names = [s.name for s in module.signals]
        assert "mem" in signal_names
        assert "wr_ptr" in signal_names
        assert "rd_ptr" in signal_names

        # Check assertions
        assert len(module.assertions) >= 7  # At least 7 assertions in FIFO

    def test_knowledge_graph(self):
        """Test knowledge graph construction."""
        kg_builder = KnowledgeGraphBuilder()
        graph = kg_builder.build(self.modules)

        assert len(graph["nodes"]) > 0
        assert len(graph["edges"]) > 0
        
        # Check for module node
        module_nodes = [n for n in graph["nodes"] if n["type"] == "module"]
        assert len(module_nodes) == 1
        assert module_nodes[0]["label"] == "fifo_sync"

        # Check for FIFO detection in metadata
        module_props = module_nodes[0]["properties"]
        assert module_props["metadata"].get("is_fifo") is True

        # Check recommendations
        recommendations = kg_builder.get_modules_needing_verification()
        assert len(recommendations) > 0
        fifo_rec = next((r for r in recommendations if r["module"] == "fifo_sync"), None)
        assert fifo_rec is not None
        assert fifo_rec["complexity_score"] > 0

    def test_verification_plan_generation(self):
        """Test verification plan generation."""
        planner = VerificationPlanGenerator()
        plan = planner.generate(self.modules, "Parameterized synchronous FIFO with full/empty flags.")

        assert "items" in plan
        assert "summary" in plan
        assert "traceability" in plan
        
        items = plan["items"]
        assert len(items) > 0

        # Check for key verification categories
        categories = {item["category"] for item in items}
        assert "functional" in categories
        assert "protocol" in categories
        assert "fsm" in categories or "corner_case" in categories
        assert "coverage" in categories

        # Check for FIFO-specific items
        fifo_items = [i for i in items if "fifo" in i["id"].lower()]
        assert len(fifo_items) > 0

        # Check summary
        summary = plan["summary"]
        assert summary["total_items"] > 0
        assert summary["modules_analyzed"] == 1

        # Check traceability
        traceability = plan["traceability"]
        assert "module_to_items" in traceability
        assert "fifo_sync" in traceability["module_to_items"]

    def test_assertion_generation(self):
        """Test SVA assertion generation."""
        generator = AssertionGenerator()
        assertions = generator.generate(self.modules)

        assert len(assertions) > 0
        
        # Check for key assertion types
        assertion_names = [a["name"] for a in assertions]
        
        # Should have reset assertions
        reset_assertions = [a for a in assertions if "reset" in a["name"].lower()]
        assert len(reset_assertions) > 0

        # Should have FIFO assertions
        fifo_assertions = [a for a in assertions if "fifo" in a["name"].lower() or "full" in a["name"].lower() or "empty" in a["name"].lower()]
        assert len(fifo_assertions) > 0

        # Check assertion structure
        for assertion in assertions:
            assert "name" in assertion
            assert "assertion_code" in assertion
            assert "explanation" in assertion
            assert "signals_used" in assertion
            assert "confidence" in assertion
            assert "source_evidence" in assertion
            assert "false_positive_conditions" in assertion

    def test_test_generation(self):
        """Test directed and random test generation."""
        generator = TestGenerator()
        tests = generator.generate(self.modules)

        assert len(tests) > 0

        # Check test types
        test_types = {t["test_type"] for t in tests}
        assert "directed" in test_types
        assert "constrained_random" in test_types
        assert "uvm_sequence_item" in test_types
        assert "uvm_sequence" in test_types
        assert "uvm_monitor" in test_types

        # Check for FIFO-specific tests
        fifo_tests = [t for t in tests if "fifo" in t["name"].lower()]
        assert len(fifo_tests) > 0

        # Check test structure
        for test in tests:
            assert "name" in test
            assert "test_type" in test
            assert "code" in test
            assert "verification_objective" in test
            assert "target_coverage" in test
            assert "target_signals" in test

    def test_coverage_analysis(self):
        """Test coverage analysis with mock data."""
        analyzer = CoverageAnalyzer()

        # Mock Verilator coverage output
        mock_coverage = """
Lines 145/150 (96.67%)
Branches 42/50 (84.00%)
Toggles 200/250 (80.00%)
"""

        coverage = analyzer.parse_verilator_coverage(mock_coverage)
        
        assert coverage["line"].overall == 96.67
        assert coverage["branch"].overall == 84.00
        assert coverage["toggle"].overall == 80.00

        # Test gap identification
        gaps = analyzer.identify_gaps(coverage, self.rtl_content, "fifo_sync")
        
        # Should identify gaps for branch and toggle coverage
        assert len(gaps) > 0
        
        gap_types = {g["gap_type"] for g in gaps}
        assert "reachable_untested" in gap_types

    def test_coverage_targeted_tests(self):
        """Test generation of tests targeting coverage gaps."""
        generator = TestGenerator()
        analyzer = CoverageAnalyzer()

        # Create mock gaps
        mock_gaps = [
            {
                "gap_type": "reachable_untested",
                "coverage_type": "branch",
                "description": "Uncovered branch in reset logic",
                "rtl_location": {"module": "fifo_sync", "line": 62},
                "conditions": ["reset", "full"],
                "suggested_test": "Test reset with full flag asserted",
            }
        ]

        tests = generator.generate(self.modules, mock_gaps)
        
        # Should generate coverage-targeted tests
        targeted_tests = [t for t in tests if t["test_type"] == "coverage_targeted"]
        assert len(targeted_tests) > 0

    def test_full_verification_flow_integration(self):
        """Integration test for the complete flow."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        
        # Run complete flow
        result = service.full_verification_flow(
            self.rtl_content,
            "Parameterized synchronous FIFO with full/empty flags, occupancy counter, and built-in assertions."
        )

        assert "analysis" in result
        assert "plan" in result
        assert "assertions" in result
        assert "tests" in result

        # Check analysis
        analysis = result["analysis"]
        assert "summary" in analysis
        assert "recommendations" in analysis

        # Check plan
        plan = result["plan"]
        assert plan["summary"]["total_items"] > 0
        assert len(plan["items_preview"]) > 0

        # Check assertions
        assertions = result["assertions"]
        assert assertions["total"] > 0
        assert len(assertions["preview"]) > 0

        # Check tests
        tests = result["tests"]
        assert tests["total"] > 0
        assert "directed" in tests["types"]
        assert "constrained_random" in tests["types"]

    def test_design_summary(self):
        """Test design summary generation."""
        summary = self.parser.get_design_summary()
        
        assert summary["num_modules"] == 1
        assert "fifo_sync" in summary["module_names"]
        assert summary["total_ports"] >= 9
        assert summary["total_fsm_count"] >= 0  # FIFO may not have explicit FSM
        assert summary["total_assertions"] >= 7
        assert summary["total_module_instances"] >= 0

    def test_corner_case_detection(self):
        """Test that corner cases are detected."""
        fifo_module = self.modules[0]
        corner_cases = fifo_module.metadata.get("corner_cases", [])
        
        assert len(corner_cases) > 0
        
        # Check for FIFO corner cases
        fifo_corner = next((cc for cc in corner_cases if cc["type"] == "fifo"), None)
        assert fifo_corner is not None
        assert len(fifo_corner["cases"]) > 0
        
        # Check for reset corner cases
        reset_corner = next((cc for cc in corner_cases if cc["type"] == "general"), None)
        assert reset_corner is not None


class TestVerificationServiceIntegration:
    """Test the verification service integration."""

    def setup_method(self):
        self.rtl_content = load_fifo_rtl()

    def test_service_initialization(self):
        """Test that all engines initialize correctly."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        
        assert service.parser is not None
        assert service.knowledge_graph is not None
        assert service.planner is not None
        assert service.assertion_gen is not None
        assert service.test_gen is not None
        assert service.coverage is not None
        assert service.logs is not None
        assert service.root_cause is not None
        assert service.regression is not None
        assert service.waveform is not None

    def test_analyze_rtl(self):
        """Test RTL analysis service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        result = service.analyze_rtl(self.rtl_content, "fifo.sv")
        
        assert "modules" in result
        assert "summary" in result
        assert "knowledge_graph" in result
        assert "recommendations" in result
        
        assert len(result["modules"]) == 1
        assert result["modules"][0].name == "fifo_sync"

    def test_generate_plan(self):
        """Test plan generation service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        result = service.generate_plan(self.rtl_content, "FIFO specification")
        
        assert "items" in result
        assert "summary" in result
        assert "traceability" in result

    def test_generate_assertions(self):
        """Test assertion generation service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        result = service.generate_assertions(self.rtl_content)
        
        assert "assertions" in result
        assert "total" in result
        assert "modules" in result
        assert result["total"] > 0

    def test_generate_tests(self):
        """Test test generation service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        result = service.generate_tests(self.rtl_content)
        
        assert "tests" in result
        assert "total" in result
        assert result["total"] > 0

    def test_analyze_coverage(self):
        """Test coverage analysis service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        mock_report = "Lines 145/150 (96.67%)\nBranches 42/50 (84.00%)"
        
        result = service.analyze_coverage(mock_report, self.rtl_content, "fifo_sync")
        
        assert "coverage" in result
        assert "gaps" in result
        assert "report" in result

    def test_analyze_log(self):
        """Test log analysis service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        mock_log = """
Error: Assertion a_no_write_when_full failed at line 89
Fatal: Simulation terminated due to assertion failure
"""
        
        result = service.analyze_log(mock_log)
        
        assert "total_lines" in result
        assert "total_errors" in result
        assert "first_failure" in result
        assert "root_cause_analysis" in result

    def test_waveform_analysis(self):
        """Test waveform analysis service."""
        from app.services.verification_service import VerificationService
        
        service = VerificationService()
        mock_vcd = """
$date
  Test
$end
$version
  Verilator
$end
$timescale
  1ns
$end
$scope module fifo_sync $end
$var wire 1 ! clk $end
$var wire 1 " reset $end
$var wire 1 # wr_en $end
$var wire 1 $ rd_en $end
$var wire 32 % din $end
$var wire 32 & dout $end
$var wire 1 ' full $end
$var wire 1 ( empty $end
$upscope $end
$enddefinitions $end
#0
$dumpvars
0!
0"
0#
0$
0%
0&
0'
0(
$end
#10
1!
$end
"""
        
        result = service.analyze_waveform_vcd(mock_vcd)
        
        assert "signals" in result
        assert "time_range" in result
        assert "transitions" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])