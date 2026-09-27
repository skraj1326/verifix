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


class RTLAnalysisResponse(BaseModel):
    filename: str
    modules: list[dict]
    summary: dict
    knowledge_graph: dict
    recommendations: list[dict]


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

    return RTLAnalysisResponse(
        filename=request.filename,
        modules=serialized_modules,
        summary=parser.get_design_summary(),
        knowledge_graph=knowledge_graph,
        recommendations=recommendations,
    )


@router.post("/upload")
async def upload_rtl_file(file: UploadFile = File(...)):
    """Upload an RTL file for analysis."""
    content = await file.read()
    text = content.decode("utf-8")

    request = RTLAnalysisRequest(content=text, filename=file.filename)
    return await analyze_rtl(request)
