# Limitations & Known Issues

## Current Limitations (MVP)

### RTL Parser
- **Not a full IEEE 1800 parser**: Uses regex-based parsing, handles ~95% of production RTL
- **Limited preprocessor support**: Basic `define and `include only
- **No elaboration**: Cannot resolve parameterized modules fully without values
- **Complex constructs**: May miss generate blocks, complex typedefs, packages
- **Workaround**: Use Verilator for full parsing in production

### Specification Parser
- **Markdown only**: PDF/Word parsing requires additional libraries
- **Heuristic-based**: Requirement extraction uses keywords, not NLP
- **No formal semantics**: Requirements stored as text, not formal logic

### Assertion Generation
- **Template-based**: Generated from detected patterns, not full formal verification
- **False positives possible**: Confidence scoring helps but not guaranteed
- **No property proving**: Assertions are for simulation, not formal proof

### Test Generation
- **Directed tests**: Manual stimulus, not fully automated constraint solving
- **UVM incomplete**: Basic components only, no register model, no sequences library
- **No coverage-driven constraints**: Random tests use `$urandom`, not coverage-directed

### Coverage Analysis
- **Verilator only**: Commercial simulator formats not supported
- **No functional coverage parsing**: Only code coverage (line/branch/toggle/FSM)
- **Gap classification heuristic**: Reachability estimation is approximate

### Simulation
- **Open-source only**: Verilator and Icarus Verilog
- **No commercial simulator integration**: Questa/VCS/Xcelium adapters not implemented
- **No distributed simulation**: Single-machine only

### AI Agents
- **Offline fallback**: Rule-based when LLM unavailable
- **No persistent learning**: Agents don't learn from project history yet
- **Single-turn**: No multi-turn conversation memory in MVP
- **Hallucination risk**: Mitigated by confidence scoring and evidence requirements

### Formal Verification
- **Not implemented**: Placeholder only
- **No SMT-LIB generation**: Formal property export not available

### Waveform Analysis
- **VCD only**: FST/FSDB not supported
- **Limited querying**: Basic signal context, no advanced temporal queries

### UI/UX
- **Single-user**: No team collaboration, comments, reviews
- **No Git integration**: Version control not connected
- **Basic visualization**: No advanced graph exploration

## Known Issues

### RTL Parser
1. **Parameter default values**: Complex expressions may not parse correctly
2. **Interface parsing**: Modports and clocking blocks partially supported
3. **Package parsing**: Limited support for package imports

### Coverage Engine
1. **XML namespace issues**: Verilator XML format varies by version
2. **Large file handling**: Memory intensive for large coverage databases

### Simulation Orchestrator
1. **Path handling**: Windows paths may cause issues in Docker
2. **Timeout reliability**: Process termination not always clean

### Database
1. **JSONB querying**: Complex queries on JSONB fields may be slow
2. **Migration conflicts**: Parallel development may cause migration conflicts

## Planned Improvements

### V1 (Next Release)
- [ ] Full Verilator XML parsing with version detection
- [ ] UVM register model generation
- [ ] Formal verification adapter (Yosys-SMTBMC)
- [ ] Waveform FST support
- [ ] Git integration with commit-linked runs
- [ ] Multi-user projects with RBAC

### V2
- [ ] Commercial simulator adapters (Questa, VCS)
- [ ] Advanced coverage (functional, assertion)
- [ ] Mutation testing integration
- [ ] Flaky test detection and quarantine
- [ ] AI-powered test optimization
- [ ] Distributed simulation support

### V3
- [ ] Persistent agent learning
- [ ] Multi-turn AI conversations
- [ ] Requirement formalization (SysML/ReqIF)
- [ ] Advanced waveform queries (temporal logic)
- [ ] SoC-level verification support
- [ ] Hardware/software co-verification

## Workarounds

### For Complex RTL
```bash
# Use Verilator for parsing
verilator --lint-only -Wall design.sv
# Or use commercial parser API
```

### For Coverage
```python
# Use Verilator coverage API directly
verilator_coverage --annotate annotated coverage.dat
# Parse annotated source for detailed coverage
```

### For Formal
```bash
# External formal tools
sby -f formal.sby
# or
yosys-smtbmc -p "prove" design.sv
```

### For UVM
```systemverilog
// Use generated components as starting point
// Extend with register model, sequences, etc.
```

## Feedback

Report issues at: https://github.com/verifix/verifix/issues

Include:
- RTL snippet that fails
- Expected vs actual behavior
- Verilator version
- Log output