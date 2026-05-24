from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MessageOut, RunIn, RunOut
from app.db import get_session
from app.models.message import Message
from app.models.run import Run
from app.runtime import run_workflow

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=201)
async def start_run(body: RunIn, s: AsyncSession = Depends(get_session)):
    run_id = await run_workflow(body.workflow_id, body.input, trigger="manual")
    run = await s.get(Run, run_id)
    if not run:
        raise HTTPException(500, "run vanished")
    return run


@router.get("", response_model=list[RunOut])
async def list_runs(s: AsyncSession = Depends(get_session)):
    res = await s.execute(select(Run).order_by(Run.started_at.desc()).limit(100))
    return list(res.scalars().all())


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: str, s: AsyncSession = Depends(get_session)):
    run = await s.get(Run, run_id)
    if not run:
        raise HTTPException(404)
    return run


@router.get("/{run_id}/messages", response_model=list[MessageOut])
async def get_run_messages(run_id: str, s: AsyncSession = Depends(get_session)):
    res = await s.execute(select(Message).where(Message.run_id == run_id).order_by(Message.created_at))
    return list(res.scalars().all())
