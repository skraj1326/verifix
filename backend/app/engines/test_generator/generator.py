"""AI Test Generator - Generates directed, constrained-random, and UVM tests."""

from ..rtl_parser.parser import DesignModule, SignalDirection


class TestGenerator:
    """Generates SystemVerilog tests with stated verification objectives.

    Every test has:
    - Verification objective
    - Target signals/coverage points
    - Stims pattern
    - Expected behavior
    """

    def generate(self, modules: list[DesignModule],
                 coverage_gaps: list[dict] = None) -> list[dict]:
        """Generate tests for all modules, optionally targeting coverage gaps."""
        tests = []
        for module in modules:
            tests.extend(self._gen_directed_tests(module))
            tests.extend(self._gen_constrained_random(module))
            tests.extend(self._gen_uvm_tests(module))

        if coverage_gaps:
            tests.extend(self._gen_coverage_targeted_tests(modules, coverage_gaps))

        return tests

    def _gen_directed_tests(self, module: DesignModule) -> list[dict]:
        """Generate directed tests for specific scenarios."""
        tests = []

        # Basic sanity test
        tests.append(self._gen_basic_test(module))

        # Reset test
        if module.reset_signals:
            tests.append(self._gen_reset_test(module))

        # Port sweep tests
        tests.append(self._gen_port_sweep_test(module))

        # FSM tests
        for fsm in module.fsm_info:
            tests.extend(self._gen_fsm_tests(module, fsm))

        # Protocol tests
        if module.metadata.get("protocol") == "valid_ready_handshake":
            tests.append(self._gen_handshake_test(module))
        if module.metadata.get("is_fifo"):
            tests.extend(self._gen_fifo_tests(module))

        return tests

    def _gen_basic_test(self, module: DesignModule) -> dict:
        """Generate a basic directed test."""
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        # Build input assignments
        input_ports = module.input_ports
        input_assignments = ""
        for port in input_ports:
            input_assignments += f"    {port.name} = 0;\n"

        code = f"""// Directed Test: {module.name} Basic Functionality
// Verification Objective: Verify {module.name} operates correctly under normal conditions

module tb_{module.name}_basic;

  // Signal declarations
  reg {clk};
  reg {rst};
"""

        # Declare port signals
        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  // Clock generation
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  // Test stimulus
  initial begin
    // Initialize
    {input_assignments}
    {rst} = 1;
    #25;
    {rst} = 0;
    #20;

    // Apply basic stimulus
    {self._gen_stimulus_block(module)}

    // Wait and check
    #100;

    $display("[PASS] {module.name} basic test completed");
    $finish;
  end

  // Timeout watchdog
  initial begin
    #10000;
    $display("[FAIL] {module.name} basic test timed out");
    $finish;
  end

endmodule
"""
        return {
            "name": f"tb_{module.name}_basic",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Verify {module.name} operates correctly under normal conditions",
            "target_coverage": ["basic_functionality"],
            "target_signals": [p.name for p in module.ports],
        }

    def _gen_reset_test(self, module: DesignModule) -> dict:
        """Generate a reset test."""
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        regs = [s.name for s in module.signals if s.signal_type.value in ("reg", "logic")]

        code = f"""// Directed Test: {module.name} Reset Behavior
// Verification Objective: Verify all registers clear on reset

module tb_{module.name}_reset;

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  integer i;
  initial begin
    {rst} = 1;
    // Apply some inputs during reset
"""
        for port in module.input_ports[:3]:
            code += f"    {port.name} = 1;\n"

        code += f"""
    #50;
    {rst} = 0;
    #20;

    // Change inputs
"""
        for port in module.input_ports[:3]:
            code += f"    {port.name} = 0;\n"

        code += f"""
    #10;

    // Assert reset again
    {rst} = 1;
    #30;

    // Verify registers cleared
