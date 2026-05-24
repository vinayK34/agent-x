from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import WorkflowIn, WorkflowOut
from app.db import get_session
from app.models.workflow import Workflow
from app.seeds.templates import TEMPLATES

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(s: AsyncSession = Depends(get_session)):
    res = await s.execute(select(Workflow).order_by(Workflow.created_at))
    return list(res.scalars().all())


@router.post("", response_model=WorkflowOut, status_code=201)
async def create_workflow(body: WorkflowIn, s: AsyncSession = Depends(get_session)):
    wf = Workflow(**body.model_dump())
    s.add(wf)
    await s.commit()
    await s.refresh(wf)
    return wf


@router.get("/templates")
async def list_templates():
    return [{"key": k} for k in TEMPLATES.keys()]


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def get_workflow(workflow_id: str, s: AsyncSession = Depends(get_session)):
    wf = await s.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404)
    return wf


@router.put("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(workflow_id: str, body: WorkflowIn, s: AsyncSession = Depends(get_session)):
    wf = await s.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404)
    wf.name = body.name
    wf.description = body.description
    wf.spec = body.spec
    await s.commit()
    await s.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, s: AsyncSession = Depends(get_session)):
    wf = await s.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404)
    await s.delete(wf)
    await s.commit()
