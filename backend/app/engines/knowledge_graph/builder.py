"""Knowledge Graph Builder - Creates a design knowledge graph from parsed RTL."""

from typing import Optional
from ..rtl_parser.parser import (
    RTLParser, DesignModule, SignalDirection, ModuleType
)


class NodeType:
    MODULE = "module"
    PORT = "port"
    SIGNAL = "signal"
    FSM = "fsm"
    FSM_STATE = "fsm_state"
    INSTANCE = "instance"
    ALWAYS_BLOCK = "always_block"
    ASSERTION = "assertion"
    PROTOCOL = "protocol"
    CLOCK = "clock"
    RESET = "reset"
    FUNCTION = "function"
    TASK = "task"


class EdgeType:
    HAS_PORT = "has_port"
    HAS_SIGNAL = "has_signal"
    HAS_FSM = "has_fsm"
    HAS_STATE = "has_state"
    HAS_INSTANCE = "has_instance"
    HAS_ALWAYS = "has_always"
    HAS_ASSERTION = "has_assertion"
    INSTANTIATES = "instantiates"
    DRIVES = "drives"
    USES = "uses"
    TRANSITIONS_TO = "transitions_to"
    CLOCK_OF = "clock_of"
    RESET_OF = "reset_of"
    DEPENDS_ON = "depends_on"
    PROTOCOL_USES = "protocol_uses"


