"""Critical-path: compile a workflow and execute it with the stub LLM path
(triggered when OPENAI_API_KEY is empty). Verifies graph wiring + persistence
without external network calls.
"""
import asyncio

import pytest


@pytest.mark.asyncio
async def test_two_agent_workflow_run(client):
    # create two agents
    a1 = (await client.post("/agents", json={"name": "A1", "system_prompt": "p1"})).json()
    a2 = (await client.post("/agents", json={"name": "A2", "system_prompt": "p2"})).json()

    spec = {
        "entrypoint": "n1",
        "nodes": [
            {"id": "n1", "type": "agent", "agent_id": a1["id"]},
            {"id": "n2", "type": "agent", "agent_id": a2["id"]},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "__end__"},
        ],
    }
    wf = (await client.post("/workflows", json={"name": "wf1", "spec": spec})).json()

    r = await client.post("/runs", json={"workflow_id": wf["id"], "input": "hello"})
    assert r.status_code == 201, r.text
    run = r.json()

    # wait for completion (stub LLM is fast)
    for _ in range(30):
        await asyncio.sleep(0.1)
        cur = (await client.get(f"/runs/{run['id']}")).json()
        if cur["status"] in {"completed", "error"} or cur["status"].startswith("guardrail"):
            break

    assert cur["status"] == "completed", cur
    msgs = (await client.get(f"/runs/{run['id']}/messages")).json()
    # user + 2 assistant turns
    assert len(msgs) >= 3
    assert any(m["role"] == "assistant" for m in msgs)
