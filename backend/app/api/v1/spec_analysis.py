"""Specification Analysis API endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.engines.spec_parser.parser import SpecParser, Requirement, RequirementCategory

router = APIRouter(prefix="/spec")


class SpecAnalysisRequest(BaseModel):
    content: str
    filename: str = "spec.md"
    doc_type: str = "markdown"


class SpecAnalysisResponse(BaseModel):
    filename: str
    total_requirements: int
    requirements: list[dict]
    summary: dict


@router.post("/analyze", response_model=SpecAnalysisResponse)
async def analyze_specification(request: SpecAnalysisRequest):
    """Parse and analyze a specification document."""
    parser = SpecParser()

    try:
        spec = parser.parse(request.content, request.filename, request.doc_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")

    if not spec.requirements:
        raise HTTPException(
            status_code=400,
            detail="No requirements found in the specification"
        )

    # Serialize requirements
    serialized_reqs = []
    for req in spec.requirements:
        serialized_reqs.append({
            "id": req.id,
            "category": req.category.value,
            "title": req.title,
            "description": req.description,
            "source": req.source.value,
            "source_location": req.source_location,
            "priority": req.priority,
            "tags": req.tags,
            "related_signals": req.related_signals,
            "verification_method": req.verification_method,
            "acceptance_criteria": req.acceptance_criteria,
            "metadata": req.metadata,
        })

    return SpecAnalysisResponse(
        filename=request.filename,
        total_requirements=len(spec.requirements),
        requirements=serialized_reqs,
        summary=spec.metadata,
    )


@router.post("/upload")
async def upload_spec_file(file: UploadFile = File(...)):
    """Upload a specification file for analysis."""
    content = await file.read()

    # Determine document type
    doc_type = "markdown"
    if file.filename.lower().endswith(".pdf"):
        doc_type = "pdf"
        # Note: Would need PyMuPDF to extract text
        # For now, treat as text
        text = content.decode("utf-8", errors="ignore")
    elif file.filename.lower().endswith(".docx"):
        doc_type = "word"
        # Would need python-docx
        text = content.decode("utf-8", errors="ignore")
    else:
        text = content.decode("utf-8")

    request = SpecAnalysisRequest(content=text, filename=file.filename, doc_type=doc_type)
    return await analyze_specification(request)


@router.get("/requirement-categories")
async def get_requirement_categories():
    """Get available requirement categories."""
    return {
        "categories": [
            {"value": cat.value, "label": cat.value.replace("_", " ").title()}
            for cat in RequirementCategory
        ]
    }