class KnowledgeGraphBuilder:
    """Builds a design knowledge graph from parsed RTL modules.

    The knowledge graph links:
    module → signal → register → FSM → interface → behavior → test → assertion → coverage → bug
    """

    def __init__(self):
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._node_id_counter = 0
        self._node_index: dict[str, int] = {}

    def build(self, modules: list[DesignModule]) -> dict:
        """Build knowledge graph from parsed modules."""
        self.nodes = []
        self.edges = []
        self._node_id_counter = 0
        self._node_index = {}

        for module in modules:
            self._add_module(module)
            self._add_ports(module)
            self._add_signals(module)
            self._add_fsms(module)
            self._add_instances(module)
            self._add_always_blocks(module)
            self._add_assertions(module)
            self._add_clock_reset_edges(module)
            self._add_dependency_edges(module)
            self._add_drive_edges(module)

        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "statistics": self._compute_statistics(),
        }

    def _make_id(self, node_type: str, name: str, parent: str = "") -> str:
        """Create a unique node ID."""
        key = f"{node_type}:{parent}:{name}" if parent else f"{node_type}:{name}"
        if key not in self._node_index:
            self._node_index[key] = self._node_id_counter
            self._node_id_counter += 1
        return str(self._node_index[key])

    def _add_node(self, node_type: str, label: str, properties: dict,
                  parent: str = "") -> str:
        """Add a node to the graph."""
        node_id = self._make_id(node_type, label, parent)
        self.nodes.append({
            "id": node_id,
            "type": node_type,
            "label": label,
            "properties": properties,
        })
        return node_id

    def _add_edge(self, source: str, target: str, edge_type: str,
                  properties: dict = None) -> None:
        """Add an edge to the graph."""
        self.edges.append({
            "source": source,
            "target": target,
            "type": edge_type,
            "properties": properties or {},
        })

    def _add_module(self, module: DesignModule) -> str:
        """Add a module node."""
        return self._add_node(NodeType.MODULE, module.name, {
            "module_type": module.module_type.value,
            "is_top": module.is_top,
            "num_ports": len(module.ports),
            "num_signals": len(module.signals),
            "num_fsms": len(module.fsm_info),
            "num_instances": len(module.instances),
            "start_line": module.start_line,
            "end_line": module.end_line,
            "metadata": module.metadata,
        })

    def _add_ports(self, module: DesignModule) -> None:
        """Add port nodes and edges."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for port in module.ports:
            port_id = self._add_node(NodeType.PORT, port.name, {
                "direction": port.direction.value,
                "width": port.width,
                "line": port.line,
            }, parent=module.name)
            self._add_edge(module_id, port_id, EdgeType.HAS_PORT)

            # Mark clock/reset ports
            name_lower = port.name.lower()
            if any(clk in name_lower for clk in ["clk", "clock", "ck"]):
                self._add_edge(port_id, module_id, EdgeType.CLOCK_OF)
            if any(rst in name_lower for rst in ["rst", "reset", "rn"]):
                self._add_edge(port_id, module_id, EdgeType.RESET_OF)

    def _add_signals(self, module: DesignModule) -> None:
        """Add signal nodes and edges."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for signal in module.signals:
            signal_id = self._add_node(NodeType.SIGNAL, signal.name, {
                "type": signal.signal_type.value,
                "width": signal.width,
                "line": signal.line,
            }, parent=module.name)
            self._add_edge(module_id, signal_id, EdgeType.HAS_SIGNAL)

    def _add_fsms(self, module: DesignModule) -> None:
        """Add FSM nodes, state nodes, and transition edges."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for fsm in module.fsm_info:
            fsm_id = self._add_node(NodeType.FSM, fsm.name, {
                "state_variable": fsm.state_variable,
                "num_states": len(fsm.states),
                "num_transitions": len(fsm.transitions),
                "line": fsm.line,
            }, parent=module.name)
            self._add_edge(module_id, fsm_id, EdgeType.HAS_FSM)

            # Add state nodes
            for state in fsm.states:
                state_id = self._add_node(NodeType.FSM_STATE, state.name, {
                    "encoding": state.encoding,
                }, parent=fsm.name)
                self._add_edge(fsm_id, state_id, EdgeType.HAS_STATE)

            # Add transition edges
            for trans in fsm.transitions:
                from_id = self._make_id(NodeType.FSM_STATE, trans.from_state, fsm.name)
                to_id = self._make_id(NodeType.FSM_STATE, trans.to_state, fsm.name)
                if from_id in [n["id"] for n in self.nodes] and \
                   to_id in [n["id"] for n in self.nodes]:
                    self._add_edge(from_id, to_id, EdgeType.TRANSITIONS_TO, {
                        "condition": trans.condition,
                    })

    def _add_instances(self, module: DesignModule) -> None:
        """Add instance nodes and instantiation edges."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for inst in module.instances:
            inst_id = self._add_node(NodeType.INSTANCE, inst.instance_name, {
                "module_type": inst.module_name,
                "connections": inst.connections,
                "line": inst.line,
            }, parent=module.name)
            self._add_edge(module_id, inst_id, EdgeType.HAS_INSTANCE)

            # Try to link to known module
            target_module_id = self._make_id(NodeType.MODULE, inst.module_name)
            if target_module_id in [n["id"] for n in self.nodes]:
                self._add_edge(inst_id, target_module_id, EdgeType.INSTANTIATES)

    def _add_always_blocks(self, module: DesignModule) -> None:
        """Add always block nodes."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for idx, ab in enumerate(module.always_blocks):
            ab_id = self._add_node(NodeType.ALWAYS_BLOCK, f"{module.name}_ab{idx}", {
                "sensitivity": ab.sensitivity,
                "clock": ab.clock,
                "reset": ab.reset,
                "reset_type": ab.reset_type,
                "line": ab.line,
            }, parent=module.name)
            self._add_edge(module_id, ab_id, EdgeType.HAS_ALWAYS)

    def _add_assertions(self, module: DesignModule) -> None:
        """Add assertion nodes."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for assertion in module.assertions:
            assert_id = self._add_node(NodeType.ASSERTION, assertion.name, {
                "type": assertion.assertion_type,
                "code": assertion.code,
                "line": assertion.line,
            }, parent=module.name)
            self._add_edge(module_id, assert_id, EdgeType.HAS_ASSERTION)

    def _add_clock_reset_edges(self, module: DesignModule) -> None:
        """Connect clock/reset signals to their consumers."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for clk in module.clock_signals:
            clk_id = self._make_id(NodeType.PORT, clk, module.name)
            if clk_id in [n["id"] for n in self.nodes]:
                for ab in module.always_blocks:
                    if ab.clock == clk:
                        ab_id = self._make_id(NodeType.ALWAYS_BLOCK,
                                              f"{module.name}_ab{module.always_blocks.index(ab)}",
                                              module.name)
                        if ab_id in [n["id"] for n in self.nodes]:
                            self._add_edge(clk_id, ab_id, EdgeType.CLOCK_OF)

        for rst in module.reset_signals:
            rst_id = self._make_id(NodeType.PORT, rst, module.name)
            if rst_id in [n["id"] for n in self.nodes]:
                for ab in module.always_blocks:
                    if ab.reset == rst:
                        ab_id = self._make_id(NodeType.ALWAYS_BLOCK,
                                              f"{module.name}_ab{module.always_blocks.index(ab)}",
                                              module.name)
                        if ab_id in [n["id"] for n in self.nodes]:
                            self._add_edge(rst_id, ab_id, EdgeType.RESET_OF)

    def _add_dependency_edges(self, module: DesignModule) -> None:
        """Add dependency edges between modules."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        deps = module.metadata.get("dependencies", [])
        for dep in deps:
            dep_id = self._make_id(NodeType.MODULE, dep)
            if dep_id in [n["id"] for n in self.nodes]:
                self._add_edge(module_id, dep_id, EdgeType.DEPENDS_ON)

    def _add_drive_edges(self, module: DesignModule) -> None:
        """Add data flow edges from assigns and always blocks."""
        module_id = self._make_id(NodeType.MODULE, module.name)
        for assign in module.assigns:
            target_id = self._make_id(NodeType.SIGNAL, assign["target"], module.name)
            if target_id in [n["id"] for n in self.nodes]:
                self._add_edge(module_id, target_id, EdgeType.DRIVES, {
                    "line": assign["line"],
                })

    def _compute_statistics(self) -> dict:
        """Compute graph statistics."""
        type_counts = {}
        for node in self.nodes:
            t = node["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        edge_type_counts = {}
        for edge in self.edges:
            t = edge["type"]
            edge_type_counts[t] = edge_type_counts.get(t, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_type_counts": type_counts,
            "edge_type_counts": edge_type_counts,
        }

    def get_modules_with_no_assertions(self) -> list[str]:
        """Find modules that lack assertions."""
        modules_with_assertions = set()
        for edge in self.edges:
            if edge["type"] == EdgeType.HAS_ASSERTION:
                # Find source module
                source_node = next((n for n in self.nodes if n["id"] == edge["source"]), None)
                if source_node and source_node["type"] == NodeType.MODULE:
                    modules_with_assertions.add(source_node["label"])

        all_modules = [n["label"] for n in self.nodes if n["type"] == NodeType.MODULE]
        return [m for m in all_modules if m not in modules_with_assertions]

    def get_uncovered_fsms(self) -> list[dict]:
        """Find FSMs that need verification attention."""
        uncovered = []
        for node in self.nodes:
            if node["type"] == NodeType.FSM:
                props = node["properties"]
                uncovered.append({
                    "name": node["label"],
                    "states": props.get("num_states", 0),
                    "transitions": props.get("num_transitions", 0),
                })
        return uncovered

    def get_modules_needing_verification(self) -> list[dict]:
        """Identify modules that need verification based on complexity."""
        recommendations = []
        for node in self.nodes:
            if node["type"] == NodeType.MODULE:
                props = node["properties"]
                score = 0
                reasons = []

                if props.get("num_fsms", 0) > 0:
                    score += props["num_fsms"] * 3
                    reasons.append(f"{props['num_fsms']} FSM(s)")

                if props.get("num_instances", 0) > 0:
                    score += props["num_instances"] * 2
                    reasons.append(f"{props['num_instances']} sub-module(s)")

                if props.get("num_ports", 0) > 10:
                    score += 2
                    reasons.append(f"{props['num_ports']} ports (complex interface)")

                meta = props.get("metadata", {})
                if meta.get("is_fifo"):
                    score += 5
                    reasons.append("FIFO detected")
                if meta.get("protocol") == "valid_ready_handshake":
                    score += 3
                    reasons.append("Handshake protocol")
                if meta.get("has_counter"):
                    score += 2
                    reasons.append("Counter logic")
                if meta.get("pipeline_stages", 0) > 3:
                    score += 3
                    reasons.append(f"Pipeline with {meta['pipeline_stages']} stages")

                if score > 0:
                    recommendations.append({
                        "module": node["label"],
                        "complexity_score": score,
                        "reasons": reasons,
                    })

        recommendations.sort(key=lambda x: x["complexity_score"], reverse=True)
        return recommendations
