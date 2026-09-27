# Verification Engine

## Overview

The Verification Engine is the core of VerifiX AI, providing automated generation of verification plans, assertions, tests, and coverage analysis from RTL designs.

## Engines

### 1. RTL Parser (`engines/rtl_parser/`)

Parses SystemVerilog/Verilog into structured data:

```python
from app.engines.rtl_parser.parser import RTLParser

parser = RTLParser()
modules = parser.parse(rtl_content, "design.sv")

# Access parsed data:
for module in modules:
    print(module.name, module.ports, module.signals)
    print(module.fsm_info)        # FSMs with states/transitions
    print(module.metadata)        # Protocol detection, corner cases
```

**Extracted Information:**
- Modules, interfaces, packages
- Ports (direction, width, type)
- Signals (type, width, const)
- Parameters
- FSMs (states, transitions, encodings)
- Always blocks (clock, reset, sensitivity)
- Assign statements
- Module instances
- Existing assertions
- Functions, tasks

**Protocol Detection:**
- Valid/ready handshake
- FIFO (full/empty/overflow/underflow)
- Bus interfaces (AXI-like, simple)
- Counters
- Memories
- Pipelines

### 2. Knowledge Graph Builder (`engines/knowledge_graph/`)

Builds a queryable graph from parsed RTL:

```python
from app.engines.knowledge_graph.builder import KnowledgeGraphBuilder

kg = KnowledgeGraphBuilder()
graph = kg.build(modules)

# Query graph:
modules_needing_verification = kg.get_modules_needing_verification()
uncovered_fsms = kg.get_uncovered_fsms()
modules_without_assertions = kg.get_modules_with_no_assertions()
```

**Graph Structure:**
- Nodes: modules, ports, signals, FSMs, states, instances, always blocks, assertions
- Edges: has_port, has_signal, has_fsm, instantiates, drives, depends_on, clock_of, reset_of

### 3. Verification Planner (`engines/verification_planner/`)

Generates comprehensive verification plans:

```python
from app.engines.verification_planner.planner import VerificationPlanGenerator

planner = VerificationPlanGenerator()
plan = planner.generate(modules, specification_text)

# Plan structure:
plan["items"]           # Verification items
plan["summary"]         # Statistics
plan["traceability"]    # Requirement → Item mapping
```

**Plan Categories:**
- Functional (basic operation, parameters)
- Port behavior (boundary values, outputs)
- FSM verification (states, transitions, reset, invalid)
- Clock/reset behavior
- Protocol compliance (handshake, FIFO, bus)
- Corner cases (auto-detected from RTL)
- Assertions (generate or verify existing)
- Coverage targets (line, branch, FSM)

**Source Types:**
- `rtl-derived`: From RTL structure
- `spec-derived`: From specification keywords
- `ai-inferred`: AI-suggested items

### 4. Assertion Generator (`engines/assertion_generator/`)

Generates SystemVerilog Assertions:

```python
from app.engines.assertion_generator.generator import AssertionGenerator

gen = AssertionGenerator()
assertions = gen.generate(modules)

# Each assertion includes:
{
    "name": "fifo_sync_reset_clears_registers",
    "assertion_code": "property ... endproperty",
    "explanation": "When reset...",
    "signals_used": ["rst", "clk", "full", "empty"],
    "confidence": "high",
    "source_evidence": "Module has async reset...",
    "false_positive_conditions": "Non-zero reset values..."
}
```

**Assertion Types:**
- Reset behavior (clears registers, initial values)
- Handshake protocol (data stability, transfer completion)
- FSM legality (valid states, legal transitions)
- FIFO behavior (no write when full, no read when empty)
- Counter properties (range, overflow)
- Output stability
- Mutual exclusion

### 5. Test Generator (`engines/test_generator/`)

Generates multiple test types:

```python
from app.engines.test_generator.generator import TestGenerator

gen = TestGenerator()
tests = gen.generate(modules, coverage_gaps)
```

**Test Types:**
- **Directed**: Basic, reset, port sweep, FSM transitions, protocol, FIFO
- **Constrained-random**: Random stimulus with `$urandom_range`
- **UVM**: Sequence items, sequences, monitors