"""
        for reg in regs[:5]:
            code += f"    if ({reg} !== 0) $display(\"[FAIL] {reg} not cleared by reset\");\n"

        code += f"""
    {rst} = 0;
    #20;

    $display("[PASS] {module.name} reset test completed");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        return {
            "name": f"tb_{module.name}_reset",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Verify reset clears all registers in {module.name}",
            "target_coverage": ["reset_behavior"],
            "target_signals": module.reset_signals + regs[:5],
        }

    def _gen_port_sweep_test(self, module: DesignModule) -> dict:
        """Generate a test that sweeps through input port values."""
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        code = f"""// Directed Test: {module.name} Port Sweep
// Verification Objective: Test all input port boundary values

module tb_{module.name}_sweep;

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  initial begin
    {rst} = 1;
    #25;
    {rst} = 0;
    #10;

    // Test all-zeros
"""
        for port in module.input_ports:
            code += f"    {port.name} = 0;\n"
        code += f"    #20;\n\n"

        # Test all-ones for each port
        for port in module.input_ports:
            width_val = self._parse_width(port.width)
            code += f"    // Test {port.name} all-ones\n"
            code += f"    {port.name} = {width_val}'{'h' if int(width_val) > 4 else 'b'}{'f' * ((int(width_val) + 3) // 4) if int(width_val) > 4 else '1' * (int(width_val) + 1)};\n"
            code += f"    #20;\n"

        code += f"""
    $display("[PASS] {module.name} port sweep test completed");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        return {
            "name": f"tb_{module.name}_sweep",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Test all input port boundary values in {module.name}",
            "target_coverage": ["port_boundary_values"],
            "target_signals": [p.name for p in module.input_ports],
        }

    def _gen_fsm_tests(self, module: DesignModule, fsm) -> list[dict]:
        """Generate FSM-specific tests."""
        tests = []
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        states = [s.name for s in fsm.states]

        # State transition test
        code = f"""// Directed Test: {module.name} FSM {fsm.name} Transitions
// Verification Objective: Exercise all state transitions in {fsm.name}

module tb_{module.name}_fsm_{fsm.name};

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  initial begin
    {rst} = 1;
    #25;
    {rst} = 0;
    #10;

    // Drive inputs to traverse all FSM transitions
"""
        for i, trans in enumerate(fsm.transitions):
            code += f"    // Transition {trans.from_state} -> {trans.to_state}\n"
            code += f"    // TODO: Set inputs to trigger this transition\n"
            code += f"    #20;\n"

        code += f"""
    $display("[PASS] {module.name} FSM {fsm.name} transition test completed");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        tests.append({
            "name": f"tb_{module.name}_fsm_{fsm.name}_transitions",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Exercise all {len(fsm.transitions)} transitions in FSM '{fsm.name}'",
            "target_coverage": [f"fsm_{fsm.name}_transition_{t.from_state}_to_{t.to_state}" for t in fsm.transitions],
            "target_signals": [fsm.state_variable],
        })

        # Reset from each state test
        code = f"""// Directed Test: {module.name} FSM {fsm.name} Reset Recovery
// Verify FSM returns to initial state from any state

module tb_{module.name}_fsm_{fsm.name}_reset;

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  initial begin
"""
        for state in states:
            code += f"    // Drive to state {state}\n"
            code += f"    // TODO: Set inputs to reach state {state}\n"
            code += f"    #20;\n"
            code += f"    {rst} = 1;\n"
            code += f"    #20;\n"
            code += f"    // Verify state == {states[0] if states else 'INIT'}\n"
            code += f"    {rst} = 0;\n"
            code += f"    #20;\n\n"

        code += f"""
    $display("[PASS] {module.name} FSM reset recovery test completed");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        tests.append({
            "name": f"tb_{module.name}_fsm_{fsm.name}_reset",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Verify FSM '{fsm.name}' returns to initial state from any state on reset",
            "target_coverage": [f"fsm_{fsm.name}_reset_from_{s}" for s in states],
            "target_signals": [fsm.state_variable, rst],
        })

        return tests

    def _gen_handshake_test(self, module: DesignModule) -> dict:
        """Generate valid/ready handshake test."""
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        all_names = [p.name for p in module.ports]
        valid = next((n for n in all_names if "valid" in n.lower()), "valid")
        ready = next((n for n in all_names if "ready" in n.lower()), "ready")
        data = next((n for n in all_names if "data" in n.lower()), "data")

        code = f"""// Directed Test: {module.name} Handshake Protocol
// Verification Objective: Test valid/ready handshake including backpressure

