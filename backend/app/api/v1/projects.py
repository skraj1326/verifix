"""Project management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Project, ProjectStatus, Design, Test, CoverageReport
from app.core.database import get_db


router = APIRouter(prefix="/projects")


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    created_at: str


class ProjectDetailResponse(ProjectResponse):
    design_count: int = 0
    test_count: int = 0
    coverage_latest: float = 0.0


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new verification project."""
    import uuid

    new_project = Project(
        id=str(uuid.uuid4()),
        name=project.name,
        description=project.description,
        status=ProjectStatus.ACTIVE,
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return ProjectResponse(
        id=str(new_project.id),
        name=new_project.name,
        description=new_project.description,
        status=new_project.status.value,
        created_at=new_project.created_at.isoformat(),
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    return [
        ProjectResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            status=p.status.value,
            created_at=p.created_at.isoformat(),
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
    )


@router.get("/{project_id}/summary", response_model=ProjectDetailResponse)
async def get_project_summary(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get project detail including design/test counts."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    designs_result = await db.execute(
        select(Design).where(Design.project_id == project.id)
    )
    design_count = len(designs_result.scalars().all())

    tests_result = await db.execute(
        select(Test).where(Test.project_id == project.id)
    )
    test_count = len(tests_result.scalars().all())

    cov_result = await db.execute(
        select(CoverageReport).where(CoverageReport.project_id == project.id)
    )
    coverage_reports = cov_result.scalars().all()
    coverage_latest = coverage_reports[-1].overall_coverage if coverage_reports else 0.0

    return ProjectDetailResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        status=project.status.value,
        created_at=project.created_at.isoformat(),
        design_count=design_count,
        test_count=test_count,
        coverage_latest=coverage_latest,
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return {"status": "deleted"}