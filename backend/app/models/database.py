"""Database models for AstrixCore Verification AI."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class ProjectStatus(str, PyEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AnalysisStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, PyEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ConfidenceLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TestStatus(str, PyEnum):
    GENERATED = "generated"
    COMPILED = "compiled"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


# ─── Project ──────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSONB, default=dict)

    designs = relationship("Design", back_populates="project", cascade="all, delete-orphan")
    verification_plans = relationship("VerificationPlan", back_populates="project", cascade="all, delete-orphan")
    tests = relationship("Test", back_populates="project", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="project", cascade="all, delete-orphan")


# ─── Design (RTL) ─────────────────────────────────────────────────────

class Design(Base):
    __tablename__ = "designs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    language = Column(String(50), default="SystemVerilog")
    file_path = Column(String(1024))
    raw_content = Column(Text)
    analysis_status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="designs")
    modules = relationship("DesignModule", back_populates="design", cascade="all, delete-orphan")
    knowledge_graph = relationship("KnowledgeGraph", uselist=False, back_populates="design", cascade="all, delete-orphan")


class DesignModule(Base):
    __tablename__ = "design_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    module_type = Column(String(50), default="module")  # module, interface, package, program
    is_top = Column(Boolean, default=False)
    start_line = Column(Integer)
    end_line = Column(Integer)
    parameters = Column(JSONB, default=list)
    ports = Column(JSONB, default=list)
    signals = Column(JSONB, default=list)
    fsm_states = Column(JSONB, default=list)
    fsm_transitions = Column(JSONB, default=list)
    instances = Column(JSONB, default=list)
    always_blocks = Column(JSONB, default=list)
    assign_statements = Column(JSONB, default=list)
    assertions = Column(JSONB, default=list)
    functions = Column(JSONB, default=list)
    tasks = Column(JSONB, default=list)
    extra_metadata = Column("metadata", JSONB, default=dict)

    design = relationship("Design", back_populates="modules")
    __table_args__ = (
        Index("idx_module_design", "design_id"),
        Index("idx_module_name", "name"),
    )


# ─── Knowledge Graph ──────────────────────────────────────────────────

class KnowledgeGraph(Base):
    __tablename__ = "knowledge_graphs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    nodes = Column(JSONB, default=list)  # [{id, type, label, properties}]
    edges = Column(JSONB, default=list)  # [{source, target, type, properties}]
    created_at = Column(DateTime, default=datetime.utcnow)

    design = relationship("Design", back_populates="knowledge_graph")


# ─── Verification Plan ────────────────────────────────────────────────

class VerificationPlan(Base):
    __tablename__ = "verification_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), default="Auto-generated Plan")
    items = Column(JSONB, default=list)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="verification_plans")


class VerificationItem(Base):
    __tablename__ = "verification_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("verification_plans.id"), nullable=False)
    category = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    source_type = Column(String(50))  # rtl-derived, spec-derived, ai-inferred
    source_reference = Column(JSONB, default=dict)
    priority = Column(Integer, default=5)
    status = Column(String(50), default="pending")
    coverage_points = Column(JSONB, default=list)
    related_assertions = Column(JSONB, default=list)
    related_tests = Column(JSONB, default=list)


# ─── Assertions ───────────────────────────────────────────────────────

class Assertion(Base):
    __tablename__ = "assertions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    assertion_code = Column(Text, nullable=False)
    assertion_type = Column(String(50))  # immediate, concurrent, cover, assume
    explanation = Column(Text, default="")
    signals_used = Column(ARRAY(String), default=list)
    confidence = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.MEDIUM)
    source_evidence = Column(Text, default="")
    false_positive_conditions = Column(Text, default="")
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_assertion_design", "design_id"),
    )


# ─── Tests ────────────────────────────────────────────────────────────

class Test(Base):
    __tablename__ = "tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    test_type = Column(String(50))  # directed, constrained_random, uvm_sequence, uvm_test
    test_code = Column(Text, nullable=False)
    verification_objective = Column(Text, default="")
    target_coverage = Column(JSONB, default=list)
    target_signals = Column(ARRAY(String), default=list)
    status = Column(Enum(TestStatus), default=TestStatus.GENERATED)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="tests")
    simulation_results = relationship("SimulationResult", back_populates="test")
    __table_args__ = (
        Index("idx_test_project", "project_id"),
    )


# ─── Simulation ───────────────────────────────────────────────────────

class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    simulator = Column(String(50), default="verilator")
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    log_path = Column(String(1024))
    coverage_path = Column(String(1024))
    waveform_path = Column(String(1024))
    compilation_log = Column(Text)
    simulation_log = Column(Text)
    extra_metadata = Column("metadata", JSONB, default=dict)

    project = relationship("Project", back_populates="simulations")
    results = relationship("SimulationResult", back_populates="simulation", cascade="all, delete-orphan")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    test_id = Column(UUID(as_uuid=True), ForeignKey("tests.id"), nullable=True)
    test_name = Column(String(255))
    status = Column(Enum(TestStatus), default=TestStatus.GENERATED)
    assertion_failures = Column(JSONB, default=list)
    errors = Column(JSONB, default=list)
    warnings = Column(JSONB, default=list)
    runtime_seconds = Column(Float)
    exit_code = Column(Integer)

    simulation = relationship("Simulation", back_populates="results")
    test = relationship("Test", back_populates="simulation_results")


# ─── Coverage ─────────────────────────────────────────────────────────

class CoverageReport(Base):
    __tablename__ = "coverage_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    report_type = Column(String(50))  # line, branch, toggle, fsm, functional, assertion
    overall_coverage = Column(Float, default=0.0)
    details = Column(JSONB, default=dict)
    gaps = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class CoverageGap(Base):
    __tablename__ = "coverage_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("coverage_reports.id"), nullable=False)
    gap_type = Column(String(50))  # uncovered, reachable_untested, potentially_unreachable
    description = Column(Text)
    rtl_location = Column(JSONB, default=dict)
    conditions = Column(JSONB, default=list)
    suggested_test = Column(Text)
    severity = Column(Enum(SeverityLevel), default=SeverityLevel.WARNING)
    is_addressed = Column(Boolean, default=False)
    addressed_by_test_id = Column(UUID(as_uuid=True), nullable=True)


# ─── Failure Analysis ─────────────────────────────────────────────────

class FailureAnalysis(Base):
    __tablename__ = "failure_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    failure_type = Column(String(100))
    summary = Column(Text)
    first_failing_signal = Column(String(255))
    affected_module = Column(String(255))
    relevant_rtl_lines = Column(JSONB, default=list)
    relevant_signals = Column(ARRAY(String), default=list)
    root_cause_hypothesis = Column(Text)
    confidence = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.LOW)
    evidence = Column(JSONB, default=list)
    suggested_investigation = Column(Text)
    potential_fix = Column(Text)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Audit Log ────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSONB, default=dict)
    user_id = Column(String(255))
    ip_address = Column(String(45))

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_action", "action"),
    )


# ─── Subscription / Billing ───────────────────────────────────────────

class SubscriptionTier(str, PyEnum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"
    UNPAID = "unpaid"


class BillingInterval(str, PyEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    tier = Column(Enum(SubscriptionTier), nullable=False)
    description = Column(Text, default="")
    price_monthly = Column(Integer, default=0)  # in cents
    price_yearly = Column(Integer, default=0)  # in cents
    features = Column(JSONB, default=list)  # List of feature strings
    limits = Column(JSONB, default=dict)  # {projects, simulations, storage_gb, team_members, api_calls}
    is_active = Column(Boolean, default=True)
    stripe_price_id_monthly = Column(String(100))
    stripe_price_id_yearly = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="plan")

    __table_args__ = (
        Index("idx_plan_tier", "tier"),
        Index("idx_plan_active", "is_active"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE)
    billing_interval = Column(Enum(BillingInterval), default=BillingInterval.MONTHLY)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime)
    stripe_customer_id = Column(String(100))
    stripe_subscription_id = Column(String(100))
    stripe_price_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", backref="subscription")
    plan = relationship("Plan", back_populates="subscriptions")

    __table_args__ = (
        Index("idx_subscription_status", "status"),
        Index("idx_subscription_stripe", "stripe_subscription_id"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    stripe_invoice_id = Column(String(100), unique=True)
    amount_due = Column(Integer, default=0)  # in cents
    amount_paid = Column(Integer, default=0)
    amount_remaining = Column(Integer, default=0)
    currency = Column(String(3), default="usd")
    status = Column(String(50))  # draft, open, paid, void, uncollectible
    invoice_pdf = Column(String(500))
    hosted_invoice_url = Column(String(500))
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_invoice_subscription", "subscription_id"),
        Index("idx_invoice_stripe", "stripe_invoice_id"),
        Index("idx_invoice_status", "status"),
    )


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(100), nullable=False)  # Stripe customer ID
    stripe_payment_method_id = Column(String(100), unique=True)
    type = Column(String(50))  # card, bank_transfer, etc.
    card_brand = Column(String(50))
    card_last4 = Column(String(4))
    card_exp_month = Column(Integer)
    card_exp_year = Column(Integer)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_payment_method_customer", "customer_id"),
    )


# ─── Reports ──────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=True)
    title = Column(String(500), nullable=False)
    format = Column(String(20), default="html")  # html, json, pdf
    template = Column(String(100), default="standard")
    sections = Column(JSONB, default=list)  # [{id, title, content, order, type}]
    report_metadata = Column("metadata", JSONB, default=dict)  # evidence_policy, coverage_target, etc.
    generated_by = Column(String(255))  # user or system identifier
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
    simulation = relationship("Simulation")

    __table_args__ = (
        Index("idx_report_project", "project_id"),
        Index("idx_report_created", "created_at"),
    )
