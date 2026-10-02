"""RTL Hierarchy Browser API endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engines.rtl_parser.parser import RTLParser

router = APIRouter(prefix="/rtl", tags=["RTL Hierarchy"])


class HierarchyNode(BaseModel):
    id: str
    name: str
    type: str
    children: List["HierarchyNode"] = Field(default_factory=list)
    ports: List[Dict[str, Any]] = Field(default_factory=list)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    instances: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HierarchyResponse(BaseModel):
    modules: List[HierarchyNode]
    diagram: Dict[str, Any]


HierarchyNode.model_rebuild()


@router.get("/hierarchy/{design_id}", response_model=HierarchyResponse)
async def get_hierarchy(design_id: str):
    """Get hierarchical module structure with diagram data."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Design
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Design).where(Design.id == design_id))
        design = result.scalar_one_or_none()

        if not design:
            raise HTTPException(
                status_code=404,
                detail="Design not found. Analyze the RTL with a project_id to persist it first.",
            )
        design_name = design.name
        raw_content = design.raw_content

    if not raw_content:
        raise HTTPException(status_code=400, detail="Design has no stored RTL content")

    # Parse RTL from the persisted content.
    parser = RTLParser()
    modules = parser.parse(raw_content, design_name)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    by_name: Dict[str, Any] = {}
    for module in modules:
        by_name.setdefault(module.name, module)

    def build_node(module, seen: frozenset) -> HierarchyNode:
        """Recursively build a node, guarding against instantiation cycles."""
        children: List[HierarchyNode] = []
        for inst in module.instances:
            child = by_name.get(inst.module_name)
            # Skip self-references and already-visited modules (recursive RTL).
            if child is None or child.name in seen:
                continue
            children.append(build_node(child, seen | {child.name}))

        return HierarchyNode(
            id=f"mod_{module.name}",
            name=module.name,
            type=module.module_type.value,
            children=children,
            ports=[
                {
                    "name": p.name,
                    "direction": p.direction.value,
                    "width": p.width,
                    "line": p.line,
                }
                for p in module.ports
            ],
            signals=[
                {
                    "name": s.name,
                    "type": s.signal_type.value,
                    "width": s.width,
                    "line": s.line,
                }
                for s in module.signals
            ],
            instances=[
                {
                    "name": inst.instance_name,
                    "module": inst.module_name,
                    "line": inst.line,
                }
                for inst in module.instances
            ],
            metadata=module.metadata if isinstance(module.metadata, dict) else {},
        )

    # A top module is one that nothing else instantiates (or is flagged top).
    instantiated = {inst.module_name for m in modules for inst in m.instances}
    tops = [m for m in modules if m.is_top or m.name not in instantiated]
    if not tops:
        tops = list(modules)

    hierarchy = [build_node(m, frozenset({m.name})) for m in tops]

    return HierarchyResponse(
        modules=hierarchy,
        diagram={
            "mermaid": generate_mermaid_diagram(modules),
            "graphviz": generate_graphviz_diagram(modules),
            "hierarchy": [m.name for m in modules],
        },
    )


def _safe_id(name: str) -> str:
    """Create a Mermaid-safe identifier from a module name."""
    return "".join(ch if ch.isalnum() else "_" for ch in name)


def generate_mermaid_diagram(modules) -> str:
    """Generate Mermaid diagram for module hierarchy."""
    module_ids = {m.name: f"M{_safe_id(m.name)}" for m in modules}
    unique_ids = {}
    used = set()
    for name, mid in module_ids.items():
        candidate, counter = mid, 1
        while candidate in used:
            counter += 1
            candidate = f"{mid}_{counter}"
        used.add(candidate)
        unique_ids[name] = candidate

    lines = ["graph TD"]
    for module in modules:
        mid = unique_ids[module.name]
        shape = "[" if module.module_type.value == "module" else "(("
        close = "]" if module.module_type.value == "module" else "))"
        lines.append(f'  {mid}{shape}"{module.name}"{close}')
        lines.append(
            f"  style {mid} fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff"
        )

    for module in modules:
        for inst in module.instances:
            target = unique_ids.get(inst.module_name)
            if target:
                lines.append(f'  {unique_ids[module.name]} -->|"{inst.instance_name}"| {target}')

    return "\n".join(lines)


def generate_graphviz_diagram(modules) -> str:
    """Generate Graphviz DOT diagram for module hierarchy."""
    lines = [
        "digraph hierarchy {",
        "  rankdir=TB;",
        "  node [fontname=\"Monospace\", fontsize=10, style=filled, fillcolor=\"#1e293b\", color=\"#3b82f6\", fontcolor=\"white\"];",
        "  edge [color=\"#64748b\"];",
        "  bgcolor=\"#0f172a\";",
    ]

    for module in modules:
        shape = "box" if module.module_type.value == "module" else "ellipse"
        label = f"{module.name}\\n({module.module_type.value})"
        lines.append(f'  "{module.name}" [shape={shape}, label="{label}"];')

    for module in modules:
        for inst in module.instances:
            lines.append(f'  "{module.name}" -> "{inst.module_name}" [label="{inst.instance_name}"];')

    lines.append("}")
    return "\n".join(lines)


class DiagramRequest(BaseModel):
    design_id: str
    format: str = "mermaid"  # mermaid, graphviz, json


@router.post("/diagram")
async def generate_diagram(request: DiagramRequest):
    """Generate diagram for a design."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Design
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Design).where(Design.id == request.design_id))
        design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    parser = RTLParser()
    modules = parser.parse(design.raw_content, design.name)

    if request.format == "mermaid":
        return {"diagram": generate_mermaid_diagram(modules), "format": "mermaid"}
    elif request.format == "graphviz":
        return {"diagram": generate_graphviz_diagram(modules), "format": "graphviz"}
    else:
        return {"diagram": {"modules": [m.name for m in modules]}, "format": "json"}