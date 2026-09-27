# AI Agents Architecture

## Overview

VerifiX AI uses a multi-agent architecture coordinated by an Orchestrator. Each agent specializes in a specific verification task and operates through a controlled tool system.

## Agent Types

### 1. Project Manager Agent
**Responsibilities:**
- Task tracking and progress monitoring
- Coordination between agents
- Project memory management
- Duplicate work prevention

**Tools:**
- `create_task`, `update_progress`, `query_memory`

### 2. Specification Analyst Agent
**Responsibilities:**
- Parse PDF, Markdown, Word documents
- Extract structured requirements with unique IDs (REQ-XXX)
- Identify timing, protocol, reset, error handling requirements
- Store requirements in database

**Tools:**
- `parse_spec`, `extract_requirements`, `store_requirements`

### 3. RTL Analyst Agent
**Responsibilities:**
- Parse RTL and build design understanding
- Extract modules, ports, signals, clocks, resets, FSMs
- Detect protocols (valid/ready, FIFO, bus)
- Identify corner cases and suspicious constructs
- Build Knowledge Graph

**Tools:**
- `parse_rtl`, `build_knowledge_graph`, `analyze_module`

### 4. Planner Agent
**Responsibilities:**
- Generate verification objectives from RTL and spec
- Prioritize by risk, complexity, coverage gaps
- Create traceability matrix
- Generate test categories

**Tools:**
- `generate_plan`, `prioritize_items`, `trace_requirements`

### 5. Assertion Generator Agent
**Responsibilities:**
- Generate SVA assertions for protocols, FSMs, FIFOs, counters
- Provide evidence, confidence levels, false-positive warnings
- Map assertions to requirements

**Tools:**
- `generate_assertions`, `validate_syntax`, `check_false_positives`

### 6. Test Generator Agent
**Responsibilities:**
- Generate directed tests for specific scenarios
- Generate constrained-random tests for broad exploration
- Generate UVM components (seq_item, sequence, monitor, driver, agent, scoreboard)
- Generate coverage-targeted tests

**Tools:**
- `generate_directed`, `generate_random`, `generate_uvm`, `target_coverage`

### 7. Coverage Intelligence Agent
**Responsibilities:**
- Parse coverage reports (Verilator XML, text)
- Identify gaps and classify reachability
- Estimate coverage impact
- Suggest targeted tests

**Tools:**
- `parse_coverage`, `identify_gaps`, `classify_reachability`, `suggest_tests`

### 8. Failure Triage Agent
**Responsibilities:**
- Parse simulation logs
- Classify failures (RTL bug, testbench bug, assertion, environment)
- Cluster similar failures
- Find first meaningful failure

**Tools:**
- `parse_log`, `classify_failure`, `cluster_similar`

### 9. Root Cause Agent
**Responsibilities:**
- Analyze waveforms around failure
- Compare passing vs failing runs
- Build reasoning chains (FACT/INFERENCE/HYPOTHESIS/UNKNOWN)
- Suggest debugging steps

**Tools:**
- `analyze_waveform`, `compare_runs`, `build_reasoning_chain`

### 10. Regression Intelligence Agent
**Responsibilities:**
- Compare regression runs
- Detect flaky tests
- Correlate failures with Git changes
- Recommend minimal regression

**Tools:**
- `compare_regressions`, `detect_flaky`, `correlate_changes`

### 11. Formal Verification Agent
**Responsibilities:**
- Generate formal properties (safety, liveness)
- Interface with formal tools (Yosys-SMTBMC, EBMC)
- Extract proof evidence

**Tools:**
- `generate_formal_props`, `run_formal`, `extract_proof`

## Orchestrator

The `AgentOrchestrator` coordinates the complete verification loop:

