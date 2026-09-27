# FIFO Synchronous - Verification Demo RTL

## Overview

This is a clean, parameterized synchronous FIFO implementation designed as the canonical example for **ASTRIXCORE VERIFICATION AI V0.1**.

The FIFO demonstrates:
- Parameterized depth and data width
- Standard FIFO interface (wr_en, rd_en, din, dout, full, empty)
- Occupancy counter
- Read/write pointers
- Built-in SystemVerilog Assertions (SVA)
- Cover properties for functional coverage

## Interface

| Signal | Direction | Width | Description |
|--------|-----------|-------|-------------|
| clk | input | 1 | Rising-edge clock |
| reset | input | 1 | Active-high synchronous reset |
| wr_en | input | 1 | Write enable |
| rd_en | input | 1 | Read enable |
| din | input | DATA_WIDTH | Data input |
| dout | output | DATA_WIDTH | Data output |
| full | output | 1 | FIFO full flag |
| empty | output | 1 | FIFO empty flag |
| count | output | $clog2(DEPTH)+1 | Occupancy count |

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| DEPTH | 16 | FIFO depth (number of entries) |
| DATA_WIDTH | 32 | Data bus width |

## Assertions (Built-in)

| Assertion | Description |
|-----------|-------------|
| `a_reset` | On reset: full=0, empty=1, count=0, pointers=0 |
| `a_no_write_when_full` | Write enable not asserted when full |
| `a_no_read_when_empty` | Read enable not asserted when empty |
| `a_wr_ptr_increments` | Write pointer increments on valid write |
| `a_rd_ptr_increments` | Read pointer increments on valid read |
| `a_count_tracking` | Count equals wr_ptr - rd_ptr |
| `a_full_empty_mutex` | Full and empty mutually exclusive |

## Cover Properties

| Cover | Description |
|-------|-------------|
| `c_full` | FIFO reaches full state |
| `c_empty` | FIFO reaches empty state |
| `c_simultaneous_rw` | Simultaneous read and write |
| `c_wr_at_full` | Write attempted when full |
| `c_rd_at_empty` | Read attempted when empty |

## Verification Targets (V0.1)

The ASTRIXCORE VERIFICATION AI will automatically generate:

1. **Verification Plan** (12 items VP-001 through VP-012)
2. **SVA Assertions** (8+ assertions covering all key properties)
3. **Directed Tests** (12 test scenarios)
4. **UVM Testbench Structure** (test, env, agent, driver, monitor, sequencer, sequence, scoreboard)
5. **Simulation** via Verilator adapter
6. **Coverage Analysis** with gap detection
7. **Traceability Matrix** linking requirements → plan → assertions → tests → simulations

## Usage with AstrixCore

```bash
# Start the platform
docker compose up --build

# In the Dashboard, click "ANALYZE FIFO DEMO"
# This will:
# 1. Load fifo.sv
# 2. Create project
# 3. Analyze RTL
# 4. Generate verification plan
# 5. Generate SVA assertions
# 6. Generate directed tests
# 7. Generate UVM structure
# 8. Update dashboard with all artifacts
```

## Design Notes

- **Synchronous reset**: Active-high, single-cycle
- **Registered output**: `dout` is registered for timing closure
- **No X-propagation**: All registers initialized on reset
- **Parameterizable**: DEPTH and DATA_WIDTH are generic
- **Clean coding style**: No latches, no combinational loops, proper clock domain

## Known Limitations

- Single clock domain only (no async FIFO)
- No almost_full/almost_empty flags
- No ECC or parity
- No programmable thresholds

These are intentionally omitted to keep the V0.1 demo focused and verifiable.