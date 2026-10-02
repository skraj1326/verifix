"""RTL Analysis API endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.engines.rtl_parser.parser import RTLParser
from app.engines.knowledge_graph.builder import KnowledgeGraphBuilder

router = APIRouter(prefix="/rtl")


class RTLAnalysisRequest(BaseModel):
    content: str
    filename: str = "design.sv"
    # When supplied, the parsed design and its modules are persisted against the
    # project so hierarchy/diagram endpoints can reference a real design_id.
    project_id: Optional[str] = None


class RTLAnalysisResponse(BaseModel):
    filename: str
    modules: list[dict]
    summary: dict
    knowledge_graph: dict
    recommendations: list[dict]
    design_id: Optional[str] = None
    persisted: bool = False


@router.post("/analyze", response_model=RTLAnalysisResponse)
async def analyze_rtl(request: RTLAnalysisRequest):
    """Parse and analyze SystemVerilog RTL code."""
    parser = RTLParser()

    try:
        modules = parser.parse(request.content, request.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")

    if not modules:
        raise HTTPException(
            status_code=400,
            detail="No modules found in the provided RTL code"
        )

    # Build knowledge graph
    kg_builder = KnowledgeGraphBuilder()
    knowledge_graph = kg_builder.build(modules)

    # Get recommendations
    recommendations = kg_builder.get_modules_needing_verification()
    modules_without_assertions = kg_builder.get_modules_with_no_assertions()

    # Serialize modules
    serialized_modules = []
    for m in modules:
        serialized_modules.append({
            "name": m.name,
            "module_type": m.module_type.value,
            "is_top": m.is_top,
            "start_line": m.start_line,
            "end_line": m.end_line,
            "ports": [
                {
                    "name": p.name,
                    "direction": p.direction.value,
                    "width": p.width,
                    "line": p.line,
                }
                for p in m.ports
            ],
            "signals": [
                {
                    "name": s.name,
                    "type": s.signal_type.value,
                    "width": s.width,
                }
                for s in m.signals
            ],
            "parameters": [
                {"name": p.name, "default_value": p.default_value}
                for p in m.parameters
            ],
            "fsm_info": [
                {
                    "name": f.name,
                    "state_variable": f.state_variable,
                    "states": [{"name": s.name} for s in f.states],
                    "transitions": [
                        {"from": t.from_state, "to": t.to_state}
                        for t in f.transitions
                    ],
                }
                for f in m.fsm_info
            ],
            "instances": [
                {
                    "module_name": i.module_name,
                    "instance_name": i.instance_name,
                }
                for i in m.instances
            ],
            "always_blocks": [
                {
                    "sensitivity": a.sensitivity,
                    "clock": a.clock,
                    "reset": a.reset,
                    "reset_type": a.reset_type,
                }
                for a in m.always_blocks
            ],
            "assertions": [
                {"name": a.name, "type": a.assertion_type, "code": a.code}
                for a in m.assertions
            ],
            "metadata": m.metadata,
        })

    design_id = None
    persisted = False
    if request.project_id:
        design_id = await _persist_design(request.project_id, request.filename, request.content, modules)
        persisted = True

    return RTLAnalysisResponse(
        filename=request.filename,
        modules=serialized_modules,
        summary=parser.get_design_summary(),
        knowledge_graph=knowledge_graph,
        recommendations=recommendations,
        design_id=design_id,
        persisted=persisted,
    )


async def _persist_design(project_id: str, filename: str, content: str, modules) -> str:
    """Persist a parsed design and its modules so it can be referenced later."""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.database import AnalysisStatus, Design, DesignModule, Project

    design_name = modules[0].name if modules else filename

    async with AsyncSessionLocal() as db:
        project = await db.execute(select(Project).where(Project.id == project_id))
        if project.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Replace any previous analysis of the same design for this project.
        existing = await db.execute(
            select(Design).where(Design.project_id == project_id, Design.name == design_name)
        )
        for stale in existing.scalars().all():
            await db.delete(stale)
        await db.flush()

        design = Design(
            project_id=project_id,
            name=design_name,
            file_path=filename,
            raw_content=content,
            analysis_status=AnalysisStatus.COMPLETED,
        )
        db.add(design)
        await db.flush()

        for m in modules:
            db.add(
                DesignModule(
                    design_id=design.id,
                    name=m.name,
                    module_type=m.module_type.value,
                    is_top=bool(m.is_top),
                    start_line=m.start_line,
                    end_line=m.end_line,
                    parameters=[{"name": p.name, "default_value": p.default_value} for p in m.parameters],
                    ports=[
                        {
                            "name": p.name,
                            "direction": p.direction.value,
                            "width": p.width,
                            "line": p.line,
                        }
                        for p in m.ports
                    ],
                    signals=[
                        {"name": s.name, "type": s.signal_type.value, "width": s.width, "line": s.line}
                        for s in m.signals
                    ],
                    fsm_states=[{"name": s.name} for f in m.fsm_info for s in f.states],
                    fsm_transitions=[
                        {"from": t.from_state, "to": t.to_state}
                        for f in m.fsm_info
                        for t in f.transitions
                    ],
                    instances=[
                        {"module_name": i.module_name, "instance_name": i.instance_name, "line": i.line}
                        for i in m.instances
                    ],
                    always_blocks=[
                        {
                            "sensitivity": a.sensitivity,
                            "clock": a.clock,
                            "reset": a.reset,
                            "reset_type": a.reset_type,
                        }
                        for a in m.always_blocks
                    ],
                    assertions=[{"name": a.name, "type": a.assertion_type, "code": a.code} for a in m.assertions],
                    functions=[{"name": f.name} for f in getattr(m, "functions", []) or []],
                    tasks=[{"name": t.name} for t in getattr(m, "tasks", []) or []],
                    extra_metadata=m.metadata if isinstance(m.metadata, dict) else {},
                )
            )

        await db.commit()
        return str(design.id)


@router.post("/upload")
async def upload_rtl_file(file: UploadFile = File(...)):
    """Upload an RTL file for analysis."""
    content = await file.read()
    text = content.decode("utf-8")

    request = RTLAnalysisRequest(content=text, filename=file.filename)
    return await analyze_rtl(request)
