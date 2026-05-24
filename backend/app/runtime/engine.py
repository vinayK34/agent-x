"""LangGraph compiler + executor.

A WorkflowSpec (the JSON the UI emits) is compiled into a StateGraph 1:1:
  - node {"type": "agent"}     -> graph node that invokes an LLM with the agent's config
  - node {"type": "condition"} -> conditional edge using a safe-evaluated expression
  - edges become add_edge / add_conditional_edges calls

Every meaningful event is published on the EventBus so the UI monitor stays live.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.events import bus
from app.models.agent import Agent
from app.models.message import Message
from app.models.run import Run, RunEvent
from app.models.workflow import Workflow
from app.runtime.guardrails import GuardrailViolation, check_output, check_step
from app.runtime.memory import load_memory
from app.runtime.state import RunState
from app.runtime.tools import REGISTRY as TOOLS

log = logging.getLogger(__name__)

# Approximate token pricing (USD / 1K tokens). Override per-model as needed.
_PRICING = {
    "gpt-4o-mini":   {"in": 0.00015, "out": 0.00060},
    "gpt-4o":        {"in": 0.0025,  "out": 0.01},
    "gpt-3.5-turbo": {"in": 0.0005,  "out": 0.0015},
}


def _price(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = _PRICING.get(model, _PRICING["gpt-4o-mini"])
    return (prompt_tokens * p["in"] + completion_tokens * p["out"]) / 1000.0


# ----- safe condition evaluator (no eval) --------------------------------------
import ast


def _safe_eval(expr: str, ctx: dict[str, Any]) -> bool:
    """Evaluate a tiny boolean expression against `ctx`. Supports:
    names, attribute access, comparisons, and/or/not, len(), int/str/float literals.
    """
    tree = ast.parse(expr, mode="eval")

    def ev(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return ctx.get(node.id)
        if isinstance(node, ast.Attribute):
            return getattr(ev(node.value), node.attr, None) if not isinstance(ev(node.value), dict) else ev(node.value).get(node.attr)
        if isinstance(node, ast.Subscript):
            return ev(node.value)[ev(node.slice)]
        if isinstance(node, ast.BoolOp):
            vals = [ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand)
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op_node, right_node in zip(node.ops, node.comparators):
                right = ev(right_node)
                ok = {
                    ast.Eq: left == right, ast.NotEq: left != right,
                    ast.Lt: left < right, ast.LtE: left <= right,
                    ast.Gt: left > right, ast.GtE: left >= right,
                    ast.In: left in right, ast.NotIn: left not in right,
                }[type(op_node)]
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
            return len(ev(node.args[0]) or "")
        raise ValueError(f"unsupported expression node: {type(node).__name__}")

    try:
        return bool(ev(tree))
    except Exception:
        return False


# ----- LLM call (OpenAI-compatible) --------------------------------------------
async def _llm_call(
    agent: Agent,
    history: list[dict[str, str]],
    *,
    run_id: str,
) -> tuple[str, list[dict[str, Any]], int, int]:
    """Returns (content, tool_calls, prompt_tokens, completion_tokens)."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    settings = get_settings()
    if not settings.openai_api_key:
        # Deterministic fallback so the demo still runs without an API key.
        # Shows in the UI as a clearly-tagged stub.
        stub = f"[stub:{agent.name}] " + (history[-1]["content"] if history else "")
        return stub[:500], [], 0, 0

    # Bind tools the agent is allowed to use
    tools_spec = (
        [
            {
                "type": "function",
                "function": {
                    "name": t,
                    "description": TOOLS[t]["description"],
                    "parameters": TOOLS[t]["schema"],
                },
            }
            for t in (agent.tools or [])
            if t in TOOLS
        ]
        if not settings.disable_tool_calling
        else []
    )

    llm = ChatOpenAI(
        model=agent.model or settings.default_model,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    bound_llm = llm.bind(tools=tools_spec) if tools_spec else llm

    lc_msgs: list[Any] = [SystemMessage(content=agent.system_prompt or f"You are {agent.name}.")]
    for m in history:
        if m["role"] == "user":
            lc_msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_msgs.append(AIMessage(content=m["content"]))
        elif m["role"] == "system":
            lc_msgs.append(SystemMessage(content=m["content"]))

    try:
        resp = await bound_llm.ainvoke(lc_msgs)
    except Exception as e:  # noqa: BLE001
        # Some OpenAI-compatible servers (e.g. vanilla vLLM without
        # --enable-auto-tool-choice) reject any `tools` payload with a 400.
        # If that happens, latch the flag for the remainder of this process
        # and retry once without tools so the conversation still progresses.
        msg = str(e).lower()
        tool_unsupported = tools_spec and (
            "tool choice" in msg
            or "tool-call" in msg
            or "tool_choice" in msg
            or "enable-auto-tool-choice" in msg
        )
        if not tool_unsupported:
            raise
        settings.disable_tool_calling = True  # remember for subsequent calls
        log.warning(
            "llm endpoint rejected tool-calling — disabling tools for this process and retrying without them"
        )
        resp = await llm.ainvoke(lc_msgs)
        tool_calls = []
        content = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
        usage = getattr(resp, "response_metadata", {}).get("token_usage", {}) or {}
        return content, tool_calls, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))

    content = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    tool_calls = getattr(resp, "tool_calls", []) or []
    usage = getattr(resp, "response_metadata", {}).get("token_usage", {}) or {}
    return content, tool_calls, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))


