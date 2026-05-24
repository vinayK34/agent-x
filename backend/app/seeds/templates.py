"""Seed data + pre-built workflow templates.

Two templates as required by the spec (success criteria > Functional).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db import session_scope
from app.models.agent import Agent
from app.models.workflow import Workflow


# ---------- agents ----------
SEED_AGENTS: list[dict[str, Any]] = [
    {
        "name": "Concierge",
        "role": "Customer-facing router",
        "avatar": "ðŸŽ©",
        "system_prompt": (
            "You are AgentX's concierge. You greet users on Telegram, decide whether to answer directly "
            "or delegate to a workflow, and keep responses concise (â‰¤3 sentences)."
        ),
        "model": "",  # uses DEFAULT_MODEL from .env
        "tools": ["now"],
        "channels": ["telegram"],
        "skills": ["routing", "small_talk"],
    },
    {
        "name": "Researcher",
        "role": "Gathers facts from the web",
        "avatar": "ðŸ”Ž",
        "system_prompt": (
            "You are a precise researcher. Use the web_search tool to gather 3â€“5 facts about the topic. "
            "Reply with a tight bullet list. Cite no opinions."
        ),
        "model": "",  # uses DEFAULT_MODEL from .env
        "tools": ["web_search", "now"],
        "skills": ["research"],
    },
    {
        "name": "Writer",
        "role": "Turns facts into prose",
        "avatar": "âœï¸",
        "system_prompt": (
            "You write tight, engaging prose based on the bullets you receive. "
            "Aim for â‰¤150 words. Plain language, no marketing fluff."
        ),
        "model": "",  # uses DEFAULT_MODEL from .env
        "tools": [],
        "skills": ["writing"],
    },
    {
        "name": "Summarizer",
        "role": "Condenses long output for delivery",
        "avatar": "ðŸ“",
        "system_prompt": "Summarize the prior message in 2 sentences for a busy reader.",
        "model": "",  # uses DEFAULT_MODEL from .env
        "tools": [],
        "skills": ["summarization"],
    },
    {
        "name": "Triage",
        "role": "Decides which specialist handles a request",
        "avatar": "ðŸ§­",
        "system_prompt": (
            "Classify the user's request into one of: 'numeric', 'research', 'other'. "
            "Reply with only the single word label."
        ),
        "model": "",  # uses DEFAULT_MODEL from .env
        "tools": [],
        "skills": ["routing"],
    },
    {
        "name": "Calculator",
        "role": "Numeric specialist",
        "avatar": "ðŸ§®",
        "system_prompt": "When the user asks something numeric, call the calc tool with a clean expression and return the result.",
        "model": "",  # uses DEFAULT_MODEL from .env
        "tools": ["calc"],
        "skills": ["math"],
    },
]


def _agent_id_by_name(agents: dict[str, str], name: str) -> str:
    return agents[name]


def _research_writer(agents: dict[str, str]) -> dict[str, Any]:
    return {
        "name": "Research â†’ Writer",
        "description": "Researcher gathers facts; Writer crafts a brief. A condition loops back if the draft is too short.",
        "spec": {
            "entrypoint": "researcher",
            "nodes": [
                {"id": "researcher", "type": "agent", "agent_id": agents["Researcher"]},
                {"id": "writer",     "type": "agent", "agent_id": agents["Writer"]},
                {"id": "check",      "type": "condition", "expr": "len(input) > 200"},
            ],
            "edges": [
                {"from": "researcher", "to": "writer"},
                {"from": "writer",     "to": "check"},
                {"from": "check",      "to": "__end__", "when": "true"},
                {"from": "check",      "to": "writer",  "when": "false"},
            ],
        },
    }


def _triage_specialist_summarizer(agents: dict[str, str]) -> dict[str, Any]:
    return {
        "name": "Triage â†’ Specialist â†’ Summarizer",
        "description": "Triage routes to Calculator or Researcher, then Summarizer condenses the answer.",
        "spec": {
            "entrypoint": "triage",
            "nodes": [
                {"id": "triage",      "type": "agent", "agent_id": agents["Triage"]},
                {"id": "route",       "type": "condition", "expr": "'numeric' in (input or '').lower()"},
                {"id": "calculator",  "type": "agent", "agent_id": agents["Calculator"]},
                {"id": "researcher",  "type": "agent", "agent_id": agents["Researcher"]},
                {"id": "summarizer",  "type": "agent", "agent_id": agents["Summarizer"]},
            ],
            "edges": [
                {"from": "triage",      "to": "route"},
                {"from": "route",       "to": "calculator", "when": "true"},
                {"from": "route",       "to": "researcher", "when": "false"},
                {"from": "calculator",  "to": "summarizer"},
                {"from": "researcher",  "to": "summarizer"},
                {"from": "summarizer",  "to": "__end__"},
            ],
        },
    }


TEMPLATES = {
    "research_writer": _research_writer,
    "triage_specialist_summarizer": _triage_specialist_summarizer,
}


async def seed_if_empty() -> None:
    async with session_scope() as s:
        existing = (await s.execute(select(Agent))).scalars().first()
        if existing:
            return

        name_to_id: dict[str, str] = {}
        for cfg in SEED_AGENTS:
            a = Agent(**cfg)
            s.add(a)
            await s.flush()
            name_to_id[a.name] = a.id

        for builder in TEMPLATES.values():
            spec = builder(name_to_id)
            s.add(Workflow(name=spec["name"], description=spec["description"], spec=spec["spec"]))
