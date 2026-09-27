"""Initial migration for VerifiX AI database schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    project_status = sa.Enum('active', 'archived', name='project_status')
    analysis_status = sa.Enum('pending', 'running', 'completed', 'failed', name='analysis_status')
    severity_level = sa.Enum('info', 'warning', 'error', 'fatal', name='severity_level')
    confidence_level = sa.Enum('low', 'medium', 'high', 'very_high', name='confidence_level')
    test_status = sa.Enum('generated', 'compiled', 'passed', 'failed', 'error', name='test_status')

    project_status.create(op.get_bind(), checkfirst=True)
    analysis_status.create(op.get_bind(), checkfirst=True)
    severity_level.create(op.get_bind(), checkfirst=True)
    confidence_level.create(op.get_bind(), checkfirst=True)
    test_status.create(op.get_bind(), checkfirst=True)

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, default=''),
        sa.Column('status', project_status, default='active'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('settings', JSONB, default={}),
    )

    # Designs table
    op.create_table(
        'designs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('language', sa.String(50), default='SystemVerilog'),
        sa.Column('file_path', sa.String(1024)),
        sa.Column('raw_content', sa.Text),
        sa.Column('analysis_status', analysis_status, default='pending'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('idx_design_project', 'designs', ['project_id'])

    # Design Modules table
    op.create_table(
        'design_modules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', UUID(as_uuid=True), sa.ForeignKey('designs.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('module_type', sa.String(50), default='module'),
        sa.Column('is_top', sa.Boolean, default=False),
        sa.Column('start_line', sa.Integer),
        sa.Column('end_line', sa.Integer),
        sa.Column('parameters', JSONB, default=[]),
        sa.Column('ports', JSONB, default=[]),
        sa.Column('signals', JSONB, default=[]),
        sa.Column('fsm_states', JSONB, default=[]),
        sa.Column('fsm_transitions', JSONB, default=[]),
        sa.Column('instances', JSONB, default=[]),
        sa.Column('always_blocks', JSONB, default=[]),
        sa.Column('assign_statements', JSONB, default=[]),
        sa.Column('assertions', JSONB, default=[]),
        sa.Column('functions', JSONB, default=[]),
        sa.Column('tasks', JSONB, default=[]),
        sa.Column('metadata', JSONB, default={}),
    )
    op.create_index('idx_module_design', 'design_modules', ['design_id'])
    op.create_index('idx_module_name', 'design_modules', ['name'])

    # Knowledge Graphs table
    op.create_table(
        'knowledge_graphs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', UUID(as_uuid=True), sa.ForeignKey('designs.id'), nullable=False),
        sa.Column('nodes', JSONB, default=[]),
        sa.Column('edges', JSONB, default=[]),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Verification Plans table
    op.create_table(
        'verification_plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), default='Auto-generated Plan'),
        sa.Column('items', JSONB, default=[]),
        sa.Column('status', analysis_status, default='pending'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Verification Items table
    op.create_table(
        'verification_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', UUID(as_uuid=True), sa.ForeignKey('verification_plans.id'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, default=''),
        sa.Column('source_type', sa.String(50)),
        sa.Column('source_reference', JSONB, default={}),
        sa.Column('priority', sa.Integer, default=5),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('coverage_points', JSONB, default=[]),
        sa.Column('related_assertions', JSONB, default=[]),
        sa.Column('related_tests', JSONB, default=[]),
    )

    # Assertions table
    op.create_table(
        'assertions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', UUID(as_uuid=True), sa.ForeignKey('designs.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('assertion_code', sa.Text, nullable=False),
        sa.Column('assertion_type', sa.String(50)),
        sa.Column('explanation', sa.Text, default=''),
        sa.Column('signals_used', ARRAY(sa.String), default=[]),
        sa.Column('confidence', confidence_level, default='medium'),
        sa.Column('source_evidence', sa.Text, default=''),
        sa.Column('false_positive_conditions', sa.Text, default=''),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('idx_assertion_design', 'assertions', ['design_id'])

    # Tests table
    op.create_table(
        'tests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('design_id', UUID(as_uuid=True), sa.ForeignKey('designs.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('test_type', sa.String(50)),
        sa.Column('test_code', sa.Text, nullable=False),
        sa.Column('verification_objective', sa.Text, default=''),
        sa.Column('target_coverage', JSONB, default=[]),
        sa.Column('target_signals', ARRAY(sa.String), default=[]),
        sa.Column('status', test_status, default='generated'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('idx_test_project', 'tests', ['project_id'])

    # Simulations table
    op.create_table(
        'simulations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('simulator', sa.String(50), default='verilator'),
        sa.Column('status', analysis_status, default='pending'),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('log_path', sa.String(1024)),
        sa.Column('coverage_path', sa.String(1024)),
        sa.Column('waveform_path', sa.String(1024)),
        sa.Column('compilation_log', sa.Text),
        sa.Column('simulation_log', sa.Text),
        sa.Column('metadata', JSONB, default={}),
    )

    # Simulation Results table
    op.create_table(
        'simulation_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id'), nullable=False),
        sa.Column('test_id', UUID(as_uuid=True), sa.ForeignKey('tests.id'), nullable=True),
        sa.Column('test_name', sa.String(255)),
        sa.Column('status', test_status, default='generated'),
        sa.Column('assertion_failures', JSONB, default=[]),
        sa.Column('errors', JSONB, default=[]),
        sa.Column('warnings', JSONB, default=[]),
        sa.Column('runtime_seconds', sa.Float),
        sa.Column('exit_code', sa.Integer),
    )

    # Coverage Reports table
    op.create_table(
        'coverage_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id'), nullable=False),
        sa.Column('report_type', sa.String(50)),
        sa.Column('overall_coverage', sa.Float, default=0.0),
        sa.Column('details', JSONB, default={}),
        sa.Column('gaps', JSONB, default=[]),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Coverage Gaps table
    op.create_table(
        'coverage_gaps',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', UUID(as_uuid=True), sa.ForeignKey('coverage_reports.id'), nullable=False),
        sa.Column('gap_type', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('rtl_location', JSONB, default={}),
        sa.Column('conditions', JSONB, default=[]),
        sa.Column('suggested_test', sa.Text),
        sa.Column('severity', severity_level, default='warning'),
        sa.Column('is_addressed', sa.Boolean, default=False),
        sa.Column('addressed_by_test_id', UUID(as_uuid=True), nullable=True),
    )

    # Failure Analyses table
    op.create_table(
        'failure_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id'), nullable=False),
        sa.Column('failure_type', sa.String(100)),
        sa.Column('summary', sa.Text),
        sa.Column('first_failing_signal', sa.String(255)),
        sa.Column('affected_module', sa.String(255)),
        sa.Column('relevant_rtl_lines', JSONB, default=[]),
        sa.Column('relevant_signals', ARRAY(sa.String), default=[]),
        sa.Column('root_cause_hypothesis', sa.Text),
        sa.Column('confidence', confidence_level, default='low'),
        sa.Column('evidence', JSONB, default=[]),
        sa.Column('suggested_investigation', sa.Text),
        sa.Column('potential_fix', sa.Text),
        sa.Column('is_confirmed', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime, default=sa.func.now()),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100)),
        sa.Column('resource_id', UUID(as_uuid=True)),
        sa.Column('details', JSONB, default={}),
        sa.Column('user_id', sa.String(255)),
        sa.Column('ip_address', sa.String(45)),
    )
    op.create_index('idx_audit_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('failure_analyses')
    op.drop_table('coverage_gaps')
    op.drop_table('coverage_reports')
    op.drop_table('simulation_results')
    op.drop_table('simulations')
    op.drop_table('tests')
    op.drop_table('assertions')
    op.drop_table('verification_items')
    op.drop_table('verification_plans')
    op.drop_table('knowledge_graphs')
    op.drop_table('design_modules')
    op.drop_table('designs')
    op.drop_table('projects')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS test_status')
    op.execute('DROP TYPE IF EXISTS confidence_level')
    op.execute('DROP TYPE IF EXISTS severity_level')
    op.execute('DROP TYPE IF EXISTS analysis_status')
    op.execute('DROP TYPE IF EXISTS project_status')