# ----- node factory ------------------------------------------------------------
def _make_agent_node(agent_id: str, node_id: str):
    async def node(state: RunState) -> dict[str, Any]:
        check_step(state, _resolve_guardrails(state))
        async with session_scope() as s:
            agent = await s.get(Agent, agent_id)
            if not agent:
                raise RuntimeError(f"agent {agent_id} not found")

            history = await load_memory(s, run_id=state.get("run_id"), strategy=agent.memory or {})
            # Append latest input as the active user turn for the agent
            user_turn = state.get("input") or (state.get("messages") or [{}])[-1].get("content", "")
            if user_turn:
                history.append({"role": "user", "content": user_turn})

            await bus.publish(
                "monitor",
                {"type": "node_start", "run_id": state["run_id"], "node": node_id, "agent": agent.name, "ts": time.time()},
            )

            content, tool_calls, p_tok, c_tok = await _llm_call(agent, history, run_id=state["run_id"])

            # Tool execution loop (1 hop — keep simple; LangGraph could nest a ReAct subgraph)
            for tc in tool_calls or []:
                tname = tc.get("name") or tc.get("function", {}).get("name")
                targs = tc.get("args") or json.loads(tc.get("function", {}).get("arguments") or "{}")
                fn = TOOLS.get(tname, {}).get("fn")
                if not fn:
                    continue
                await bus.publish("monitor", {"type": "tool_call", "run_id": state["run_id"], "node": node_id, "tool": tname, "args": targs})
                try:
                    result = await fn(targs)
                except Exception as e:  # noqa: BLE001
                    result = f"error: {e}"
                await bus.publish("monitor", {"type": "tool_result", "run_id": state["run_id"], "node": node_id, "tool": tname, "result": result[:500]})
                content = (content + f"\n\n[{tname}] {result}").strip()

            cost = _price(agent.model, p_tok, c_tok)
            check_output(content, _resolve_guardrails(state))

            # Persist messages
            msg = Message(
                run_id=state["run_id"],
                from_agent_id=agent.id,
                role="assistant",
                content=content,
                tool_calls=tool_calls or None,
            )
            s.add(msg)
            s.add(RunEvent(run_id=state["run_id"], type="node_end", payload={"node": node_id, "agent": agent.name, "cost": cost}))

            await bus.publish(
                "monitor",
                {"type": "message", "run_id": state["run_id"], "node": node_id, "agent": agent.name, "content": content, "cost_usd": cost},
            )

        return {
            "messages": [{"role": "assistant", "content": content}],
            "steps": state.get("steps", 0) + 1,
            "cost_usd": state.get("cost_usd", 0.0) + cost,
            "tokens": state.get("tokens", 0) + p_tok + c_tok,
            "input": content,  # feeds the next node
        }

    return node


def _resolve_guardrails(state: RunState) -> dict[str, Any]:
    settings = get_settings()
    return {
        "max_steps": settings.default_max_steps,
        "max_cost_usd": settings.default_max_cost_usd,
        "denylist_regex": [],
    }


