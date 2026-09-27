"""Verification Planner - Automatically generates verification plans from RTL analysis."""

from typing import Optional
from ..rtl_parser.parser import DesignModule, SignalDirection


class VerificationPlanGenerator:
    """Generates comprehensive verification plans from RTL analysis.

    Each generated item is traceable back to RTL behavior or explicit requirements.
    Items are labeled as [RTL-derived], [Specification-derived], or [AI-inferred].
    """

    def generate(self, modules: list[DesignModule],
                 specification: str = "") -> dict:
        """Generate a verification plan from parsed RTL modules."""
        items = []

        for module in modules:
            items.extend(self._plan_module_functionality(module))
            items.extend(self._plan_port_behavior(module))
            items.extend(self._plan_fsm_verification(module))
            items.extend(self._plan_clock_reset(module))
            items.extend(self._plan_protocol(module))
            items.extend(self._plan_corner_cases(module))
            items.extend(self._plan_assertions(module))
            items.extend(self._plan_coverage(module))

        # Add specification-derived items if spec provided
        if specification:
            items.extend(self._plan_from_specification(specification, modules))

        # Prioritize items
        items = self._prioritize_items(items)

        return {
            "items": items,
            "summary": self._generate_summary(items, modules),
            "traceability": self._build_traceability(items),
        }

    def _plan_module_functionality(self, module: DesignModule) -> list:
        """Plan verification of core module functionality."""
        items = []

        # Basic module instantiation test
        items.append({
            "id": f"vf_{module.name}_basic",
            "category": "functional",
            "title": f"Verify {module.name} basic functionality",
            "description": f"Verify that {module.name} operates correctly under normal conditions with all inputs at valid values.",
            "source_type": "rtl-derived",
            "source_reference": {
                "module": module.name,
                "lines": f"{module.start_line}-{module.end_line}",
            },
            "priority": 10,
            "status": "pending",
            "coverage_points": [
                f"All output ports have valid values under normal operation",
                f"Module produces expected results for known inputs",
            ],
        })

        # Parameter variation
        if module.parameters:
            items.append({
                "id": f"vf_{module.name}_params",
                "category": "parametric",
                "title": f"Verify {module.name} with different parameter values",
                "description": f"Test {module.name} with each parameter at min, default, and max values. Parameters: {[p.name for p in module.parameters]}",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "parameters": [p.name for p in module.parameters],
                },
                "priority": 8,
                "status": "pending",
                "coverage_points": [
                    f"Each parameter combination tested: {[p.name for p in module.parameters]}",
                ],
            })

        return items

    def _plan_port_behavior(self, module: DesignModule) -> list:
        """Plan verification of port behavior."""
        items = []

        for port in module.ports:
            if port.direction in [SignalDirection.INPUT, SignalDirection.INOUT]:
                # Test each input at boundary values
                items.append({
                    "id": f"vf_{module.name}_port_{port.name}",
                    "category": "boundary",
                    "title": f"Verify {module.name}.{port.name} boundary values",
                    "description": f"Test input port {port.name} ({port.width or '1-bit'}) at boundary values: all-zeros, all-ones, alternating patterns.",
                    "source_type": "rtl-derived",
                    "source_reference": {
                        "module": module.name,
                        "port": port.name,
                        "line": port.line,
                    },
                    "priority": 7,
                    "status": "pending",
                    "coverage_points": [
                        f"Port {port.name} tested at 0",
                        f"Port {port.name} tested at max value",
                        f"Port {port.name} tested at alternating bits",
                    ],
                })

            if port.direction == SignalDirection.OUTPUT:
                items.append({
                    "id": f"vf_{module.name}_output_{port.name}",
                    "category": "output_check",
                    "title": f"Verify {module.name}.{port.name} output behavior",
                    "description": f"Verify output port {port.name} responds correctly to input stimuli.",
                    "source_type": "rtl-derived",
                    "source_reference": {
                        "module": module.name,
                        "port": port.name,
                        "line": port.line,
                    },
                    "priority": 6,
                    "status": "pending",
                    "coverage_points": [
                        f"Output {port.name} has correct values for known input combinations",
                    ],
                })

        return items

    def _plan_fsm_verification(self, module: DesignModule) -> list:
        """Plan FSM-specific verification."""
        items = []

        for fsm in module.fsm_info:
            states = [s.name for s in fsm.states]
            num_transitions = len(fsm.transitions)

            # State enumeration
            items.append({
                "id": f"vf_{module.name}_fsm_{fsm.name}_states",
                "category": "fsm",
                "title": f"Enumerate all states in {fsm.name}",
                "description": f"Verify FSM '{fsm.name}' can reach and operate in all {len(states)} states: {states}",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "fsm": fsm.name,
                    "states": states,
                },
                "priority": 10,
                "status": "pending",
                "coverage_points": [
                    f"FSM reaches state {s}" for s in states
                ],
            })

            # Transition coverage
            items.append({
                "id": f"vf_{module.name}_fsm_{fsm.name}_transitions",
                "category": "fsm",
                "title": f"Cover all transitions in {fsm.name}",
                "description": f"Exercise all {num_transitions} state transitions in FSM '{fsm.name}'",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "fsm": fsm.name,
                    "transitions": [
                        {"from": t.from_state, "to": t.to_state}
                        for t in fsm.transitions
                    ],
                },
                "priority": 10,
                "status": "pending",
                "coverage_points": [
                    f"Transition {t.from_state} -> {t.to_state} covered"
                    for t in fsm.transitions
                ],
            })

            # Reset from each state
            items.append({
                "id": f"vf_{module.name}_fsm_{fsm.name}_reset",
                "category": "reset",
                "title": f"Verify reset behavior from each state in {fsm.name}",
                "description": f"Assert reset while FSM is in each state, verify it returns to initial state.",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "fsm": fsm.name,
                },
                "priority": 9,
                "status": "pending",
                "coverage_points": [
                    f"Reset from state {s} returns to initial state" for s in states
                ],
            })

            # Invalid state recovery
            items.append({
                "id": f"vf_{module.name}_fsm_{fsm.name}_invalid",
                "category": "error",
                "title": f"Verify invalid state recovery in {fsm.name}",
                "description": f"Force FSM to invalid state encoding, verify it recovers via reset.",
                "source_type": "ai-inferred",
                "source_reference": {
                    "module": module.name,
                    "fsm": fsm.name,
                },
                "priority": 8,
                "status": "pending",
                "coverage_points": [
                    "FSM recovers from invalid state encoding via reset",
                ],
            })

        return items

    def _plan_clock_reset(self, module: DesignModule) -> list:
        """Plan clock and reset verification."""
        items = []

        clocks = module.clock_signals
        resets = module.reset_signals

        if clocks:
            items.append({
                "id": f"vf_{module.name}_clock",
                "category": "clock",
                "title": f"Verify {module.name} clock behavior",
                "description": f"Verify module operates correctly at target clock frequency. Clock signals: {clocks}",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "clocks": clocks,
                },
                "priority": 9,
                "status": "pending",
                "coverage_points": [
                    "Normal clock operation verified",
                ],
            })

        if resets:
            items.append({
                "id": f"vf_{module.name}_reset",
                "category": "reset",
                "title": f"Verify {module.name} reset behavior",
                "description": f"Verify all reset scenarios. Reset signals: {resets}. Check async vs sync reset behavior.",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "resets": resets,
                },
                "priority": 10,
                "status": "pending",
                "coverage_points": [
                    "Reset assertion clears all registers",
                    "Reset de-assertion starts normal operation",
                    "Reset during active operation handled correctly",
                ],
            })

        return items

    def _plan_protocol(self, module: DesignModule) -> list:
        """Plan protocol-specific verification."""
        items = []
        protocol = module.metadata.get("protocol", "")

        if protocol == "valid_ready_handshake":
            items.append({
                "id": f"vf_{module.name}_handshake",
                "category": "protocol",
                "title": f"Verify {module.name} valid/ready handshake",
                "description": "Verify correct operation of valid/ready handshake protocol including backpressure.",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "protocol": protocol,
                },
                "priority": 10,
                "status": "pending",
                "coverage_points": [
                    "Data transfer with valid=1, ready=1",
                    "Backpressure: valid=1, ready=0 (data held)",
                    "No transfer: valid=0",
                    "Data stability during valid assertion",
                    "Multiple transfers in sequence",
                    "Reset during handshake",
                ],
            })

        if module.metadata.get("is_fifo"):
            items.append({
                "id": f"vf_{module.name}_fifo",
                "category": "protocol",
                "title": f"Verify {module.name} FIFO behavior",
                "description": "Verify FIFO full, empty, overflow, underflow, and simultaneous read/write.",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "protocol": "fifo",
                },
                "priority": 10,
                "status": "pending",
                "coverage_points": [
                    "Write when FIFO not full",
                    "Read when FIFO not empty",
                    "Write when FIFO full (overflow protection)",
                    "Read when FIFO empty (underflow protection)",
                    "Simultaneous read and write",
                    "FIFO full and empty transitions",
                    "Reset clears FIFO",
                    "FIFO depth correctly tracked",
                ],
            })

        if protocol in ["axi_like", "simple_bus"]:
            items.append({
                "id": f"vf_{module.name}_bus",
                "category": "protocol",
                "title": f"Verify {module.name} bus protocol",
                "description": f"Verify bus protocol compliance. Protocol: {protocol}",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "protocol": protocol,
                },
                "priority": 9,
                "status": "pending",
                "coverage_points": [
                    "Single beat transfer",
                    "Burst transfer (if applicable)",
                    "Address decoding",
                    "Data integrity",
                ],
            })

        return items

    def _plan_corner_cases(self, module: DesignModule) -> list:
        """Plan corner case verification."""
        items = []

        corner_cases = module.metadata.get("corner_cases", [])
        for cc in corner_cases:
            items.append({
                "id": f"vf_{module.name}_corner_{cc['type']}",
                "category": "corner_case",
                "title": f"Corner cases: {cc['description']}",
                "description": f"Test corner cases for {module.name}: " + "; ".join(cc["cases"]),
                "source_type": "ai-inferred",
                "source_reference": {
                    "module": module.name,
                    "corner_type": cc["type"],
                },
                "priority": 8,
                "status": "pending",
                "coverage_points": cc["cases"],
            })

        return items

    def _plan_assertions(self, module: DesignModule) -> list:
        """Plan assertion-based verification."""
        items = []

        if not module.has_assertions:
            items.append({
                "id": f"vf_{module.name}_assertions",
                "category": "assertions",
                "title": f"Generate assertions for {module.name}",
                "description": f"Module {module.name} has no assertions. Generate SVA assertions for key properties.",
                "source_type": "ai-inferred",
                "source_reference": {
                    "module": module.name,
                },
                "priority": 8,
                "status": "pending",
                "coverage_points": [
                    "Assertions generated for handshake correctness",
                    "Assertions generated for FSM transitions",
                    "Assertions generated for reset behavior",
                ],
            })
        else:
            items.append({
                "id": f"vf_{module.name}_assertions_check",
                "category": "assertions",
                "title": f"Verify existing assertions in {module.name}",
                "description": f"Module has {len(module.assertions)} existing assertions. Verify they are correct and cover key properties.",
                "source_type": "rtl-derived",
                "source_reference": {
                    "module": module.name,
                    "num_assertions": len(module.assertions),
                },
                "priority": 7,
                "status": "pending",
                "coverage_points": [
                    f"Assertion '{a.name}' passes" for a in module.assertions
                ],
            })

        return items

    def _plan_coverage(self, module: DesignModule) -> list:
        """Plan coverage targets."""
        items = []

        items.append({
            "id": f"vf_{module.name}_line_cov",
            "category": "coverage",
            "title": f"Achieve line coverage for {module.name}",
            "description": f"Target 95%+ line coverage for {module.name}.",
            "source_type": "rtl-derived",
            "source_reference": {"module": module.name},
            "priority": 9,
            "status": "pending",
            "coverage_points": [
                "Line coverage >= 95%",
            ],
        })

        items.append({
            "id": f"vf_{module.name}_branch_cov",
            "category": "coverage",
            "title": f"Achieve branch coverage for {module.name}",
            "description": f"Target 90%+ branch coverage for {module.name}.",
            "source_type": "rtl-derived",
            "source_reference": {"module": module.name},
            "priority": 8,
            "status": "pending",
            "coverage_points": [
                "Branch coverage >= 90%",
            ],
        })

        if module.has_fsm:
            items.append({
                "id": f"vf_{module.name}_fsm_cov",
                "category": "coverage",
                "title": f"Achieve FSM coverage for {module.name}",
                "description": f"Target 100% FSM state and transition coverage for {module.name}.",
                "source_type": "rtl-derived",
                "source_reference": {"module": module.name},
                "priority": 10,
                "status": "pending",
                "coverage_points": [
                    "All FSM states reached",
                    "All FSM transitions covered",
                    "FSM arc coverage >= 100%",
                ],
            })

        return items

    def _plan_from_specification(self, spec: str,
                                 modules: list[DesignModule]) -> list:
        """Extract verification items from specification text."""
        items = []

        # Simple keyword-based extraction
        spec_lower = spec.lower()
        keywords = {
            "reset": ("reset", "Verify reset behavior as specified"),
            "overflow": ("overflow", "Verify overflow handling as specified"),
            "underflow": ("underflow", "Verify underflow handling as specified"),
            "timeout": ("timeout", "Verify timeout behavior as specified"),
            "error": ("error", "Verify error handling as specified"),
            "interrupt": ("interrupt", "Verify interrupt behavior as specified"),
            "dma": ("dma", "Verify DMA transfer as specified"),
            "pipeline": ("pipeline", "Verify pipeline behavior as specified"),
        }

        for keyword, (category, desc) in keywords.items():
            if keyword in spec_lower:
                items.append({
                    "id": f"vf_spec_{category}",
                    "category": category,
                    "title": desc,
                    "description": f"Specification mentions {keyword}. Verify behavior matches specification.",
                    "source_type": "spec-derived",
                    "source_reference": {"keyword": keyword},
                    "priority": 9,
                    "status": "pending",
                    "coverage_points": [
                        f"Spec requirement for {keyword} is verified",
                    ],
                })

        return items

    def _prioritize_items(self, items: list) -> list:
        """Sort and prioritize verification items."""
        # Sort by priority (higher = more important)
        items.sort(key=lambda x: (-x.get("priority", 5), x.get("category", "")))
        return items

    def _generate_summary(self, items: list,
                          modules: list[DesignModule]) -> dict:
        """Generate a summary of the verification plan."""
        categories = {}
        source_counts = {"rtl-derived": 0, "spec-derived": 0, "ai-inferred": 0}

        for item in items:
            cat = item.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            src = item.get("source_type", "unknown")
            if src in source_counts:
                source_counts[src] += 1

        return {
            "total_items": len(items),
            "categories": categories,
            "source_breakdown": source_counts,
            "modules_analyzed": len(modules),
            "total_fsm": sum(len(m.fsm_info) for m in modules),
            "total_assertions": sum(len(m.assertions) for m in modules),
            "estimated_test_count": len(items) * 2,  # rough estimate
        }

    def _build_traceability(self, items: list) -> dict:
        """Build traceability matrix."""
        traceability = {
            "module_to_items": {},
            "category_to_items": {},
            "source_to_items": {},
        }

        for item in items:
            ref = item.get("source_reference", {})
            module = ref.get("module", "unknown")
            if module not in traceability["module_to_items"]:
                traceability["module_to_items"][module] = []
            traceability["module_to_items"][module].append(item["id"])

            cat = item.get("category", "unknown")
            if cat not in traceability["category_to_items"]:
                traceability["category_to_items"][cat] = []
            traceability["category_to_items"][cat].append(item["id"])

            src = item.get("source_type", "unknown")
            if src not in traceability["source_to_items"]:
                traceability["source_to_items"][src] = []
            traceability["source_to_items"][src].append(item["id"])

        return traceability
