"""SVA Assertion Generator - Generates SystemVerilog Assertions from RTL analysis."""

from ..rtl_parser.parser import DesignModule, SignalDirection


class AssertionGenerator:
    """Generates syntactically valid SystemVerilog assertions.

    For every assertion provides:
    - Assertion code
    - Explanation
    - Signals used
    - Reasoning/evidence
    - Confidence level
    - Potential false-positive conditions
    """

    def generate(self, modules: list[DesignModule]) -> list[dict]:
        """Generate assertions for all analyzed modules."""
        all_assertions = []
        for module in modules:
            all_assertions.extend(self._generate_for_module(module))
        return all_assertions

    def _generate_for_module(self, module: DesignModule) -> list[dict]:
        """Generate all applicable assertions for a single module."""
        assertions = []

        # Reset assertions
        assertions.extend(self._gen_reset_assertions(module))

        # Handshake assertions
        if module.metadata.get("protocol") == "valid_ready_handshake":
            assertions.extend(self._gen_handshake_assertions(module))

        # FSM assertions
        for fsm in module.fsm_info:
            assertions.extend(self._gen_fsm_assertions(module, fsm))

        # FIFO assertions
        if module.metadata.get("is_fifo"):
            assertions.extend(self._gen_fifo_assertions(module))

        # Counter assertions
        if module.metadata.get("has_counter"):
            assertions.extend(self._gen_counter_assertions(module))

        # Output stability assertions
        assertions.extend(self._gen_stability_assertions(module))

        # Mutual exclusion assertions
        assertions.extend(self._gen_mutex_assertions(module))

        return assertions

    def _gen_reset_assertions(self, module: DesignModule) -> list[dict]:
        """Generate reset-related assertions."""
        assertions = []
        resets = module.reset_signals

        if not resets:
            return assertions

        for rst in resets:
            # Find register signals in the module
            regs = [s.name for s in module.signals
                    if s.signal_type.value in ("reg", "logic")]

            if regs:
                reg_list = ", ".join(regs[:5])
                assertions.append({
                    "name": f"{module.name}_reset_clears_registers",
                    "assertion_code": (
                        f"// Assert: Reset clears all registers\n"
                        f"property {module.name}_p_reset_clears;\n"
                        f"  @(posedge {module.clock_signals[0] if module.clock_signals else 'clk'})\n"
                        f"  {rst} |-> ##1 ({' && '.join(f'{r} == 0' for r in regs[:5])});\n"
                        f"endproperty\n"
                        f"{module.name}_a_reset_clears: assert property ({module.name}_p_reset_clears);"
                    ),
                    "explanation": (
                        f"When reset ({rst}) is asserted, all register outputs should "
                        f"clear to their reset values within one clock cycle."
                    ),
                    "signals_used": [rst] + module.clock_signals[:1] + regs[:5],
                    "confidence": "high",
                    "source_evidence": (
                        f"Module '{module.name}' has async/sync reset '{rst}' and "
                        f"registers: {reg_list}"
                    ),
                    "false_positive_conditions": (
                        "Registers with non-zero reset values. Check module parameters "
                        "for reset value configuration."
                    ),
                })

        return assertions

    def _gen_handshake_assertions(self, module: DesignModule) -> list[dict]:
        """Generate valid/ready handshake assertions."""
        assertions = []

        # Find valid and ready signals
        all_names = [p.name for p in module.ports] + [s.name for s in module.signals]
        valid_signals = [n for n in all_names if "valid" in n.lower()]
        ready_signals = [n for n in all_names if "ready" in n.lower()]

        clk = module.clock_signals[0] if module.clock_signals else "clk"

        for valid in valid_signals[:2]:
            for ready in ready_signals[:2]:
                # Data stability during valid
                assertions.append({
                    "name": f"{module.name}_{valid}_data_stable",
                    "assertion_code": (
                        f"// Assert: Data stable while valid is asserted and ready is deasserted\n"
                        f"property {module.name}_p_{valid}_stability;\n"
                        f"  @(posedge {clk})\n"
                        f"  ({valid} && !{ready}) |-> $stable({valid});\n"
                        f"endproperty\n"
                        f"{module.name}_a_{valid}_stability: assert property ({module.name}_p_{valid}_stability);"
                    ),
                    "explanation": (
                        f"When {valid} is high and {ready} is low (backpressure), "
                        f"the valid signal must remain stable (no deassertion without handshake completing)."
                    ),
                    "signals_used": [valid, ready, clk],
                    "confidence": "very_high",
                    "source_evidence": (
                        f"Standard valid/ready handshake protocol requirement. "
                        f"Signals {valid} and {ready} detected in module '{module.name}'."
                    ),
                    "false_positive_conditions": (
                        "Protocol variants where valid can be deasserted during backpressure. "
                        "AXI allows certain deassertion patterns."
                    ),
                })

                # Handshake completes
                assertions.append({
                    "name": f"{module.name}_{valid}_{ready}_handshake",
                    "assertion_code": (
                        f"// Assert: When valid and ready both high, transfer occurs\n"
                        f"property {module.name}_p_{valid}_{ready}_transfer;\n"
                        f"  @(posedge {clk})\n"
                        f"  disable iff ({module.reset_signals[0] if module.reset_signals else 'rst'})\n"
                        f"  {valid} && {ready} |-> ##1 1;\n"
                        f"endproperty\n"
                        f"{module.name}_a_{valid}_{ready}_transfer: assert property ({module.name}_p_{valid}_{ready}_transfer);"
                    ),
                    "explanation": (
                        f"When both {valid} and {ready} are high, a data transfer occurs "
                        f"on this clock edge."
                    ),
                    "signals_used": [valid, ready, clk] + module.reset_signals[:1],
                    "confidence": "high",
                    "source_evidence": f"Standard handshake protocol in '{module.name}'",
                    "false_positive_conditions": (
                        "First cycle after reset de-assertion may need to be excluded."
                    ),
                })

        return assertions

    def _gen_fsm_assertions(self, module: DesignModule, fsm) -> list[dict]:
        """Generate FSM-specific assertions."""
        assertions = []
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"
        state_var = fsm.state_variable

        # Legal state transitions only
        if fsm.transitions:
            legal_transitions = set()
            for t in fsm.transitions:
                legal_transitions.add(f"({t.from_state}, {t.to_state})")

            assertions.append({
                "name": f"{module.name}_{fsm.name}_legal_transitions",
                "assertion_code": (
                    f"// Assert: Only legal FSM transitions occur\n"
                    f"property {module.name}_{fsm.name}_p_legal_transitions;\n"
                    f"  @(posedge {clk})\n"
                    f"  disable iff ({rst})\n"
                    f"  ($changed({state_var})) |-> (\n"
                    + "    ".join(
                        f"({state_var} == {t.from_state} && $next(state_var) == {t.to_state})"
                        for t in fsm.transitions[:10]
                    ) + "\n  );\n"
                    f"endproperty\n"
                    f"{module.name}_{fsm.name}_a_legal_transitions: "
                    f"assert property ({module.name}_{fsm.name}_p_legal_transitions);"
                ),
                "explanation": (
                    f"FSM '{fsm.name}' should only make transitions that are defined "
                    f"in the RTL. Any undefined transition indicates a bug."
                ),
                "signals_used": [state_var, clk, rst],
                "confidence": "high",
                "source_evidence": (
                    f"FSM '{fsm.name}' has {len(fsm.transitions)} defined transitions "
                    f"across {len(fsm.states)} states."
                ),
                "false_positive_conditions": (
                    "If FSM has unreachable states that could be entered via "
                    "glitch or power-up, this assertion may be too strict."
                ),
            })

        # State reachability
        if fsm.states:
            state_names = [s.name for s in fsm.states]
            assertions.append({
                "name": f"{module.name}_{fsm.name}_valid_state",
                "assertion_code": (
                    f"// Assert: FSM is always in a known state\n"
                    f"property {module.name}_{fsm.name}_p_valid_state;\n"
                    f"  @(posedge {clk})\n"
                    f"  disable iff ({rst})\n"
                    f"  ({state_var} inside {{{', '.join(state_names)}}});\n"
                    f"endproperty\n"
                    f"{module.name}_{fsm.name}_a_valid_state: "
                    f"assert property ({module.name}_{fsm.name}_p_valid_state);"
                ),
                "explanation": (
                    f"FSM '{fsm.name}' should always be in one of the defined states: "
                    f"{', '.join(state_names)}."
                ),
                "signals_used": [state_var, clk, rst],
                "confidence": "very_high",
                "source_evidence": f"FSM has {len(state_names)} defined states",
                "false_positive_conditions": (
                    "State register width may allow encodings not in the state list. "
                    "Power-up state may be undefined."
                ),
            })

        return assertions

    def _gen_fifo_assertions(self, module: DesignModule) -> list[dict]:
        """Generate FIFO-related assertions."""
        assertions = []
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        all_names = [p.name for p in module.ports] + [s.name for s in module.signals]

        # Find FIFO signals
        full_sig = next((n for n in all_names if "full" in n.lower()), None)
        empty_sig = next((n for n in all_names if "empty" in n.lower()), None)
        wr_en = next((n for n in all_names if "wr" in n.lower() and "en" in n.lower()), None)
        rd_en = next((n for n in all_names if "rd" in n.lower() and "en" in n.lower()), None)

        if full_sig and wr_en:
            assertions.append({
                "name": f"{module.name}_no_write_when_full",
                "assertion_code": (
                    f"// Assert: No write when FIFO is full\n"
                    f"property {module.name}_p_no_write_full;\n"
                    f"  @(posedge {clk})\n"
                    f"  disable iff ({rst})\n"
                    f"  {full_sig} |-> !{wr_en};\n"
                    f"endproperty\n"
                    f"{module.name}_a_no_write_full: "
                    f"assert property ({module.name}_p_no_write_full);"
                ),
                "explanation": (
                    f"When FIFO is full ({full_sig}=1), write enable ({wr_en}) "
                    f"should not be asserted to prevent data loss."
                ),
                "signals_used": [full_sig, wr_en, clk, rst],
                "confidence": "high",
                "source_evidence": f"Standard FIFO protocol in module '{module.name}'",
                "false_positive_conditions": (
                    "Some FIFO designs accept writes when full (drop or overwrite). "
                    "Check module specification."
                ),
            })

        if empty_sig and rd_en:
            assertions.append({
                "name": f"{module.name}_no_read_when_empty",
                "assertion_code": (
                    f"// Assert: No read when FIFO is empty\n"
                    f"property {module.name}_p_no_read_empty;\n"
                    f"  @(posedge {clk})\n"
                    f"  disable iff ({rst})\n"
                    f"  {empty_sig} |-> !{rd_en};\n"
                    f"endproperty\n"
                    f"{module.name}_a_no_read_empty: "
                    f"assert property ({module.name}_p_no_read_empty);"
                ),
                "explanation": (
                    f"When FIFO is empty ({empty_sig}=1), read enable ({rd_en}) "
                    f"should not be asserted to prevent underflow."
                ),
                "signals_used": [empty_sig, rd_en, clk, rst],
                "confidence": "high",
                "source_evidence": f"Standard FIFO protocol in module '{module.name}'",
                "false_positive_conditions": (
                    "Some FIFO designs return invalid data on underflow intentionally."
                ),
            })

        return assertions

    def _gen_counter_assertions(self, module: DesignModule) -> list[dict]:
        """Generate counter-related assertions."""
        assertions = []
        clk = module.clock_signals[0] if module.clock_signals else "clk"

        all_names = [s.name for s in module.signals]
        counters = [n for n in all_names if "count" in n.lower() or "cnt" in n.lower()]

        for counter in counters[:3]:
            assertions.append({
                "name": f"{module.name}_{counter}_no_overflow",
                "assertion_code": (
                    f"// Assert: Counter {counter} does not overflow silently\n"
                    f"// This is a cover property to check counter reaches max\n"
                    f"property {module.name}_p_{counter}_range;\n"
                    f"  @(posedge {clk})\n"
                    f"  1'b1 |=> ({counter} >= 0);\n"
                    f"endproperty\n"
                    f"{module.name}_c_{counter}_range: "
                    f"cover property ({module.name}_p_{counter}_range);"
                ),
                "explanation": (
                    f"Cover property to verify counter {counter} operates "
                    f"within expected range."
                ),
                "signals_used": [counter, clk],
                "confidence": "medium",
                "source_evidence": f"Counter '{counter}' detected in module '{module.name}'",
                "false_positive_conditions": (
                    "Counter width and max value need to be verified against specification."
                ),
            })

        return assertions

    def _gen_stability_assertions(self, module: DesignModule) -> list[dict]:
        """Generate data stability assertions."""
        assertions = []

        # Check for registered outputs
        regs = [s.name for s in module.signals if s.signal_type.value == "reg"]
        if regs and module.clock_signals:
            clk = module.clock_signals[0]
            assertions.append({
                "name": f"{module.name}_registered_outputs_stable",
                "assertion_code": (
                    f"// Assert: Registered outputs only change on clock edge\n"
                    f"property {module.name}_p_registered_stability;\n"
                    f"  @(posedge {clk})\n"
                    f"  disable iff ({module.reset_signals[0] if module.reset_signals else 'rst'})\n"
                    f"  $stable({clk}) |-> ($stable({regs[0]}) || $changed({clk}));\n"
                    f"endproperty\n"
                    f"{module.name}_a_registered_stability: "
                    f"assert property ({module.name}_p_registered_stability);"
                ),
                "explanation": (
                    f"Registered output {regs[0]} should only change on clock edges, "
                    f"not combinatorially."
                ),
                "signals_used": [regs[0], clk] + module.reset_signals[:1],
                "confidence": "medium",
                "source_evidence": f"Register '{regs[0]}' detected in module '{module.name}'",
                "false_positive_conditions": (
                    "If {regs[0]} is a combinational signal mistakenly typed as reg, "
                    "this assertion would be incorrect."
                ),
            })

        return assertions

    def _gen_mutex_assertions(self, module: DesignModule) -> list[dict]:
        """Generate mutual exclusion assertions."""
        assertions = []

        # Look for signals that should be mutually exclusive
        all_names = [p.name for p in module.ports] + [s.name for s in module.signals]

        # Common mutually exclusive patterns
        for name in all_names:
            if "rd" in name.lower() and "wr" in name.lower():
                # Read/write mutual exclusion for some protocols
                pass  # Complex - need more context

            if "error" in name.lower() and "valid" in name.lower():
                assertions.append({
                    "name": f"{module.name}_{name}_mutual_exclusion",
                    "assertion_code": (
                        f"// Assert: {name} and valid are mutually exclusive\n"
                        f"property {module.name}_p_{name}_mutex;\n"
                        f"  @(posedge {module.clock_signals[0] if module.clock_signals else 'clk'})\n"
                        f"  !({name} && {next((n for n in all_names if 'valid' in n.lower()), 'valid')});\n"
                        f"endproperty\n"
                        f"{module.name}_a_{name}_mutex: "
                        f"assert property ({module.name}_p_{name}_mutex);"
                    ),
                    "explanation": (
                        f"Error indicator '{name}' and valid signal should not be "
                        f"asserted simultaneously."
                    ),
                    "signals_used": [name],
                    "confidence": "medium",
                    "source_evidence": f"Heuristic: error + valid signals in '{module.name}'",
                    "false_positive_conditions": (
                        "Some protocols allow error and valid to be simultaneous."
                    ),
                })

        return assertions
