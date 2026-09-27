# FIFO Demo - Complete Verification Flow

## Overview

This demo demonstrates the complete VerifiX AI verification flow using a parameterized synchronous FIFO.

## Demo RTL: `examples/fifo/fifo.sv`

```systemverilog
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
    // ... implementation with 7 assertions + 5 cover properties
endmodule
```

## Demo Specification: `examples/fifo/fifo_spec.md`

```markdown
# FIFO Synchronous - Verification Specification

## Requirements

REQ-FIFO-001: The FIFO shall not allow a write when full.
REQ-FIFO-002: The FIFO shall not allow a read when empty.
REQ-FIFO-003: On reset, full=0, empty=1, count=0, pointers=0.
REQ-FIFO-004: Write pointer increments on valid write.
REQ-FIFO-005: Read pointer increments on valid read.
REQ-FIFO-006: Count tracks occupancy correctly.
REQ-FIFO-007: Full and empty are mutually exclusive.
REQ-FIFO-008: Data integrity maintained through FIFO.
REQ-FIFO-009: Simultaneous read/write supported when not full/empty.
REQ-FIFO-010: Write attempted when full is blocked.
REQ-FIFO-011: Read attempted when empty is blocked.
REQ-FIFO-012: Reset during operation handled correctly.
```

## Running the Demo

### Option 1: Web UI (Recommended)

1. Start the platform:
```bash
docker compose -f docker/docker-compose.yml up --build
```

2. Open http://localhost:3000

3. Click **"Analyze FIFO Demo"** on the dashboard

4. Watch the complete flow:
   - RTL Analysis → Knowledge Graph
   - Verification Plan Generation
   - SVA Assertion Generation
   - Test Generation (Directed + Random + UVM)
   - Simulation via Verilator
   - Coverage Analysis & Gap Detection
   - Targeted Test Generation
   - Final Report

### Option 2: API Calls

```bash
# 1. Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "FIFO Demo", "description": "Auto-generated FIFO verification"}'

# 2. Analyze RTL
curl -X POST http://localhost:8000/api/v1/rtl/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "'"$(cat examples/fifo/fifo.sv | sed ':a;N;$!ba;s/\n/\\n/g; s/"/\\"/g')"'"}'

# 3. Generate verification plan
curl -X POST http://localhost:8000/api/v1/verification/plan \
  -H "Content-Type: application/json" \
  -d '{"rtl_content": "'"$(cat examples/fifo/fifo.sv | sed ':a;N;$!ba;s/\n/\\n/g; s/"/\\"/g')"'"}'

# 4. Generate assertions
curl -X POST http://localhost:8000/api/v1/verification/assertions \
  -H "Content-Type: application/json" \
  -d '{"rtl_content": "'"$(cat examples/fifo/fifo.sv | sed ':a;N;$!ba;s/\n/\\n/g; s/"/\\"/g')"'"}'

# 5. Generate tests
curl -X POST http://localhost:8000/api/v1/verification/tests \
  -H "Content-Type: application/json" \
  -d '{"rtl_content": "'"$(cat examples/fifo/fifo.sv | sed ':a;N;$!ba;s/\n/\\n/g; s/"/\\"/g')"'"}'

# 6. Run full flow
curl -X POST http://localhost:8000/api/v1/verification/full-flow \
  -H "Content-Type: application/json" \
  -d '{"rtl_content": "'"$(cat examples/fifo/fifo.sv | sed ':a;N;$!ba;s/\n/\\n/g; s/"/\\"/g')"'", "specification": "Parameterized sync FIFO..."}'
```

### Option 3: Python Script

```python
# demo_fifo.py
import asyncio
from app.services.verification_service import VerificationService

async def main():
    service = VerificationService()
    
    with open("examples/fifo/fifo.sv") as f:
        rtl = f.read()
    
    with open("examples/fifo/fifo_spec.md") as f:
        spec = f.read()
    
    # Run complete flow
    result = await service.full_verification_flow(rtl, spec)
    
    print(f"Modules: {result['analysis']['summary']['num_modules']}")
    print(f"Plan items: {result['plan']['summary']['total_items']}")
    print(f"Assertions: {result['assertions']['total']}")
    print(f"Tests: {result['tests']['total']}")
    print(f"Test types: {result['tests']['types']}")

asyncio.run(main())
```

