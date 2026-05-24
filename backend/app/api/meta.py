from __future__ import annotations

from fastapi import APIRouter

from app.channels import REGISTRY
from app.runtime.tools import list_tools

router = APIRouter(tags=["meta"])


@router.get("/channels")
async def list_channels():
    return [{"name": k} for k in REGISTRY.keys()]


@router.get("/tools")
async def tools():
    return list_tools()


@router.get("/health")
async def health():
    return {"ok": True}
