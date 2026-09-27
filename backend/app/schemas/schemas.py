"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TestType(str, Enum):
    DIRECTED = "directed"
    CONSTRAINED_RANDOM = "constrained_random"
    UVM_SEQUENCE = "uvm_sequence"
    UVM_TEST = "uvm_test"
    COVERAGE_TARGETED = "coverage_targeted"


class SourceType(str, Enum):
    RTL_DERIVED = "rtl-derived"
    SPEC_DERIVED = "spec-derived"
    AI_INFERRED = "ai-inferred"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ─── Project Schemas ──────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    created_at: str


class ProjectList(BaseModel):
    projects: list[ProjectResponse]
    total: int


# ─── RTL Analysis Schemas ─────────────────────────────────────────────

class RTLAnalysisRequest(BaseModel):
    content: str = Field(..., min_length=1)
    filename: str = "design.sv"


class PortInfo(BaseModel):
    name: str
    direction: str
    width: str = ""
    line: int = 0


class SignalInfo(BaseModel):
    name: str
    type: str
    width: str = ""


class FSMStateInfo(BaseModel):
    name: str


class FSMTransitionInfo(BaseModel):
    from_state: str
    to_state: str
    condition: str = ""


class FSMInfo(BaseModel):
    name: str
    state_variable: str
    states: list[FSMStateInfo]
    transitions: list[FSMTransitionInfo]


class ModuleInfo(BaseModel):
    name: str
    module_type: str
    is_top: bool = False
    start_line: int = 0
    end_line: int = 0
    ports: list[PortInfo] = []
    signals: list[SignalInfo] = []
    parameters: list[dict] = []
    fsm_info: list[FSMInfo] = []
    instances: list[dict] = []
    always_blocks: list[dict] = []
    assertions: list[dict] = []
    metadata: dict = {}


class DesignSummary(BaseModel):
    num_modules: int
    module_names: list[str]
    total_ports: int
    total_internal_signals: int
    total_fsm_count: int
    total_assertions: int
    total_module_instances: int
    clock_signals: list[str] = []
    reset_signals: list[str] = []
    protocols_detected: list[str] = []
    modules_with_fsm: list[str] = []
    modules_with_assertions: list[str] = []


class KnowledgeGraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    node_type_counts: dict = {}
    edge_type_counts: dict = {}


class VerificationRecommendation(BaseModel):
    module: str
    complexity_score: int
    reasons: list[str]


class RTLAnalysisResponse(BaseModel):
    filename: str
    modules: list[ModuleInfo]
    summary: DesignSummary
    knowledge_graph: dict
    recommendations: list[VerificationRecommendation]


# ─── Verification Plan Schemas ────────────────────────────────────────

class VerificationPlanRequest(BaseModel):
    rtl_content: str = Field(..., min_length=1)
    specification: Optional[str] = ""


class VerificationItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    source_type: str
    source_reference: dict = {}
    priority: int = 5
    status: str = "pending"
    coverage_points: list[str] = []


class VerificationPlanSummary(BaseModel):
    total_items: int
    categories: dict = {}
    source_breakdown: dict = {}
    modules_analyzed: int = 0
    total_fsm: int = 0
    total_assertions: int = 0


class VerificationPlanResponse(BaseModel):
    plan: dict
    summary: VerificationPlanSummary
    traceability: dict
    modules_analyzed: list[str]


# ─── Assertion Schemas ────────────────────────────────────────────────

class AssertionGenRequest(BaseModel):
    rtl_content: str = Field(..., min_length=1)


class GeneratedAssertion(BaseModel):
    name: str
    assertion_code: str
    explanation: str = ""
    signals_used: list[str] = []
    confidence: str = "medium"
    source_evidence: str = ""
    false_positive_conditions: str = ""


class AssertionGenResponse(BaseModel):
    assertions: list[GeneratedAssertion]
    total_generated: int
    modules_analyzed: list[str]


# ─── Test Schemas ─────────────────────────────────────────────────────

class TestGenRequest(BaseModel):
    rtl_content: str = Field(..., min_length=1)
    coverage_gaps: Optional[list[dict]] = None
    test_types: list[str] = ["directed", "constrained_random"]


class GeneratedTest(BaseModel):
    name: str
    test_type: str
    code: str
    verification_objective: str = ""
    target_coverage: list[str] = []
    target_signals: list[str] = []


class TestGenResponse(BaseModel):
    tests: list[GeneratedTest]
    total_generated: int
    test_types: dict = {}
    modules_analyzed: list[str]


# ─── Simulation Schemas ───────────────────────────────────────────────

class CompileRequest(BaseModel):
    rtl_files: list[str]
    testbench: str
    top_module: str
    simulator: str = "verilator"
    timeout: int = 300


class CompileResponse(BaseModel):
    success: bool
    exit_code: int
    compilation_log: str = ""
    error_message: str = ""
    runtime_seconds: float = 0.0


class LogAnalysisRequest(BaseModel):
    log_content: str = Field(..., min_length=1)
    log_type: str = "simulation"


class LogAnalysisResponse(BaseModel):
    log_type: str
    total_lines: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    first_failure: dict = {}
    failure_clusters: list = []
    root_cause_analysis: dict = {}


# ─── Coverage Schemas ─────────────────────────────────────────────────

class CoverageAnalysisRequest(BaseModel):
    coverage_report: str = Field(..., min_length=1)
    rtl_content: Optional[str] = ""
    module_name: Optional[str] = ""


class CoverageData(BaseModel):
    coverage: float = 0.0
    covered: int = 0
    total: int = 0


class CoverageGap(BaseModel):
    gap_type: str
    coverage_type: str
    description: str
    rtl_location: dict = {}
    suggested_test: str = ""


class CoverageReport(BaseModel):
    module: str = ""
    overall_coverage: float = 0.0
    coverage_by_type: dict = {}
    total_gaps: int = 0
    gap_summary: dict = {}
    high_priority_gaps: list = []
    closure_estimate: dict = {}


class CoverageAnalysisResponse(BaseModel):
    report: CoverageReport
    coverage: dict = {}
    gaps: list[CoverageGap] = []


class CoverageComparisonRequest(BaseModel):
    coverage_before: dict
    coverage_after: dict


class CoverageComparisonResponse(BaseModel):
    comparison: dict
    overall_improved: bool
    total_delta: float


# ─── Failure Analysis Schemas ─────────────────────────────────────────

class FailureAnalysisRequest(BaseModel):
    failure_info: dict
    rtl_content: Optional[str] = ""
    log_analysis: Optional[dict] = None


class FailureFact(BaseModel):
    fact: str
    source: str = ""
    confidence: str = "observed"


class FailureHypothesis(BaseModel):
    hypothesis: str
    confidence: str = "low"
    evidence: list[str] = []
    suggested_investigation: list[str] = []
    potential_fix: str = ""


class FailureAnalysisResponse(BaseModel):
    failure_summary: str
    facts: list[FailureFact]
    relevant_signals: list[dict]
    rtl_context: dict
    hypotheses: list[FailureHypothesis]
    suggested_investigation: list[str]
    confidence: str
    separation_of_concerns: dict


# ─── WebSocket Schemas ────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # "status", "progress", "result", "error"
    data: dict = {}
    task_id: Optional[str] = None