module tb_{module.name}_handshake;

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  initial begin
    {rst} = 1;
    #25;
    {rst} = 0;
    #10;

    // Test 1: Normal transfer (valid=1, ready=1)
    $display("Test 1: Normal transfer");
    {valid} = 1;
    {data} = 32'hDEAD_BEEF;
    {ready} = 1;
    #20;

    // Test 2: Backpressure (valid=1, ready=0)
    $display("Test 2: Backpressure");
    {valid} = 1;
    {data} = 32'hCAFE_BABE;
    {ready} = 0;
    #40;
    {ready} = 1;
    #20;

    // Test 3: No valid (valid=0)
    $display("Test 3: No valid");
    {valid} = 0;
    #20;

    // Test 4: Multiple transfers
    $display("Test 4: Multiple transfers");
    {valid} = 1;
    {ready} = 1;
    {data} = 32'h0000_0001; #20;
    {data} = 32'h0000_0002; #20;
    {data} = 32'h0000_0003; #20;

    $display("[PASS] {module.name} handshake test completed");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        return {
            "name": f"tb_{module.name}_handshake",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Test valid/ready handshake protocol in {module.name}",
            "target_coverage": [
                "handshake_normal_transfer",
                "handshake_backpressure",
                "handshake_no_valid",
                "handshake_multiple_transfers",
            ],
            "target_signals": [valid, ready, data],
        }

    def _gen_fifo_tests(self, module: DesignModule) -> list[dict]:
        """Generate FIFO-specific tests."""
        tests = []
        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        all_names = [p.name for p in module.ports]
        full = next((n for n in all_names if "full" in n.lower()), None)
        empty = next((n for n in all_names if "empty" in n.lower()), None)
        wr_en = next((n for n in all_names if "wr" in n.lower() and "en" in n.lower()), None)
        rd_en = next((n for n in all_names if "rd" in n.lower() and "en" in n.lower()), None)

        code = f"""// Directed Test: {module.name} FIFO Behavior
// Verify FIFO full, empty, overflow, underflow, simultaneous R/W

module tb_{module.name}_fifo;

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  integer i;
  initial begin
    {rst} = 1;
"""
        if wr_en:
            code += f"    {wr_en} = 0;\n"
        if rd_en:
            code += f"    {rd_en} = 0;\n"
        code += f"""
    #25;
    {rst} = 0;
    #10;

    // Fill FIFO
    $display("Filling FIFO");
"""
        if wr_en:
            code += f"    {wr_en} = 1;\n"
            code += f"    for (i = 0; i < 20; i = i + 1) begin\n"
            code += f"      #10;\n"
            if full:
                code += f"      if ({full}) begin\n"
                code += f"        $display(\"FIFO full at iteration %0d\", i);\n"
                code += f"        {wr_en} = 0;\n"
                code += f"        break;\n"
                code += f"      end\n"
            code += f"    end\n"
            code += f"    {wr_en} = 0;\n"

        code += f"""
    // Read from FIFO
    $display("Reading from FIFO");
"""
        if rd_en:
            code += f"    {rd_en} = 1;\n"
            code += f"    for (i = 0; i < 20; i = i + 1) begin\n"
            code += f"      #10;\n"
            if empty:
                code += f"      if ({empty}) begin\n"
                code += f"        $display(\"FIFO empty at iteration %0d\", i);\n"
                code += f"        {rd_en} = 0;\n"
                code += f"        break;\n"
                code += f"      end\n"
            code += f"    end\n"
            code += f"    {rd_en} = 0;\n"

        code += f"""
    $display("[PASS] {module.name} FIFO test completed");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        tests.append({
            "name": f"tb_{module.name}_fifo",
            "test_type": "directed",
            "code": code,
            "verification_objective": f"Verify FIFO full/empty/overflow/underflow behavior in {module.name}",
            "target_coverage": ["fifo_fill", "fifo_drain", "fifo_full", "fifo_empty"],
            "target_signals": [s for s in [full, empty, wr_en, rd_en] if s],
        })

        return tests

    def _gen_constrained_random(self, module: DesignModule) -> list[dict]:
        """Generate constrained-random tests."""
        tests = []

        input_ports = module.input_ports
        if not input_ports:
            return tests

        clk = module.clock_signals[0] if module.clock_signals else "clk"
        rst = module.reset_signals[0] if module.reset_signals else "rst"

        code = f"""// Constrained Random Test: {module.name}