**Coverage-Targeted Tests:**
```python
tests = gen.generate(modules, coverage_gaps)
# Generates tests specifically for uncovered coverage points
```

### 6. Coverage Engine (`engines/coverage_engine/`)

Analyzes coverage and identifies gaps:

```python
from app.engines.coverage_engine.analyzer import CoverageAnalyzer

analyzer = CoverageAnalyzer()

# Parse coverage reports
coverage = analyzer.parse_verilator_xml(xml_content)
coverage = analyzer.parse_verilator_coverage(text_content)

# Identify gaps
gaps = analyzer.identify_gaps(coverage, rtl_content, "module_name")

# Compare before/after
comparison = analyzer.compare_coverage(before, after)
```

**Gap Classification:**
- `reachable_untested`: Reachable but not exercised
- `potentially_unreachable`: Complex conditions, error paths
- `unreachable`: Provably unreachable code

### 7. Log Analyzer (`engines/log_analyzer/`)

Parses simulation logs:

```python
from app.engines.log_analyzer.analyzer import LogAnalyzer

analyzer = LogAnalyzer()
result = analyzer.parse_log(simulation_log)

# Result includes:
# - total_errors, total_warnings
# - assertion_failures
# - first_failure
# - failure_clusters
# - root_cause_analysis
```

### 8. Root Cause Engine (`engines/root_cause_engine/`)

Analyzes failures:

```python
from app.engines.root_cause_engine.engine import RootCauseEngine

engine = RootCauseEngine()
result = engine.analyze(failure_info, rtl_content, log_analysis)
```

### 9. Regression Engine (`engines/regression_engine/`)

Manages regression runs:

```python
from app.engines.regression_engine.engine import RegressionEngine

engine = RegressionEngine()
result = engine.analyze_regression(results, changed_modules)
```

### 10. Waveform Analyzer (`engines/waveform_analyzer/`)

Analyzes VCD waveforms:

```python
from app.engines.waveform_analyzer.analyzer import WaveformAnalyzer

analyzer = WaveformAnalyzer()
result = analyzer.parse_vcd(vcd_content)

# Signal context around failure
context = analyzer.analyze_signal_around_failure(signals, time, window)
```

## Integration: VerificationService

```python
from app.services.verification_service import VerificationService

service = VerificationService()

# Complete flow
result = service.full_verification_flow(rtl_content, specification)

# Individual steps
analysis = service.analyze_rtl(rtl_content)
plan = service.generate_plan(rtl_content, specification)
assertions = service.generate_assertions(rtl_content)
tests = service.generate_tests(rtl_content, coverage_gaps)
coverage = service.analyze_coverage(report, rtl_content, module_name)
```

## Evidence-Driven Design

Every generated artifact includes traceability:

```
Requirement (REQ-FIFO-001)
    ↓
Verification Objective (VF-FIFO-005)
    ↓
Assertion (a_no_write_when_full)
    ↓
Test (tb_fifo_sync_handshake)
    ↓
Coverage Point (handshake_backpressure)
    ↓
Simulation Evidence (SIM-042 PASS)
    ↓
Result (VERIFIED)
```

## Configuration

```python
# In config.py
VERILATOR_PATH = "verilator"
ICARUS_PATH = "iverilog"
SIMULATION_TIMEOUT = 300
MAX_CONCURRENT_SIMS = 4
AI_CONFIDENCE_THRESHOLD = 0.6
```

## Extending the Engine

### Adding New Assertion Types

```python
class CustomAssertionGenerator(AssertionGenerator):
    def _gen_custom_assertions(self, module):
        # Your custom logic
        return assertions
```

### Adding New Test Types

```python
class CustomTestGenerator(TestGenerator):
    def _gen_my_test_type(self, module):
        # Your custom test generation
        return tests
```

### Adding New Coverage Parsers

```python
class CustomCoverageAnalyzer(CoverageAnalyzer):
    def parse_my_format(self, content):
        # Your parsing logic
        return coverage
```