# Walkthrough — how to present AgentX

A 1-page cheat sheet to walk a reviewer through the project. Read top to bottom.

## 1. The pitch (30 seconds)

> "AgentX is a local, single-command platform where a non-engineer can **create AI agents**, **wire them into workflows** visually, **run them on a real LangGraph runtime**, and **chat with the swarm over Telegram** — while watching every inter-agent message, tool call, and dollar of cost live in the UI."

## 2. Demo flow (do this in order)

| Step | Action | What it proves |
|------|--------|----------------|
| 1 | `cp .env.example .env`, paste `OPENAI_API_KEY` and `TELEGRAM_BOT_TOKEN`, `docker compose up` | **Single-command setup** ✅ |
| 2 | Open `http://localhost:3000` → Dashboard | Stats pulled from the running API |
| 3 | Go to **Agents** → click *Concierge* | Show all 10+ configurable dimensions in one form |
| 4 | Go to **Workflows** → open *Research → Writer* | React Flow renders the seeded graph; show the feedback loop edge |
| 5 | Click **▶ Run** with input *"Write a 150-word brief on AgentX"* | Browser routes to **Live monitor** |
| 6 | Watch the monitor | `run_start → node_start(Researcher) → tool_call(web_search) → tool_result → message → node_start(Writer) → message → run_end` |
| 7 | Open Telegram, DM your bot *"What time is it?"* | Concierge replies via the **same runtime** — proves channel adapter wiring |
| 8 | Go to **Runs** → click the Telegram-triggered run | Persisted message history, visible in UI ✅ |

## 3. Code walkthrough (in this order)

```
README.md                              # the pitch and run instructions
docs/ARCHITECTURE.md                   # the why and the diagrams
backend/app/runtime/engine.py          # ← the heart: spec → LangGraph
backend/app/runtime/tools.py           # registry pattern for tools
backend/app/channels/base.py           # ABC — proof channels are pluggable
backend/app/channels/telegram.py       # concrete implementation
backend/app/main.py                    # lifespan: boots channels, mounts API
backend/app/seeds/templates.py         # the 2 required templates
frontend/app/workflows/[id]/page.tsx   # React Flow editor; node/edge ↔ spec
frontend/app/monitor/page.tsx          # WebSocket subscriber
backend/tests/                         # critical-path tests
```

## 4. Requirement → file mapping (so you can answer any question instantly)

| Challenge requirement | Where it lives |
|---|---|
| Agent CRUD (name, role, prompt, model, tools, channels) | `backend/app/api/agents.py`, `backend/app/models/agent.py`, `frontend/app/agents/page.tsx` |
| Agent config: schedules, memory, skills, interaction rules, guardrails | Same `Agent` model — JSON columns; `runtime/memory.py`, `runtime/guardrails.py` |
| Visual workflow builder w/ conditions + feedback loops | `frontend/app/workflows/[id]/page.tsx` + `backend/app/runtime/engine.py` (`add_conditional_edges`) |
| At least 2 pre-built workflow templates | `backend/app/seeds/templates.py` → `TEMPLATES` |
| External channel integration (Telegram) | `backend/app/channels/telegram.py` |
| Live monitoring (logs, inter-agent messages, token/cost) | `backend/app/events.py` + `backend/app/api/ws.py` + `frontend/app/monitor/page.tsx` |
| Agents communicate asynchronously | LangGraph `astream` + `asyncio.create_task` in `engine.run_workflow` |
| Message history persisted + visible in UI | `models/message.py`, `/runs/{id}/messages`, `frontend/app/runs/[id]/page.tsx` |
| Real runtime executing real tools | `runtime/engine.py` invokes `langchain_openai` w/ tool binding; tool fns in `runtime/tools.py` |
| Single setup command | `docker compose up --build` |
| Architecture diagram + setup + runtime justification | `README.md`, `docs/ARCHITECTURE.md` |
| Tests for critical paths | `backend/tests/test_agents.py`, `test_workflow.py`, `test_telegram.py` |
| Instructions for adding new templates / channels | `README.md` § "Extending the platform" |

## 5. Likely interview questions and crisp answers

**Q. Why LangGraph and not CrewAI/AutoGen?**
A. Because the *workflow the user draws* must be the *graph that runs*. LangGraph models nodes + conditional edges + cycles natively, so the compiler in `runtime/engine.py` is ~20 lines. CrewAI and AutoGen are more opinionated about roles and turn-taking — they fight a free-form visual builder.

**Q. How would you scale this past one machine?**
A. Three changes, all isolated: (1) swap `events.py` for Redis pub/sub, (2) flip `DATABASE_URL` to Postgres, (3) move the channel worker into its own process consuming a job queue. The API and runtime don't change.

**Q. How do agents talk to each other?**
A. Through the shared `RunState` in LangGraph — each node's output is appended to `messages` and stored in `state.input` for the next node. Every hop also writes a `Message` row, so the UI sees the conversation regardless of which agents participated.

**Q. What happens if an LLM call fails or loops?**
A. Three layers: `guardrails.py` enforces `max_steps` and `max_cost_usd` between nodes; LangGraph's `recursion_limit` (set to 25 in `engine.py`) is the hard ceiling; failures land in the run with `status=error` and a `RunEvent`, which the monitor renders in red.

**Q. Why long-polling Telegram?**
A. Webhooks need a public URL — ngrok in a local demo is friction. Long-polling is one line and works behind any NAT.

**Q. What's the biggest thing you cut?**
A. A proper summarizer for the `summary` memory strategy and pgvector retrieval. The interface is in place (`memory.py`), but the implementation falls back to a wider window. It's the single highest-leverage thing to ship next.

## 6. What I'd build next (already in `docs/ARCHITECTURE.md` §10)

1. Redis-backed event bus + Postgres for multi-replica deployment.
2. Replay-based eval harness so prompt edits never silently regress.
3. pgvector for true `summary` memory.
4. OpenTelemetry tracing.
5. RBAC + multi-tenancy.
