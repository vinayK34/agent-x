"""Built-in tool registry. Adding a tool = adding a function and registering it.

Tools are intentionally side-effect-light and dependency-free so the demo works
without external API keys beyond the LLM provider.
"""
from __future__ import annotations

import ast
import operator as op
from datetime import datetime
from typing import Any, Awaitable, Callable

import httpx

ToolFn = Callable[[dict[str, Any]], Awaitable[str]]


# ---------- web_search (DuckDuckGo Instant Answer — no key required) ----------
async def web_search(args: dict[str, Any]) -> str:
    q = str(args.get("query", "")).strip()
    if not q:
        return "error: missing 'query'"
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(
            "https://api.duckduckgo.com/",
            params={"q": q, "format": "json", "no_redirect": 1, "no_html": 1},
        )
    data = r.json()
    parts = []
    if data.get("AbstractText"):
        parts.append(data["AbstractText"])
    for t in data.get("RelatedTopics", [])[:5]:
        if isinstance(t, dict) and t.get("Text"):
            parts.append("- " + t["Text"])
    return "\n".join(parts) or "no results"


# ---------- calc (safe arithmetic) ----------
_SAFE_BINOPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
        return _SAFE_BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand)
    raise ValueError("unsupported expression")


async def calc(args: dict[str, Any]) -> str:
    expr = str(args.get("expr", ""))
    try:
        return str(_eval(ast.parse(expr, mode="eval").body))
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


# ---------- now ----------
async def now(_: dict[str, Any]) -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------- registry ----------
REGISTRY: dict[str, dict[str, Any]] = {
    "web_search": {
        "fn": web_search,
        "description": "Search the public web (DuckDuckGo). Args: {query: string}",
        "schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    "calc": {
        "fn": calc,
        "description": "Evaluate a basic arithmetic expression. Args: {expr: string}",
        "schema": {"type": "object", "properties": {"expr": {"type": "string"}}, "required": ["expr"]},
    },
    "now": {
        "fn": now,
        "description": "Return current UTC time. No args.",
        "schema": {"type": "object", "properties": {}},
    },
}


def get_tool(name: str) -> ToolFn | None:
    entry = REGISTRY.get(name)
    return entry["fn"] if entry else None


def list_tools() -> list[dict[str, Any]]:
    return [{"name": k, "description": v["description"]} for k, v in REGISTRY.items()]
