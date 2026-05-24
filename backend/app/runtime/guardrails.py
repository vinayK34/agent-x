"""Guardrails enforced between node invocations."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GuardrailViolation(Exception):
    code: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}: {self.detail}"


def check_step(state: dict[str, Any], guardrails: dict[str, Any]) -> None:
    if state.get("steps", 0) >= int(guardrails.get("max_steps", 20)):
        raise GuardrailViolation("max_steps", f"exceeded {guardrails.get('max_steps')}")
    if state.get("cost_usd", 0.0) >= float(guardrails.get("max_cost_usd", 1.0)):
        raise GuardrailViolation("max_cost_usd", f"exceeded ${guardrails.get('max_cost_usd')}")


def check_output(text: str, guardrails: dict[str, Any]) -> None:
    for pattern in guardrails.get("denylist_regex") or []:
        try:
            if re.search(pattern, text or "", flags=re.IGNORECASE):
                raise GuardrailViolation("denylist", f"matched /{pattern}/")
        except re.error:
            continue
