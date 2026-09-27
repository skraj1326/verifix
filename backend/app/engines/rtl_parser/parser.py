"""RTL Parser Engine - Extracts structural and behavioral information from SystemVerilog/Verilog."""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SignalDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"
    INTERNAL = "internal"


class SignalType(str, Enum):
    WIRE = "wire"
    REG = "reg"
    LOGIC = "logic"
    INTEGER = "integer"
    REAL = "real"
    BIT = "bit"
    TRI = "tri"
    WAND = "wand"
    WOR = "wor"
    UNKNOWN = "unknown"


class ModuleType(str, Enum):
    MODULE = "module"
    INTERFACE = "interface"
    PACKAGE = "package"
    PROGRAM = "program"


@dataclass
class Parameter:
    name: str
    default_value: str = ""
    type: str = "integer"
    line: int = 0


@dataclass
class Port:
    name: str
    direction: SignalDirection = SignalDirection.INPUT
    width: str = ""
    type: str = "logic"
    line: int = 0
    is_array: bool = False
    array_dims: list = field(default_factory=list)


@dataclass
class Signal:
    name: str
    signal_type: SignalType = SignalType.WIRE
    width: str = ""
    line: int = 0
    is_const: bool = False
    const_value: str = ""


@dataclass
class FSMState:
    name: str
    encoding: str = ""
    line: int = 0


@dataclass
class FSMTransition:
    from_state: str
    to_state: str
    condition: str = ""
    line: int = 0


@dataclass
class FSMInfo:
    name: str
    current_signal: str = ""
    states: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    state_variable: str = ""
    line: int = 0


@dataclass
class AlwaysBlock:
    sensitivity: str = ""  # "posedge clk", "comb", etc.
    clock: str = ""
    reset: str = ""
    reset_type: str = ""  # "async", "sync"
    statements: list = field(default_factory=list)
    line: int = 0


@dataclass
class ModuleInstance:
    module_name: str
    instance_name: str
    connections: dict = field(default_factory=dict)
    line: int = 0


@dataclass
class Assertion:
    name: str
    code: str
    assertion_type: str = "concurrent"  # immediate, concurrent, cover, assume
    line: int = 0


@dataclass
class Function:
    name: str
    return_type: str = ""
    arguments: list = field(default_factory=list)
    line: int = 0


@dataclass
class Task:
    name: str
    arguments: list = field(default_factory=list)
    line: int = 0


@dataclass
class DesignModule:
    name: str
    module_type: ModuleType = ModuleType.MODULE
    is_top: bool = False
    start_line: int = 0
    end_line: int = 0
    parameters: list = field(default_factory=list)
    ports: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    fsm_info: list = field(default_factory=list)
    instances: list = field(default_factory=list)
    always_blocks: list = field(default_factory=list)
    assigns: list = field(default_factory=list)
    assertions: list = field(default_factory=list)
    functions: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    includes: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def clock_signals(self) -> list:
        """Extract likely clock signals from always blocks."""
        clocks = set()
        for ab in self.always_blocks:
            if ab.clock:
                clocks.add(ab.clock)
        return list(clocks)

    @property
    def reset_signals(self) -> list:
        """Extract likely reset signals from always blocks."""
        resets = set()
        for ab in self.always_blocks:
            if ab.reset:
                resets.add(ab.reset)
        return list(resets)

    @property
    def input_ports(self) -> list:
        return [p for p in self.ports if p.direction == SignalDirection.INPUT]

    @property
    def output_ports(self) -> list:
        return [p for p in self.ports if p.direction == SignalDirection.OUTPUT]

    @property
    def has_fsm(self) -> bool:
        return len(self.fsm_info) > 0

    @property
    def has_assertions(self) -> bool:
        return len(self.assertions) > 0


