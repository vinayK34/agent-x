# Architecture

This document explains **why** AgentX is built the way it is, the data model, and the runtime sequence. The goal is that a senior reviewer can predict where any feature lives before opening a file.

## 1. Guiding principles

1. **Local-first, single command.** No cloud dependencies are required to demo. Cloud is a deployment target, not a prerequisite.
2. **The graph the user draws is the graph that runs.** Visual builder nodes/edges map 1:1 onto LangGraph nodes/edges. No translation layer that can drift.
3. **Layer boundaries are real.** API → Runtime → Persistence is a one-way dependency. The event bus is the only path back upstream (for live monitoring).
4. **Channels are plugins.** Telegram today, Slack/WhatsApp tomorrow, each behind a single ABC.
5. **Everything observable.** Every node entry/exit, every tool call, every LLM token is an event. The UI is just a subscriber.

## 2. Component map

```
┌─ frontend (Next.js) ───────────────────────────────────────┐
│  pages: /agents /workflows /workflows/[id] /runs /monitor  │
│  components: WorkflowBuilder (React Flow), LiveLog, Forms  │
│  lib: api.ts (fetch), ws.ts (WebSocket client)             │
└────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + WS
                              ▼
┌─ backend/app ──────────────────────────────────────────────┐
│  main.py        ASGI app, lifespan boots channel workers   │
│  config.py      Pydantic settings (env)                    │
│  db.py          Engine, session, init_db, seed             │
│                                                            │
│  api/                                                      │
│    agents.py        CRUD /agents                           │
│    workflows.py     CRUD /workflows                        │
│    runs.py          POST /runs (start) + GET history       │
│    channels.py      list channels, send/test               │
│    ws.py            /ws/monitor (event stream)             │
│                                                            │
│  runtime/                                                  │
│    engine.py        compile(WorkflowSpec) → LangGraph      │
│    tools.py         Tool registry (web_search, calc, ...)  │
│    memory.py        window / summary strategies            │
│    guardrails.py    max_steps, cost ceiling, denylist      │
│    state.py         TypedDict RunState                     │
│                                                            │
│  channels/                                                 │
│    base.py          ChannelAdapter ABC                     │
│    telegram.py      long-polling worker                    │
│    __init__.py      REGISTRY                               │
│                                                            │
│  models/        SQLAlchemy ORM (Agent, Workflow, Run, Msg) │
│  seeds/         templates.py — 2 workflow templates        │
│  events.py      asyncio pub/sub (EventBus)                 │
└────────────────────────────────────────────────────────────┘
```

## 3. Data model

```
Agent ─┐
       ├─< WorkflowNode >─ Workflow
       │
       └─< Message >── Run >── Workflow
                              │
                              └─ events (in-memory + persisted as RunEvent)
```

Tables:

- **agents** — id, name, role, system_prompt, model, temperature, tools (JSON), memory (JSON), schedule, guardrails (JSON), channels (JSON), created_at
- **workflows** — id, name, description, spec (JSON: nodes + edges + entrypoint), created_at
- **runs** — id, workflow_id, status, input, output, cost_usd, tokens, started_at, finished_at
- **messages** — id, run_id, from_agent_id, to_agent_id, role, content, tool_calls (JSON), created_at
- **run_events** — id, run_id, type, payload (JSON), created_at  *(append-only, replays the live monitor)*

JSON columns are deliberate: agent configuration evolves fast, and a wide schema would require Alembic migrations for every new dimension.

## 4. Runtime sequence (a single run)

```
UI ──POST /runs──▶ api.runs ──▶ runtime.engine.run_workflow(workflow_id, input)
                                       │
                                       │ 1. load WorkflowSpec from DB
                                       │ 2. compile to LangGraph (cached)
                                       │ 3. stream graph events:
                                       │       on_node_start  ─┐
                                       │       on_tool_call    ├─▶ EventBus.publish
                                       │       on_llm_token    │       │
                                       │       on_node_end    ─┘       ▼
                                       │                          WS /ws/monitor
                                       │ 4. persist Messages + RunEvents
                                       │ 5. write Run.status/output
                                       ▼
                                  UI receives run_id; live updates over WS
```

When a Telegram message arrives, `channels.telegram` calls the same `run_workflow` entrypoint with the inbound text — the runtime is channel-agnostic.

## 5. Workflow spec (the JSON the UI emits)

```json
{
  "name": "Research → Writer",
  "entrypoint": "researcher",
  "nodes": [
    {"id": "researcher", "agent_id": "...", "type": "agent"},
    {"id": "writer",     "agent_id": "...", "type": "agent"},
    {"id": "review",     "type": "condition", "expr": "len(state.draft) > 100"}
  ],
  "edges": [
    {"from": "researcher", "to": "writer"},
    {"from": "writer",     "to": "review"},
    {"from": "review",     "to": "writer",  "when": "false"},
    {"from": "review",     "to": "__end__", "when": "true"}
  ]
}
```

`engine.compile()` walks this spec and builds a `StateGraph`. `condition` nodes become LangGraph **conditional edges** — that is how feedback loops are expressed without any custom interpreter.

## 6. Memory strategies

| Strategy | Implementation |
|---|---|
| `none` | Each call gets only the system prompt + current message |
| `window:N` | Keep last N (user, assistant) turns from the run's `messages` table |
| `summary` | After N turns, summarize older history with a cheap model and prepend |

Memory is read fresh on each node entry, so changing strategy never requires migration.

## 7. Guardrails

Enforced inside `runtime.engine` between node invocations:

- `max_steps` — abort with `status=guardrail_max_steps`
- `max_cost_usd` — track per-run cost from LLM responses; abort if exceeded
- `denylist_regex` — applied to outbound tool args and final outputs

Failures become `RunEvent(type="guardrail_triggered", ...)` and are visible in the monitor.

## 8. Channel adapter contract

```python
class ChannelAdapter(ABC):
    name: str
    async def start(self, on_message: Callable[[InboundMessage], Awaitable[None]]) -> None: ...
    async def stop(self) -> None: ...
    async def send(self, chat_id: str, text: str) -> None: ...
```

`main.py`'s lifespan starts every adapter listed in `settings.enabled_channels`. The `on_message` callback resolves the target agent (by channel binding) and calls `run_workflow` or a single-agent reply path.

## 9. Trade-offs I made consciously

| Trade-off | Decision | Cost |
|---|---|---|
| LangGraph vs. CrewAI/AutoGen | LangGraph | Slightly more wiring than CrewAI, but graphs map to the UI cleanly and feedback loops are first-class |
| SQLite vs. Postgres | SQLite | Single-file local; not suitable for multi-writer prod — solved by `DATABASE_URL` swap |
| Long-polling vs. webhooks | Long-polling for Telegram | Slightly higher idle traffic; pays for itself by removing ngrok from setup |
| In-process EventBus vs. Redis | In-process | Won't scale across replicas; replaced by Redis pub/sub when we go multi-instance |
| Monorepo vs. split repos | Monorepo | Shared types are easier; CI is slightly heavier |

## 10. What I would build next

- Replace in-process EventBus with Redis when going multi-replica.
- Add an **evaluation harness**: replay logged runs against new prompts to detect regressions.
- Persist vector memory (pgvector) for the `summary` strategy.
- RBAC + per-org tenancy.
- OpenTelemetry traces exported to Tempo/Jaeger.