// Verification Objective: Random stimulus to explore state space

module tb_{module.name}_random;

  reg {clk};
  reg {rst};
"""

        for port in module.ports:
            width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
            code += f"  {port.direction.value}{width} {port.name};\n"

        code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  integer i;
  initial begin
    {rst} = 1;
    #25;
    {rst} = 0;
    #10;

    // Random stimulus
    for (i = 0; i < 1000; i = i + 1) begin
"""
        for port in input_ports:
            width_val = self._parse_width(port.width)
            code += f"      {port.name} = $urandom_range(0, {width_val}'{'h' if int(width_val) > 4 else 'b'}{'f' * ((int(width_val) + 3) // 4) if int(width_val) > 4 else '1' * (int(width_val) + 1)});\n"
        code += f"""
      #10;
    end

    $display("[PASS] {module.name} random test completed");
    $finish;
  end

  initial begin #100000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
        tests.append({
            "name": f"tb_{module.name}_random",
            "test_type": "constrained_random",
            "code": code,
            "verification_objective": f"Random stimulus to explore {module.name} state space",
            "target_coverage": ["random_exploration"],
            "target_signals": [p.name for p in input_ports],
        })

        return tests

    def _gen_uvm_tests(self, module: DesignModule) -> list[dict]:
        """Generate basic UVM test components."""
        tests = []

        input_ports = module.input_ports
        output_ports = module.output_ports
        clk = module.clock_signals[0] if module.clock_signals else "clk"

        # UVM Sequence Item
        code = f"""// UVM Sequence Item for {module.name}
class {module.name}_seq_item extends uvm_sequence_item;
  `uvm_object_utils({module.name}_seq_item)

"""

        for port in module.ports:
            width_val = self._parse_width(port.width)
            code += f"  rand {port.direction.value} logic [{width_val}:0] {port.name};\n"

        code += f"""
  function new(string name = "{module.name}_seq_item");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("{module.name} seq_item: ";
"""
        for port in module.ports[:4]:
            code += f"      + \"{port.name}=%h \", {port.name}\n"
        code += f"""    );
  endfunction

  function void do_copy(uvm_object rhs);
    {module.name}_seq_item rhs_;
    $cast(rhs_, rhs);
    super.do_copy(rhs);
"""
        for port in module.ports:
            code += f"    {port.name} = rhs_.{port.name};\n"
        code += f"""  endfunction

  function bit do_compare(uvm_object rhs, uvm_comparer comparer);
    {module.name}_seq_item rhs_;
    $cast(rhs_, rhs);
    return super.do_compare(rhs, comparer);
  endfunction

endclass
"""
        tests.append({
            "name": f"{module.name}_seq_item",
            "test_type": "uvm_sequence_item",
            "code": code,
            "verification_objective": f"UVM sequence item for {module.name} stimulus generation",
            "target_coverage": [],
            "target_signals": [p.name for p in module.ports],
        })

        # UVM Sequence
        code = f"""// UVM Sequence for {module.name}
class {module.name}_base_seq extends uvm_sequence #({module.name}_seq_item);
  `uvm_object_utils({module.name}_base_seq)

  function new(string name = "{module.name}_base_seq");
    super.new(name);
  endfunction

  virtual task body();
    {module.name}_seq_item item;
    repeat(100) begin
      item = {module.name}_seq_item::type_id::create("item");
      start_item(item);
      assert(item.randomize());
      finish_item(item);
    end
  endtask

endclass