```python
async def run_verification_loop(project_id: str, goal: str):
    # 1. UNDERSTAND
    design = await rtl_analyst.analyze(project_id)
    spec = await spec_analyst.analyze(project_id)
    
    # 2. PLAN
    plan = await planner.generate(design, spec)
    
    # 3. GENERATE
    assertions = await assertion_gen.generate(design, plan)
    tests = await test_gen.generate(design, plan)
    
    # 4. COMPILE + SIMULATE
    sim_results = await simulate(project_id, assertions, tests)
    
    # 5. ANALYZE + GAP DETECTION
    coverage = await coverage_intel.analyze(sim_results)
    gaps = await coverage_intel.find_gaps(coverage)
    
    # 6. ITERATE
    if gaps:
        new_tests = await test_gen.target_gaps(gaps)
        return await run_verification_loop(project_id, goal)
    
    # 7. REPORT
    return await generate_report(project_id)
```

## Tool System

All AI actions go through a controlled tool system:

```python
class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register(self, name: str, fn: callable, schema: dict, permissions: list):
        self.tools[name] = Tool(fn, schema, permissions)

# Permission levels:
# - read: view data
# - write: create/modify files
# - execute: run simulations
# - human_approval: requires explicit approval

tools = {
    "read_file": Tool(fn=read_file, permissions=["read"]),
    "search_code": Tool(fn=search_code, permissions=["read"]),
    "parse_rtl": Tool(fn=parse_rtl, permissions=["read"]),
    "get_design_graph": Tool(fn=get_kg, permissions=["read"]),
    "generate_file": Tool(fn=write_file, permissions=["write", "human_approval"]),
    "compile": Tool(fn=compile_rtl, permissions=["execute", "human_approval"]),
    "run_simulation": Tool(fn=run_sim, permissions=["execute", "human_approval"]),
    "get_coverage": Tool(fn=get_coverage, permissions=["read"]),
    "analyze_waveform": Tool(fn=analyze_vcd, permissions=["read"]),
    "run_regression": Tool(fn=run_regression, permissions=["execute", "human_approval"]),
    "apply_patch": Tool(fn=apply_diff, permissions=["write", "human_approval"]),
}
```

## LLM Provider Abstraction

```python
class LLMProvider:
    async def complete(self, prompt: str, system: str = "") -> LLMResponse
    async def generate_systemverilog(self, prompt: str, context: str) -> LLMResponse
    async def analyze_failure(self, failure_info: str, rtl_context: str) -> LLMResponse

# Supported providers:
# - OpenAI (GPT-4, GPT-4o)
# - Anthropic (Claude)
# - Local models via OpenAI-compatible API
# - Offline mode (rule-based fallback)
```

## Memory Layers

1. **Project Memory**: Persistent design knowledge, requirements, assertions
2. **Session Memory**: Current conversation context
3. **Evidence Memory**: Historical simulation runs, failures, coverage, fixes

## Human-in-the-Loop Modes

| Mode | AI Actions | Human Approval |
|------|------------|----------------|
| Assist | Suggest only | Everything |
| Collaborative | Generate & execute verification | Code modifications |
| Controlled Autonomous | Predefined loops within limits | Configuration changes |

## Evidence Classification

Every AI conclusion is tagged:

- **FACT**: Directly observed (e.g., "Assertion failed at 12,450 ns")
- **INFERENCE**: Reasoned from facts (e.g., "Failure related to FIFO underflow")
- **HYPOTHESIS**: Unverified theory (e.g., "Likely cause: incorrect read pointer")
- **UNKNOWN**: Insufficient evidence (e.g., "Waveform lacks signal visibility")

## Prompt Engineering

Agents use structured prompts with:
- Role definition
- Output format specification
- Evidence requirements
- Confidence scoring
- False-positive warnings

Example (Assertion Generator):
```
You are an expert SystemVerilog verification engineer.
Generate SVA assertions for the given RTL module.
For each assertion provide:
1. Assertion code (syntactically valid)
2. Explanation of what it checks
3. Signals used
4. Confidence level (high/medium/low)
5. Potential false-positive conditions
6. Source evidence from RTL
```