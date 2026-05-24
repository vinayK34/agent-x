from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AgentIn, AgentOut
from app.db import get_session
from app.models.agent import Agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(s: AsyncSession = Depends(get_session)):
    res = await s.execute(select(Agent).order_by(Agent.created_at))
    return list(res.scalars().all())


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(body: AgentIn, s: AsyncSession = Depends(get_session)):
    a = Agent(**body.model_dump())
    s.add(a)
    await s.commit()
    await s.refresh(a)
    return a


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, s: AsyncSession = Depends(get_session)):
    a = await s.get(Agent, agent_id)
    if not a:
        raise HTTPException(404)
    return a


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, body: AgentIn, s: AsyncSession = Depends(get_session)):
    a = await s.get(Agent, agent_id)
    if not a:
        raise HTTPException(404)
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    await s.commit()
    await s.refresh(a)
    return a


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, s: AsyncSession = Depends(get_session)):
    a = await s.get(Agent, agent_id)
    if not a:
        raise HTTPException(404)
    await s.delete(a)
    await s.commit()
