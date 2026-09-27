# Simulation Engine

## Overview

The simulation engine provides a unified interface for running RTL simulations across multiple simulators, with Verilator as the primary open-source option and Icarus Verilog as a secondary option.

## Supported Simulators

| Simulator | Status | Features |
|-----------|--------|----------|
| Verilator | Primary | Fast, good SV support, coverage, waveforms |
| Icarus Verilog | Secondary | Good for quick checks, VVP runtime |
| Questa | Planned | Commercial, advanced features |
| VCS | Planned | Commercial, high performance |
| Xcelium | Planned | Commercial, low power |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SimulationOrchestrator                     │
├─────────────────────────────────────────────────────────────┤
│  compile(rtl_files, config, testbench) → SimulationResult  │
│  simulate(compiled_dir, config, test_name) → SimulationResult│
│  run_test(rtl_files, test_code, config) → SimulationResult  │
│  run_regression(rtl_files, test_files, config) → dict       │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │ Verilator │    │  Icarus   │    │ Commercial│
    │  Adapter  │    │  Adapter  │    │ Adapters  │
    └───────────┘    └───────────┘    └───────────┘
```

## Configuration

```python
@dataclass
class SimulationConfig:
    simulator: str = "verilator"      # verilator, icarus
    top_module: str = ""              # Top module name
    clock_signal: str = "clk"         # Clock signal name
    reset_signal: str = "rst"         # Reset signal name
    timeout: int = 300                # Timeout in seconds
    extra_flags: list = []            # Simulator-specific flags
    include_dirs: list = []           # Include directories
```

## Verilator Adapter

### Compilation
```bash
verilator --binary --top-module <top> -Wall --trace --cc <rtl_files> <testbench>
```

### Simulation
```bash
./obj_dir/V<top_module>  # or ./V<top_module>
```

### Coverage
```bash
verilator --coverage --coverage-line --coverage-branch --coverage-toggle
verilator_coverage --annotate <annotated_dir> <coverage.dat>
```

### Waveforms
```bash
# VCD (default)
verilator --trace
# FST (faster, smaller)
verilator --trace-fst
```

## Icarus Verilog Adapter

### Compilation
```bash
iverilog -g2012 -o sim.vvp <rtl_files> <testbench>
```

### Simulation
```bash
vvp sim.vvp
```

## Usage Examples

### Basic Simulation
```python
from app.engines.simulation.orchestrator import SimulationOrchestrator, SimulationConfig

orchestrator = SimulationOrchestrator()
config = SimulationConfig(
    simulator="verilator",
    top_module="tb_fifo",
    timeout=300
)

# Compile
result = orchestrator.compile(
    rtl_files=["rtl/fifo.sv"],
    config=config,
    testbench="tb/tb_fifo.sv"
)

if result.success:
    # Simulate
    sim_result = orchestrator.simulate(
        compiled_dir="obj_dir",
        config=config
    )
```

### Complete Test Run
```python
result = orchestrator.run_test(
    rtl_files=["rtl/fifo.sv"],
    test_code="""
module tb_fifo;
  // ... testbench code
endmodule
""",
    config=SimulationConfig(simulator="verilator", top_module="tb_fifo")
)

print(f"Success: {result.success}")
print(f"Log: {result.simulation_log}")
```

### Regression Run
```python
results = orchestrator.run_regression(
    rtl_files=["rtl/fifo.sv"],
    test_files=["tb/test1.sv", "tb/test2.sv", "tb/test3.sv"],
    config=config
)

for test_name, result in results.items():
    print(f"{test_name}: {'PASS' if result.success else 'FAIL'}")
```

## Coverage Collection

### Verilator Coverage
```bash
# Compile with coverage
verilator --coverage --coverage-line --coverage-branch --coverage-toggle ...

# Run simulation (generates coverage.dat)
./Vtop

# Generate report
verilator_coverage --annotate annotated coverage.dat
```

### Parsing Coverage
```python
from app.engines.coverage_engine.analyzer import CoverageAnalyzer

analyzer = CoverageAnalyzer()

# Parse Verilator XML coverage
coverage = analyzer.parse_verilator_xml(xml_content)

# Or parse text output
coverage = analyzer.parse_verilator_coverage(text_content)

# Identify gaps
gaps = analyzer.identify_gaps(coverage, rtl_content, "fifo_sync")
```

## Waveform Generation

### VCD Format
```systemverilog
initial begin
  $dumpfile("waveform.vcd");
  $dumpvars(0, tb_fifo);
end
```

### FST Format (Verilator)
```bash
verilator --trace-fst
```

### Parsing Waveforms
```python
from app.engines.waveform_analyzer.analyzer import WaveformAnalyzer

analyzer = WaveformAnalyzer()

# Parse VCD
result = analyzer.parse_vcd(vcd_content)

# Get signal context around failure
context = analyzer.analyze_signal_around_failure(
    signals, failure_time=12500, window=100
)
```

## Sandboxing

Simulations run in isolated containers:

```yaml
# docker-compose.yml security settings
simulation:
  timeout: 300
  memory_limit: "4g"
  cpu_limit: "2"
  network: "none"
  read_only_rootfs: true
  allowed_paths: ["/app/storage", "/tmp"]
```

## Error Handling

### Compilation Errors
- Syntax errors
- Missing modules
- Parameter mismatches
- Port connection errors

### Runtime Errors
- Assertion failures
- X-propagation
- Deadlock/hang (timeout)
- Memory overflow

### Log Analysis
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

## Best Practices

1. **Use parameters** for test configurability
2. **Add timeout watchdogs** in testbenches
3. **Generate coverage** with `--coverage` flags
4. **Use `$finish`** with explicit pass/fail messages
5. **Separate testbenches** from RTL for reusability
6. **Parameterize clock/reset** in config
7. **Use unique test names** for regression tracking

## Troubleshooting

### Verilator Not Found
```bash
# Ubuntu/Debian
apt-get install verilator

# macOS
brew install verilator

# Docker (included in image)
```

### Compilation Fails
- Check SystemVerilog version (`-g2012` for Icarus)
- Verify all `include` paths
- Check for unsupported constructs

### Simulation Hangs
- Add timeout to testbench
- Check for combinational loops
- Verify reset sequences

### No Coverage Data
- Compile with `--coverage` flags
- Run simulation to generate `coverage.dat`
- Use `verilator_coverage` to parse