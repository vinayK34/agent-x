"""FastAPI app + lifespan that boots channel workers."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import agents as agents_api
from app.api import meta as meta_api
from app.api import runs as runs_api
from app.api import workflows as workflows_api
from app.api import ws as ws_api
from app.channels import REGISTRY as CHANNEL_REGISTRY
from app.channels.base import InboundMessage
from app.config import get_settings
from app.db import init_db, session_scope
from app.models.agent import Agent
from app.models.message import Message
from app.models.workflow import Workflow
from app.runtime import run_workflow
from app.seeds.templates import seed_if_empty

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
log = logging.getLogger("agentx")


# ---- inbound channel message → runtime ----------------------------------------
async def _on_channel_message(adapter, msg: InboundMessage) -> None:
    """Resolve a channel message to the right entrypoint and run it.

    Strategy: if exactly one workflow has an agent on this channel as entrypoint,
    run that workflow. Otherwise, find the first agent bound to this channel and
    answer directly via the Concierge pattern.
    """
    async with session_scope() as s:
        # find an agent listening on this channel
        result = await s.execute(select(Agent))
        agents = [a for a in result.scalars().all() if msg.channel in (a.channels or [])]
        if not agents:
            await adapter.send(msg.chat_id, "No agent is connected to this channel yet. Configure one in the UI.")
            return
        target_agent = agents[0]

        # find a workflow whose entrypoint is bound to that agent
        wfs = (await s.execute(select(Workflow))).scalars().all()
        target_wf = next(
            (
                wf for wf in wfs
                for n in wf.spec.get("nodes", [])
                if n.get("id") == wf.spec.get("entrypoint") and n.get("agent_id") == target_agent.id
            ),
            None,
        )
        # Persist the inbound message regardless
        s.add(Message(role="user", channel=msg.channel, content=msg.text, to_agent_id=target_agent.id))

    if target_wf:
        run_id = await run_workflow(target_wf.id, msg.text, trigger=msg.channel)
        # Stream the final answer back to the channel when the run completes.
        asyncio.create_task(_relay_when_done(adapter, msg.chat_id, run_id))
    else:
        # Fallback: single-shot agent reply (no workflow). Wrap as a 1-node workflow on the fly.
        from app.runtime.engine import compile_workflow
        spec = {
            "entrypoint": "only",
            "nodes": [{"id": "only", "type": "agent", "agent_id": target_agent.id}],
            "edges": [{"from": "only", "to": "__end__"}],
        }
        async with session_scope() as s:
            wf = Workflow(name=f"__inline_{target_agent.name}", description="auto", spec=spec)
            s.add(wf)
            await s.flush()
            wf_id = wf.id
        run_id = await run_workflow(wf_id, msg.text, trigger=msg.channel)
        asyncio.create_task(_relay_when_done(adapter, msg.chat_id, run_id))


async def _relay_when_done(adapter, chat_id: str, run_id: str) -> None:
    from app.models.run import Run
    for _ in range(120):  # up to ~2 min
        async with session_scope() as s:
            run = await s.get(Run, run_id)
            if run and run.status in {"completed", "error"} or (run and run.status.startswith("guardrail")):
                await adapter.send(chat_id, run.output or run.error or "(no output)")
                return
        await asyncio.sleep(1.0)
    await adapter.send(chat_id, "Timed out waiting for response.")


# ---- lifespan -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await seed_if_empty()

    settings = get_settings()
    adapters: list = []
    for name in settings.enabled_channels:
        Adapter = CHANNEL_REGISTRY.get(name)
        if not Adapter:
            log.warning("channel %s not in registry; skipping", name)
            continue
        adapter = Adapter()

        async def on_msg(m: InboundMessage, _a=adapter):
            await _on_channel_message(_a, m)

        try:
            await adapter.start(on_msg)
            adapters.append(adapter)
        except Exception as e:  # noqa: BLE001
            # A misconfigured or unreachable channel must NEVER prevent the API from booting.
            log.error("channel %s failed to start (%s: %s) — continuing without it", name, type(e).__name__, e)
    log.info("agentx boot complete — channels=%s", [a.name for a in adapters])
    try:
        yield
    finally:
        for a in adapters:
            try:
                await a.stop()
            except Exception:  # noqa: BLE001
                pass


# ---- app ----------------------------------------------------------------------
def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AgentX", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(agents_api.router)
    app.include_router(workflows_api.router)
    app.include_router(runs_api.router)
    app.include_router(meta_api.router)
    app.include_router(ws_api.router)
    return app


app = create_app()