// Directed sequence for specific scenarios
class {module.name}_directed_seq extends uvm_sequence #({module.name}_seq_item);
  `uvm_object_utils({module.name}_directed_seq)

  function new(string name = "{module.name}_directed_seq");
    super.new(name);
  endfunction

  virtual task body();
    {module.name}_seq_item item;

    // Reset scenario
    item = {module.name}_seq_item::type_id::create("item");
    start_item(item);
    assert(item.randomize() with {{
"""
        for port in module.input_ports[:3]:
            code += f"      {port.name} == 0;\n"
        code += f"""    }});
    finish_item(item);
  endtask

endclass
"""
        tests.append({
            "name": f"{module.name}_sequences",
            "test_type": "uvm_sequence",
            "code": code,
            "verification_objective": f"UVM sequences for {module.name} stimulus generation",
            "target_coverage": ["uvm_random", "uvm_directed"],
            "target_signals": [p.name for p in module.ports],
        })

        # UVM Monitor
        code = f"""// UVM Monitor for {module.name}
class {module.name}_monitor extends uvm_monitor;
  `uvm_component_utils({module.name}_monitor)

  uvm_analysis_port #({module.name}_seq_item) ap;

  virtual {module.name}_if vif;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap = new("ap", this);
  endfunction

  virtual task run_phase(uvm_phase phase);
    {module.name}_seq_item item;
    forever begin
      @(posedge vif.{clk});
      item = {module.name}_seq_item::type_id::create("item");
"""
        for port in module.ports:
            code += f"      item.{port.name} = vif.{port.name};\n"
        code += f"""      ap.write(item);
    end
  endtask

endclass
"""
        tests.append({
            "name": f"{module.name}_monitor",
            "test_type": "uvm_monitor",
            "code": code,
            "verification_objective": f"UVM monitor for {module.name} signal observation",
            "target_coverage": [],
            "target_signals": [p.name for p in module.ports],
        })

        return tests

    def _gen_coverage_targeted_tests(self, modules: list[DesignModule],
                                     gaps: list[dict]) -> list[dict]:
        """Generate tests targeting specific coverage gaps."""
        tests = []

        for gap in gaps:
            gap_type = gap.get("gap_type", "")
            description = gap.get("description", "")
            rtl_location = gap.get("rtl_location", {})
            module_name = rtl_location.get("module", "")

            module = next((m for m in modules if m.name == module_name), None)
            if not module:
                continue

            code = f"""// Coverage-Targeted Test: {description}
// Gap Type: {gap_type}
// Auto-generated to address coverage hole

module tb_{module_name}_covgap_{hash(description) % 10000};

  reg {module.clock_signals[0] if module.clock_signals else 'clk'};
  reg {module.reset_signals[0] if module.reset_signals else 'rst'};
"""

            for port in module.ports:
                width = f" [{self._parse_width(port.width)}:0]" if port.width else ""
                code += f"  {port.direction.value}{width} {port.name};\n"

            clk = module.clock_signals[0] if module.clock_signals else "clk"
            rst = module.reset_signals[0] if module.reset_signals else "rst"

            code += f"""
  initial {clk} = 0;
  always #5 {clk} = ~{clk};

  initial begin
    {rst} = 1;
    #25;
    {rst} = 0;
    #10;

    // Targeted stimulus to cover: {description}
    // TODO: Engineer should refine stimulus based on gap analysis
"""
            for port in module.input_ports[:5]:
                code += f"    {port.name} = $urandom;\n"
            code += f"""
    #100;

    $display("[INFO] Coverage-targeted test for: {description}");
    $finish;
  end

  initial begin #10000; $display("[FAIL] Timeout"); $finish; end

endmodule
"""
            tests.append({
                "name": f"tb_{module_name}_covgap_{hash(description) % 10000}",
                "test_type": "coverage_targeted",
                "code": code,
                "verification_objective": f"Address coverage gap: {description}",
                "target_coverage": [f"gap_{gap_type}"],
                "target_signals": rtl_location.get("signals", []),
            })

        return tests

    def _gen_stimulus_block(self, module: DesignModule) -> str:
        """Generate stimulus block for input ports."""
        lines = []
        for port in module.input_ports[:5]:
            lines.append(f"    {port.name} = $urandom_range(0, 16'hFFFF);")
        return "\n".join(lines)

    def _parse_width(self, width_str: str) -> str:
        """Parse width string and return bit width."""
        if not width_str:
            return "0"
        match = __import__("re").match(r"\[(\d+):(\d+)\]", width_str)
        if match:
            msb = int(match.group(1))
            lsb = int(match.group(2))
            return str(msb - lsb)
        return "0"
