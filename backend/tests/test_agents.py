import pytest


@pytest.mark.asyncio
async def test_agent_crud(client):
    payload = {
        "name": "TestBot",
        "role": "tester",
        "system_prompt": "you test things",
        "model": "gpt-4o-mini",
        "tools": ["now"],
    }
    r = await client.post("/agents", json=payload)
    assert r.status_code == 201, r.text
    agent = r.json()
    assert agent["name"] == "TestBot"

    r = await client.get(f"/agents/{agent['id']}")
    assert r.status_code == 200

    payload["role"] = "renamed"
    r = await client.put(f"/agents/{agent['id']}", json=payload)
    assert r.json()["role"] == "renamed"

    r = await client.get("/agents")
    assert any(a["id"] == agent["id"] for a in r.json())

    r = await client.delete(f"/agents/{agent['id']}")
    assert r.status_code == 204