# ----- compile -----------------------------------------------------------------
def compile_workflow(spec: dict[str, Any]):
    """Compile a workflow spec into a LangGraph StateGraph."""
    g = StateGraph(RunState)

    nodes = {n["id"]: n for n in spec["nodes"]}
    for n in spec["nodes"]:
        if n["type"] == "agent":
            g.add_node(n["id"], _make_agent_node(n["agent_id"], n["id"]))
        elif n["type"] == "condition":
            # condition nodes are pure routers; we still add a pass-through so edges can chain
            async def passthrough(state: RunState) -> dict[str, Any]:
                return {}
            g.add_node(n["id"], passthrough)
        else:
            raise ValueError(f"unknown node type: {n['type']}")

    g.add_edge(START, spec["entrypoint"])

    # Group edges by source
    by_src: dict[str, list[dict[str, Any]]] = {}
    for e in spec["edges"]:
        by_src.setdefault(e["from"], []).append(e)

    for src, edges in by_src.items():
        node = nodes.get(src, {})
        if node.get("type") == "condition" or any("when" in e for e in edges):
            # conditional routing
            expr = node.get("expr", "True")

            def make_router(_expr: str, _edges: list[dict[str, Any]]):
                def route(state: RunState) -> str:
                    val = _safe_eval(_expr, dict(state))
                    target_when_true = next((e["to"] for e in _edges if str(e.get("when")).lower() == "true"), None)
                    target_when_false = next((e["to"] for e in _edges if str(e.get("when")).lower() == "false"), None)
                    if val and target_when_true:
                        return target_when_true if target_when_true != "__end__" else END
                    if (not val) and target_when_false:
                        return target_when_false if target_when_false != "__end__" else END
                    # fallback: first edge
                    first = _edges[0]["to"]
                    return first if first != "__end__" else END
                return route

            mapping = {e["to"] if e["to"] != "__end__" else END: (e["to"] if e["to"] != "__end__" else END) for e in edges}
            g.add_conditional_edges(src, make_router(expr, edges), mapping)
        else:
            # straight edges
            for e in edges:
                target = END if e["to"] == "__end__" else e["to"]
                g.add_edge(src, target)

    return g.compile()


# ----- public entrypoint -------------------------------------------------------
async def run_workflow(workflow_id: str, user_input: str, *, trigger: str = "manual") -> str:
    """Start a run. Returns run_id immediately; execution continues in background."""
    async with session_scope() as s:
        wf = await s.get(Workflow, workflow_id)
        if not wf:
            raise ValueError(f"workflow {workflow_id} not found")
        run = Run(workflow_id=workflow_id, status="running", trigger=trigger, input=user_input)
        s.add(run)
        await s.flush()
        run_id = run.id
        # store user message
        s.add(Message(run_id=run_id, role="user", content=user_input, channel=trigger))

    asyncio.create_task(_execute(workflow_id, run_id, user_input))
    return run_id


async def _execute(workflow_id: str, run_id: str, user_input: str) -> None:
    try:
        async with session_scope() as s:
            wf = await s.get(Workflow, workflow_id)
            spec = wf.spec
        graph = compile_workflow(spec)

        await bus.publish("monitor", {"type": "run_start", "run_id": run_id, "workflow_id": workflow_id, "input": user_input})

        final_state: dict[str, Any] = {}
        async for event in graph.astream(
            {"run_id": run_id, "workflow_id": workflow_id, "input": user_input, "messages": [{"role": "user", "content": user_input}], "scratch": {}, "steps": 0, "cost_usd": 0.0, "tokens": 0},
            {"recursion_limit": 25},
        ):
            for node_id, node_state in event.items():
                final_state.update(node_state or {})

        final_output = final_state.get("input") or ""
        async with session_scope() as s:
            run = await s.get(Run, run_id)
            run.status = "completed"
            run.output = final_output
            run.cost_usd = float(final_state.get("cost_usd", 0.0))
            run.tokens = int(final_state.get("tokens", 0))
            run.finished_at = datetime.utcnow()

        await bus.publish("monitor", {"type": "run_end", "run_id": run_id, "output": final_output})

    except GuardrailViolation as g:
        await _fail(run_id, f"guardrail:{g.code}", str(g))
    except Exception as e:  # noqa: BLE001
        await _fail(run_id, "error", str(e))


async def _fail(run_id: str, status: str, error: str) -> None:
    async with session_scope() as s:
        run = await s.get(Run, run_id)
        if run:
            run.status = status
            run.error = error
            run.finished_at = datetime.utcnow()
    await bus.publish("monitor", {"type": "run_failed", "run_id": run_id, "status": status, "error": error})