## Expected Output

### RTL Analysis
- 1 module: `fifo_sync`
- 9 ports (clk, reset, wr_en, rd_en, din, dout, full, empty, count)
- 6 internal signals (mem, wr_ptr, rd_ptr, wr_ptr_next, rd_ptr_next, count_next, full_next, empty_next)
- 0 FSMs (FIFO uses pointer-based design)
- 7 existing assertions
- Protocol: FIFO detected
- Corner cases: 6 categories detected

### Verification Plan (18 items)
| Category | Items |
|----------|-------|
| functional | 3 (basic, params, outputs) |
| boundary | 9 (port boundaries) |
| protocol | 2 (FIFO, handshake) |
| reset | 2 |
| corner_case | 3 |
| coverage | 3 (line, branch, FSM) |

### Assertions Generated (15)
- Reset assertions (2)
- Handshake assertions (4)
- FIFO assertions (6)
- Counter assertions (2)
- Stability assertions (1)

### Tests Generated (20+)
- Directed: 8 (basic, reset, sweep, FIFO fill/drain, handshake)
- Constrained-random: 1
- UVM: 8 (seq_item, 2 sequences, monitor, driver, agent, scoreboard, env, test)

### Coverage Targets
- Line: 95%+
- Branch: 90%+
- FSM: N/A (no explicit FSM)
- Assertion: 100%
- Functional: 100% (cover properties)

## Verification Report

The final report includes:

```
========================================
VERIFICATION REPORT: FIFO Demo
========================================

Requirements: 12
Verified: 12
Tests: 28
Assertions: 15
Functional Coverage: 94%
Code Coverage: 96%
Failing Tests: 0
Uncovered Scenarios: 2

Per-Requirement Status:
REQ-FIFO-001: VERIFIED (a_no_write_when_full, tb_fifo_handshake)
REQ-FIFO-002: VERIFIED (a_no_read_when_empty, tb_fifo_handshake)
REQ-FIFO-003: VERIFIED (a_reset, tb_fifo_reset)
REQ-FIFO-004: VERIFIED (a_wr_ptr_increments, tb_fifo_fifo)
REQ-FIFO-005: VERIFIED (a_rd_ptr_increments, tb_fifo_fifo)
REQ-FIFO-006: VERIFIED (a_count_tracking, tb_fifo_fifo)
REQ-FIFO-007: VERIFIED (a_full_empty_mutex, tb_fifo_fifo)
REQ-FIFO-008: PARTIALLY_VERIFIED (data integrity - needs scoreboard)
REQ-FIFO-009: VERIFIED (c_simultaneous_rw, tb_fifo_fifo)
REQ-FIFO-010: VERIFIED (c_wr_at_full, tb_fifo_fifo)
REQ-FIFO-011: VERIFIED (c_rd_at_empty, tb_fifo_fifo)
REQ-FIFO-012: VERIFIED (tb_fifo_reset)

Remaining Gaps:
1. Data integrity scoreboard not implemented (UVM scoreboard needed)
2. Parameter variations (DEPTH=1, DATA_WIDTH=8) not tested

Recommendations:
1. Extend UVM scoreboard for data integrity checking
2. Add parametric test sweep for DEPTH/DATA_WIDTH
3. Add stress test with 10000 random transactions
```

## Customization

### Modify RTL
Edit `examples/fifo/fifo.sv` and re-run analysis.

### Add Requirements
Edit `examples/fifo/fifo_spec.md` with new REQ-XXX entries.

### Custom Verification
Use the API to generate specific artifacts:
```python
# Just assertions
assertions = service.generate_assertions(rtl)

# Just tests for specific gaps
tests = service.generate_tests(rtl, coverage_gaps=my_gaps)
```

## Troubleshooting

### Verilator Not Found
```bash
# In Docker (included)
# Local: apt-get install verilator
```

### Simulation Timeout
Increase timeout in SimulationConfig:
```python
config = SimulationConfig(timeout=600)  # 10 minutes
```

### Low Coverage
Run gap-targeted tests:
```python
gaps = analyzer.identify_gaps(coverage, rtl, "fifo_sync")
targeted_tests = test_gen.generate(modules, gaps)
```

### AI Features Not Working
Set LLM_API_KEY in .env:
```bash
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o
```