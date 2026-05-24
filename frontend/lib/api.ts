const BASE = "/api"; // proxied to FastAPI via next.config.js

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  agents: {
    list: () => req<any[]>("/agents"),
    get: (id: string) => req<any>(`/agents/${id}`),
    create: (body: any) => req<any>("/agents", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: any) => req<any>(`/agents/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    remove: (id: string) => req<void>(`/agents/${id}`, { method: "DELETE" }),
  },
  workflows: {
    list: () => req<any[]>("/workflows"),
    get: (id: string) => req<any>(`/workflows/${id}`),
    create: (body: any) => req<any>("/workflows", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: any) => req<any>(`/workflows/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    remove: (id: string) => req<void>(`/workflows/${id}`, { method: "DELETE" }),
  },
  runs: {
    list: () => req<any[]>("/runs"),
    get: (id: string) => req<any>(`/runs/${id}`),
    messages: (id: string) => req<any[]>(`/runs/${id}/messages`),
    start: (workflow_id: string, input: string) =>
      req<any>("/runs", { method: "POST", body: JSON.stringify({ workflow_id, input }) }),
  },
  tools: () => req<any[]>("/tools"),
  channels: () => req<any[]>("/channels"),
};