class RTLParser:
    """Comprehensive SystemVerilog/Verilog parser for design analysis.

    This parser extracts structural and behavioral information from RTL code
    without requiring a full IEEE-compliant parser. It handles the most common
    patterns found in production RTL.
    """

    def __init__(self):
        self.modules: list[DesignModule] = []
        self._current_module: Optional[DesignModule] = None
        self._content: str = ""
        self._lines: list[str] = []
        self._defines: dict = {}
        self._includes: list[str] = []

    def parse(self, content: str, filename: str = "") -> list[DesignModule]:
        """Parse SystemVerilog/Verilog content and return extracted modules."""
        self._content = content
        self._lines = content.split("\n")
        self.modules = []
        self._parse_defines()
        self._parse_includes()
        self._parse_modules()
        self._analyze_fsms()
        self._analyze_protocols()
        self._identify_corner_cases()
        return self.modules

    def _parse_defines(self) -> None:
        """Extract `define macros."""
        for i, line in enumerate(self._lines):
            match = re.match(r'\s*`define\s+(\w+)\s*(.*)', line)
            if match:
                self._defines[match.group(1)] = match.group(2).strip()

    def _parse_includes(self) -> None:
        """Extract `include directives."""
        for line in self._lines:
            match = re.match(r'\s*`include\s+["<](.+)[">]', line)
            if match:
                self._includes.append(match.group(1))

    def _parse_module_header_multi(self, mod_type, multi_line: str):
        """Parse multi-line module header with nested parentheses in port widths."""
        import re
        keyword = mod_type.value
        # Pattern: keyword name #(params) (ports)
        # Handle nested parens in port declarations like $clog2(DEPTH)
        pattern = rf'\s*{keyword}\s+(\w+)'
        match = re.match(pattern, multi_line)
        if not match:
            return None
        
        module_name = match.group(1)
        rest = multi_line[match.end():].strip()
        
        # Extract parameters if present
        params_str = ""
        if rest.startswith('#'):
            # Find matching parens for parameter list
            depth = 0
            end_idx = 0
            for idx, ch in enumerate(rest):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        end_idx = idx
                        break
            if depth == 0 and end_idx > 1:  # end_idx > 1 to have content
                params_str = rest[2:end_idx].strip()  # Skip '#('
                rest = rest[end_idx+1:].strip()
        
        # Extract ports - find the port list in parentheses
        ports_str = ""
        if rest.startswith('('):
            depth = 0
            end_idx = 0
            for idx, ch in enumerate(rest):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        end_idx = idx
                        break
            if depth == 0 and end_idx > 0:
                ports_str = rest[1:end_idx].strip()
        
        # Create a mock match object compatible with regex match groups
        # group(1) = name, group(3) = params, group(4) = ports
        class MockMatch:
            def __init__(self, name, params, ports):
                self._groups = (name, "", params, ports)
            def group(self, n):
                return self._groups[n-1] if n-1 < len(self._groups) else None
        
        return MockMatch(module_name, params_str, ports_str)

    def _parse_modules(self) -> None:
        """Parse all module/interface/package definitions."""
        i = 0
        while i < len(self._lines):
            line = self._lines[i]
            stripped = line.strip()

            # Detect module declarations (may span multiple lines)
            for mod_type in [ModuleType.MODULE, ModuleType.INTERFACE,
                           ModuleType.PACKAGE, ModuleType.PROGRAM]:
                keyword = mod_type.value
                match = None
                # Try single-line match first
                single_match = re.match(
                    rf'\s*{keyword}\s+(\w+)\s*(#\s*\(([^)]*)\))?\s*\(([^)]*)\)\s*;?\s*$',
                    stripped
                )
                if single_match:
                    match = single_match
                else:
                    # Try multi-line: module name #(params) (ports)
                    # Collect lines until we find the closing ) of port list
                    if stripped.startswith(keyword):
                        multi_line = stripped
                        j = i + 1
                        paren_depth = multi_line.count('(') - multi_line.count(')')
                        while j < len(self._lines) and paren_depth > 0:
                            next_line = self._lines[j].strip()
                            multi_line += ' ' + next_line
                            paren_depth += next_line.count('(') - next_line.count(')')
                            j += 1
                        if paren_depth == 0:
                            # Use a more robust parser for multi-line headers
                            match = self._parse_module_header_multi(mod_type, multi_line)
                if match:
                    self._parse_module_body(i, mod_type, match)
                    break

            # Skip to next line
            if self._current_module and i < self._current_module.end_line:
                i = self._current_module.end_line + 1
                self._current_module = None
            else:
                i += 1

    def _parse_module_body(self, start_line: int, mod_type: ModuleType,
                           match: re.Match) -> None:
        """Parse the body of a module definition."""
        module_name = match.group(1)
        module = DesignModule(
            name=module_name,
            module_type=mod_type,
            start_line=start_line + 1,
        )

        # Parse parameters
        param_str = match.group(3) or ""
        if param_str:
            module.parameters = self._parse_parameters(param_str, start_line)

        # Parse port list from declaration - only for simple single-line cases
        # For multi-line complex ports, ANSI parsing will handle it
        port_str = match.group(4) or ""
        if port_str and '\n' not in port_str and 'input' not in port_str and 'output' not in port_str:
            module.ports = self._parse_port_list(port_str, start_line)

        # Find module end - start from the actual module declaration line
        module_decl_line = start_line - 1  # start_line was module_decl_line + 1
        depth = 0
        end_line = module_decl_line
        for i in range(module_decl_line, len(self._lines)):
            line = self._lines[i].strip()
            # Use regex to count whole words only
            m = len(re.findall(r'\b(?:module|interface|package|program)\b', line))
            e = len(re.findall(r'\b(?:endmodule|endinterface|endpackage|endprogram)\b', line))
            depth += m - e
            if depth <= 0 and i > module_decl_line:
                end_line = i
                break

        module.end_line = end_line + 1

        # Find actual body start (after module header closing );)
        body_start = start_line
        for i in range(start_line, min(end_line + 1, len(self._lines))):
            if self._lines[i].strip().endswith(');'):
                body_start = i + 1
                break
        
        # Parse module body
        body_lines = self._lines[body_start:end_line + 1]
        self._parse_module_content(module, body_lines, body_start)

        # Also parse ANSI ports from header (multi-line module declarations)
        header_lines = self._lines[start_line:body_start]
        header_content = "\n".join(header_lines)
        self._parse_ansi_ports(module, header_content, start_line)

        self.modules.append(module)
        self._current_module = module

    def _parse_parameters(self, param_str: str, base_line: int) -> list:
        """Parse parameter declarations."""
        params = []
        for part in param_str.split(","):
            part = part.strip()
            if not part:
                continue
            # parameter [type] NAME = DEFAULT
            # Handle: parameter int DEPTH = 16 or parameter DEPTH = 16
            match = re.match(r'(?:parameter\s+)?(?:(\w+)\s+)?(\w+)\s*(?:=\s*(.+))?', part)
            if match:
                # group(1) = type (optional), group(2) = name, group(3) = default
                name = match.group(2) if match.group(1) else match.group(1)
                default_val = match.group(3) if match.group(1) else match.group(2)
                params.append(Parameter(
                    name=name.strip(),
                    default_value=(default_val or "").strip(),
                    line=base_line + 1,
                ))
        return params

    def _parse_port_list(self, port_str: str, base_line: int) -> list:
        """Parse port declarations from port list."""
        ports = []
        # Handle ANSI and non-ANSI style
        for part in port_str.split(","):
            part = part.strip()
            if not part:
                continue
            # Simple name
            match = re.match(r'(\w+)', part)
            if match:
                ports.append(Port(
                    name=match.group(1),
                    line=base_line + 1,
                ))
        return ports

    def _parse_module_content(self, module: DesignModule, lines: list,
                              base_line: int) -> None:
        """Parse the content of a module body."""
        # Build a combined string for multi-line parsing
        content = "\n".join(lines)

        # Parse port directions (ANSI style)
        self._parse_ansi_ports(module, content, base_line)

        # Parse internal signals
        self._parse_internal_signals(module, content, base_line)

        # Parse always blocks
        self._parse_always_blocks(module, content, base_line)

        # Parse continuous assignments
        self._parse_assigns(module, content, base_line)

        # Parse module instantiations
        self._parse_instances(module, content, base_line)

        # Parse assertions
        self._parse_assertions(module, content, base_line)

        # Parse functions and tasks
        self._parse_functions(module, content, base_line)
        self._parse_tasks(module, content, base_line)

    def _parse_ansi_ports(self, module: DesignModule, content: str,
                          base_line: int) -> None:
        """Parse ANSI-style port declarations."""
        # Pattern: (input|output|inout) [var] [type] [signed] [width] name
        pattern = re.compile(
            r'\b(input|output|inout)\s+'
            r'(?:var\s+)?'
            r'(?:(?:logic|wire|reg|bit)\s+)?'
            r'(?:(?:signed|unsigned)\s+)?'
            r'(?:(\[[^\]]+\])\s+)?'
            r'(\w+)',
            re.MULTILINE
        )

        for match in pattern.finditer(content):
            direction_str = match.group(1)
            width = match.group(2) or ""
            name = match.group(3)

            direction = {
                "input": SignalDirection.INPUT,
                "output": SignalDirection.OUTPUT,
                "inout": SignalDirection.INOUT,
            }.get(direction_str, SignalDirection.INPUT)

            # Find line number
            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1

            # Check if port already exists from port list
            existing = next((p for p in module.ports if p.name == name), None)
            if existing:
                existing.direction = direction
                existing.width = width.strip()
                existing.line = line_num
            else:
                module.ports.append(Port(
                    name=name,
                    direction=direction,
                    width=width.strip(),
                    line=line_num,
                ))

    def _parse_internal_signals(self, module: DesignModule, content: str,
                                base_line: int) -> None:
        """Parse internal signal declarations."""
        # Pattern to match signal declarations including comma-separated names
        pattern = re.compile(
            r'\b(logic|wire|reg|bit|integer|real|tri|wand|wor)\s+'
            r'(?:(?:signed|unsigned)\s+)?'
            r'(?:(\[[^\]]+\])\s+)?'
            r'([\w\s,]+)',
            re.MULTILINE
        )

        for match in pattern.finditer(content):
            type_str = match.group(1)
            width = match.group(2) or ""
            names_str = match.group(3)

            type_map = {
                "logic": SignalType.LOGIC,
                "wire": SignalType.WIRE,
                "reg": SignalType.REG,
                "bit": SignalType.BIT,
                "integer": SignalType.INTEGER,
                "real": SignalType.REAL,
                "tri": SignalType.TRI,
                "wand": SignalType.WAND,
                "wor": SignalType.WOR,
            }

            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1

            # Split comma-separated names
            for name in [n.strip() for n in names_str.split(",")]:
                if not name:
                    continue
                # Skip if it's a port (already captured)
                if not any(p.name == name for p in module.ports):
                    module.signals.append(Signal(
                        name=name,
                        signal_type=type_map.get(type_str, SignalType.UNKNOWN),
                        width=width.strip(),
                        line=line_num,
                    ))

    def _parse_always_blocks(self, module: DesignModule, content: str,
                             base_line: int) -> None:
        """Parse always/combinational blocks."""
        pattern = re.compile(
            r'\b(always(?:_ff|_comb|_latch)?|always)\s*@\s*\(\s*([^)]*)\s*\)',
            re.MULTILINE
        )

        for match in pattern.finditer(content):
            sensitivity = match.group(2).strip()
            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1

            clock = ""
            reset = ""
            reset_type = ""

            # Detect clock and reset
            if "posedge" in sensitivity or "negedge" in sensitivity:
                edges = re.findall(r'(posedge|negedge)\s+(\w+)', sensitivity)
                if edges:
                    clock = edges[0][1]
                    if len(edges) > 1:
                        reset = edges[1][1]
                        reset_type = "async"
                # Also check for if(reset) pattern
                block_start = match.end()
                block_text = content[block_start:block_start + 500]
                reset_match = re.search(
                    r'if\s*\(\s*(!?\s*(\w+))\s*\)', block_text
                )
                if reset_match and not reset:
                    reset = reset_match.group(2)
                    reset_type = "sync"
            else:
                sensitivity = "comb"

            module.always_blocks.append(AlwaysBlock(
                sensitivity=sensitivity,
                clock=clock,
                reset=reset,
                reset_type=reset_type,
                line=line_num,
            ))

    def _parse_assigns(self, module: DesignModule, content: str,
                       base_line: int) -> None:
        """Parse continuous assignments."""
        pattern = re.compile(r'\bassign\s+(\w+)\s*=', re.MULTILINE)
        for match in pattern.finditer(content):
            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1
            module.assigns.append({
                "target": match.group(1),
                "line": line_num,
            })

    def _parse_instances(self, module: DesignModule, content: str,
                         base_line: int) -> None:
        """Parse module instantiations."""
        # Pattern: module_name #(.params) instance_name (.ports());
        pattern = re.compile(
            r'(\w+)\s*(?:#\s*\([^)]*\))?\s+(\w+)\s*\.\s*('
            r'\([^)]*\)|$)',
            re.MULTILINE
        )

        for match in pattern.finditer(content):
            mod_name = match.group(1)
            inst_name = match.group(2)

            # Skip common keywords
            if mod_name in ("if", "else", "for", "while", "case", "assign",
                          "always", "initial", "module", "function", "task",
                          "input", "output", "inout", "logic", "wire", "reg"):
                continue

            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1

            connections = {}
            port_str = match.group(3)
            if port_str and port_str.startswith("("):
                connections = self._parse_port_connections(port_str)

            module.instances.append(ModuleInstance(
                module_name=mod_name,
                instance_name=inst_name,
                connections=connections,
                line=line_num,
            ))

    def _parse_port_connections(self, port_str: str) -> dict:
        """Parse port connections of a module instance."""
        connections = {}
        inner = port_str.strip("()")
        for part in inner.split(","):
            part = part.strip()
            if "." in part:
                match = re.match(r'\.(\w+)\s*\(\s*(.*)\s*\)', part)
                if match:
                    connections[match.group(1)] = match.group(2).strip()
        return connections

    def _parse_assertions(self, module: DesignModule, content: str,
                          base_line: int) -> None:
        """Parse SystemVerilog assertions."""
        # Concurrent assertions
        patterns = [
            (r'\bproperty\s+(\w+)\s*\(', "property"),
            (r'\bassert\s+property\s*\(', "assert"),
            (r'\bassume\s+property\s*\(', "assume"),
            (r'\bcover\s+property\s*\(', "cover"),
            (r'\bassert\s+(\w+)', "assert_immediate"),
        ]

        for pattern_str, assert_type in patterns:
            pattern = re.compile(pattern_str, re.MULTILINE)
            for match in pattern.finditer(content):
                pos = match.start()
                line_num = content[:pos].count("\n") + base_line + 1
                name = match.group(1) if match.lastindex else f"assertion_{line_num}"

                # Extract the assertion code
                start = match.start()
                depth = 0
                end = start
                for j in range(start, min(start + 2000, len(content))):
                    if content[j] == "(":
                        depth += 1
                    elif content[j] == ")":
                        depth -= 1
                        if depth <= 0:
                            end = j + 1
                            break

                module.assertions.append(Assertion(
                    name=name,
                    code=content[start:end].strip(),
                    assertion_type=assert_type,
                    line=line_num,
                ))

    def _parse_functions(self, module: DesignModule, content: str,
                         base_line: int) -> None:
        """Parse function declarations."""
        pattern = re.compile(
            r'\bfunction\s+(?:automatic\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)',
            re.MULTILINE
        )
        for match in pattern.finditer(content):
            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1
            args = [a.strip() for a in match.group(3).split(",") if a.strip()]
            module.functions.append(Function(
                name=match.group(2),
                return_type=match.group(1),
                arguments=args,
                line=line_num,
            ))

    def _parse_tasks(self, module: DesignModule, content: str,
                     base_line: int) -> None:
        """Parse task declarations."""
        pattern = re.compile(
            r'\btask\s+(?:automatic\s+)?(\w+)\s*\(([^)]*)\)',
            re.MULTILINE
        )
        for match in pattern.finditer(content):
            pos = match.start()
            line_num = content[:pos].count("\n") + base_line + 1
            args = [a.strip() for a in match.group(2).split(",") if a.strip()]
            module.tasks.append(Task(
                name=match.group(1),
                arguments=args,
                line=line_num,
            ))

    def _analyze_fsms(self) -> None:
        """Analyze and extract Finite State Machines from parsed modules."""
        for module in self.modules:
            fsm_candidates = self._detect_fsm(module)
            module.fsm_info = fsm_candidates

    def _detect_fsm(self, module: DesignModule) -> list:
        """Detect FSMs by looking for state register patterns."""
        fsms = []

        # Look for case statements with state-like names
        case_pattern = re.compile(r'\bcase\s*\(\s*(\w+)\s*\)', re.MULTILINE)
        for ab in module.always_blocks:
            # Find case statements in the module content
            module_content = "\n".join(self._lines[module.start_line-1:module.end_line])
            for match in case_pattern.finditer(module_content):
                state_var = match.group(1)
                pos = match.start()
                line_num = module.start_line + module_content[:pos].count("\n")

                # Extract case items
                states = self._extract_case_states(module_content, match.end())

                if states and self._looks_like_fsm(states):
                    transitions = self._extract_transitions(
                        module_content, match.end(), states, state_var
                    )
                    fsms.append(FSMInfo(
                        name=f"fsm_{state_var}",
                        current_signal=state_var,
                        states=[FSMState(name=s) for s in states],
                        transitions=transitions,
                        state_variable=state_var,
                        line=line_num,
                    ))

        return fsms

    def _extract_case_states(self, content: str, start: int) -> list:
        """Extract state names from a case statement."""
        states = []
        depth = 0
        i = start
        while i < len(content) and i < start + 5000:
            ch = content[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == ":" and depth == 0:
                # Look backward for state name
                j = i - 1
                while j >= 0 and content[j] in " \t\n\r":
                    j -= 1
                name_end = j + 1
                while j >= 0 and (content[j].isalnum() or content[j] == "_"):
                    j -= 1
                state_name = content[j+1:name_end].strip()
                if state_name and state_name not in ("endcase", "default", "endswitch"):
                    states.append(state_name)
            elif ch == "e" and content[i:i+8] == "endcase":
                break
            i += 1
        return states

    def _looks_like_fsm(self, states: list) -> bool:
        """Heuristic: does this look like an FSM?"""
        if len(states) < 2:
            return False
        # FSM states often have common prefixes or naming patterns
        state_names = [s.upper() for s in states]
        # Check for common FSM naming patterns
        fsm_keywords = ["IDLE", "WAIT", "START", "DONE", "ERROR", "RESET",
                       "ACTIVE", "BUSY", "READY", "VALID", "LOAD", "FETCH",
                       "EXEC", "WRITE", "READ", "INIT", "SETUP"]
        matches = sum(1 for s in state_names if any(kw in s for kw in fsm_keywords))
        return matches >= 1 or len(states) >= 3

    def _extract_transitions(self, content: str, start: int,
                             states: list, state_var: str) -> list:
        """Extract FSM transitions from case/if-else patterns."""
        transitions = []
        # Look for state assignment patterns: state_var <= NEXT_STATE
        pattern = re.compile(
            rf'{re.escape(state_var)}\s*<=?\s*(\w+)',
            re.MULTILINE
        )
        for match in pattern.finditer(content, start):
            next_state = match.group(1)
            if next_state in states:
                pos = match.start()
                # Look backward for the case item (source state)
                preceding = content[max(0, pos-200):pos]
                source_state = None
                for s in reversed(states):
                    if s in preceding:
                        source_state = s
                        break
                if source_state:
                    transitions.append(FSMTransition(
                        from_state=source_state,
                        to_state=next_state,
                        line=start + content[:pos].count("\n"),
                    ))
        return transitions

    def _analyze_protocols(self) -> None:
        """Detect handshake protocols, FIFOs, and common patterns."""
        for module in self.modules:
            content = "\n".join(self._lines[module.start_line-1:module.end_line])
            metadata = module.__dict__.get("metadata", {})

            # Detect valid/ready handshake
            signals = [s.name for s in module.signals] + [p.name for p in module.ports]
            has_valid = any("valid" in s.lower() for s in signals)
            has_ready = any("ready" in s.lower() for s in signals)
            has_enable = any("enable" in s.lower() or "en" == s.lower() for s in signals)

            if has_valid and has_ready:
                metadata["protocol"] = "valid_ready_handshake"
            elif has_enable:
                metadata["protocol"] = "enable_based"

            # Detect FIFO patterns
            has_fifo = any("fifo" in s.lower() for s in signals)
            has_full = any("full" in s.lower() for s in signals)
            has_empty = any("empty" in s.lower() for s in signals)
            if has_fifo or (has_full and has_empty):
                metadata["is_fifo"] = True

            # Detect counter patterns
            has_count = any("count" in s.lower() for s in signals)
            has_overflow = any("overflow" in s.lower() or "ovf" in s.lower() for s in signals)
            if has_count:
                metadata["has_counter"] = True
                if has_overflow:
                    metadata["counter_has_overflow"] = True

            # Detect memory/ram patterns
            has_mem = any("mem" in s.lower() or "ram" in s.lower() for s in signals)
            if has_mem:
                metadata["is_memory"] = True

            # Detect bus interfaces
            has_addr = any("addr" in s.lower() for s in signals)
            has_data = any("data" in s.lower() for s in signals)
            has_strb = any("strb" in s.lower() or "strobe" in s.lower() for s in signals)
            if has_addr and has_data:
                if has_strb:
                    metadata["protocol"] = "axi_like"
                else:
                    metadata["protocol"] = "simple_bus"

            # Count register stages (pipeline detection)
            reg_stages = len([s for s in module.signals if s.signal_type == SignalType.REG])
            if reg_stages > 3:
                metadata["pipeline_stages"] = reg_stages

            # Store dependencies (instantiated modules)
            metadata["dependencies"] = list(set(
                inst.module_name for inst in module.instances
            ))

            module.metadata = metadata

    def _identify_corner_cases(self) -> None:
        """Identify potential corner cases based on module structure."""
        for module in self.modules:
            corner_cases = []

            # FSM corner cases
            for fsm in module.fsm_info:
                if fsm.states:
                    corner_cases.append({
                        "type": "fsm",
                        "description": f"FSM '{fsm.name}' with {len(fsm.states)} states",
                        "cases": [
                            "All state transitions exercised",
                            "Reset behavior from each state",
                            "Invalid state recovery",
                            f"Simultaneous events in states: {[s.name for s in fsm.states]}",
                        ],
                    })

            # FIFO corner cases
            if module.metadata.get("is_fifo"):
                corner_cases.append({
                    "type": "fifo",
                    "description": "FIFO boundary conditions",
                    "cases": [
                        "Write when full",
                        "Read when empty",
                        "Simultaneous read and write when full",
                        "Simultaneous read and write when empty",
                        "Reset during operation",
                        "Backpressure scenarios",
                    ],
                })

            # Counter corner cases
            if module.metadata.get("has_counter"):
                corner_cases.append({
                    "type": "counter",
                    "description": "Counter boundary conditions",
                    "cases": [
                        "Counter overflow",
                        "Counter underflow",
                        "Counter at max value",
                        "Counter at min value",
                        "Reset during count",
                    ],
                })

            # Handshake corner cases
            if module.metadata.get("protocol") == "valid_ready_handshake":
                corner_cases.append({
                    "type": "handshake",
                    "description": "Valid/ready protocol corner cases",
                    "cases": [
                        "Backpressure (ready deasserted)",
                        "Data stability during valid",
                        "Protocol violation timing",
                        "Reset during transfer",
                        "Multiple valid without ready",
                    ],
                })

            # Pipeline corner cases
            if module.metadata.get("pipeline_stages", 0) > 0:
                corner_cases.append({
                    "type": "pipeline",
                    "description": "Pipeline corner cases",
                    "cases": [
                        "Flush during active transfer",
                        "Stall during active transfer",
                        "Reset propagation through pipeline",
                    ],
                })

            # General corner cases
            corner_cases.append({
                "type": "general",
                "description": "General corner cases",
                "cases": [
                    "Async reset assertion and de-assertion",
                    "Clock start/stop",
                    "All inputs tied to same value",
                    "All outputs checked simultaneously",
                ],
            })

            module.metadata["corner_cases"] = corner_cases

    def get_design_summary(self) -> dict:
        """Generate a summary of the entire parsed design."""
        total_ports = sum(len(m.ports) for m in self.modules)
        total_signals = sum(len(m.signals) for m in self.modules)
        total_fsms = sum(len(m.fsm_info) for m in self.modules)
        total_assertions = sum(len(m.assertions) for m in self.modules)
        total_instances = sum(len(m.instances) for m in self.modules)
        total_always = sum(len(m.always_blocks) for m in self.modules)

        return {
            "num_modules": len(self.modules),
            "module_names": [m.name for m in self.modules],
            "total_ports": total_ports,
            "total_internal_signals": total_signals,
            "total_fsm_count": total_fsms,
            "total_assertions": total_assertions,
            "total_module_instances": total_instances,
            "total_always_blocks": total_always,
            "clock_signals": list(set(
                c for m in self.modules for c in m.clock_signals
            )),
            "reset_signals": list(set(
                r for m in self.modules for r in m.reset_signals
            )),
            "protocols_detected": list(set(
                m.metadata.get("protocol", "none")
                for m in self.modules
                if m.metadata.get("protocol")
            )),
            "modules_with_fsm": [m.name for m in self.modules if m.has_fsm],
            "modules_with_assertions": [m.name for m in self.modules if m.has_assertions],
        }

    def _parse_defines(self) -> None:
        """Extract `define macros."""
        for i, line in enumerate(self._lines):
            match = re.match(r'\s*`define\s+(\w+)\s*(.*)', line)
            if match:
                self._defines[match.group(1)] = match.group(2).strip()

    def _parse_includes(self) -> None:
        """Extract `include directives."""
        for line in self._lines:
            match = re.match(r'\s*`include\s+["<](.+)[">]', line)
            if match:
                self._includes.append(match.group(1))