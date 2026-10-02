"""RTL Hierarchy Browser API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.engines.rtl_parser.parser import RTLParser
from app.engines.knowledge_graph.builder import KnowledgeGraphBuilder

router = APIRouter(prefix="/rtl", tags=["RTL Hierarchy"])


class HierarchyNode(BaseModel):
    id: str
    name: str
    type: str
    children: List["HierarchyNode"] = []
    ports: List[Dict[str, Any]] = []
    signals: List[Dict[str, Any]] = []
    instances: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


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
        raise HTTPException(status_code=404, detail="Design not found")

    # Parse RTL if not already parsed
    parser = RTLParser()
    modules = parser.parse(design.raw_content, design.name)

    if not modules:
        raise HTTPException(status_code=400, detail="No modules found in RTL")

    # Build knowledge graph
    kg_builder = KnowledgeGraphBuilder()
    graph = kg_builder.build(modules)

    # Build hierarchy tree
    def build_node(module) -> HierarchyNode:
        return HierarchyNode(
            id=f"mod_{module.name}",
            name=module.name,
            type=module.module_type.value,
            children=[build_node(inst) for inst in module.instances if any(m.name == inst.module_name for m in modules)],
            ports=[{
                "name": p.name,
                "direction": p.direction.value,
                "width": p.width,
                "line": p.line
            } for p in module.ports],
            signals=[{
                "name": s.name,
                "type": s.signal_type.value,
                "width": s.width,
                "line": s.line
            } for s in module.signals],
            instances=[{
                "name": inst.instance_name,
                "module": inst.module_name,
                "line": inst.line
            } for inst in module.instances],
            metadata=module.metadata
        )

    # Build diagram data
    mermaid = generate_mermaid_diagram(modules)
    graphviz = generate_graphviz_diagram(modules)

    hierarchy = [build_node(m) for m in modules if m.is_top or not any(inst.module_name == m.name for m in modules for inst in m.instances)]

    return HierarchyResponse(
        modules=hierarchy,
        diagram={
            "mermaid": mermaid,
            "graphviz": graphviz,
            "hierarchy": [m.name for m in modules]
        }
    )


def generate_mermaid_diagram(modules) -> str:
    """Generate Mermaid diagram for module hierarchy."""
    lines = ["graph TD"]
    lines.append("  style A fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff")
    lines.append("  style B fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff")
    lines.append("  style C fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff")

    node_id = 0
    module_ids = {}

    for module in modules:
        mid = f"M{node_id}"
        module_ids[module.name] = mid
        node_id += 1
        shape = "[" if module.module_type.value == "module" else "(("
        close = "]" if module.module_type.value == "module" else "))"
        lines.append(f"  {mid}{shape}{module.name}{close}")

    for module in modules:
        mid = module_ids[module.name]
        for inst in module.instances:
            if inst.module_name in module_ids:
                lines.append(f"  {mid} --> {module_ids[inst.module_name]}")

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