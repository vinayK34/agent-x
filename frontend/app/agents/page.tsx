"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

const empty = {
  name: "",
  role: "",
  avatar: "🤖",
  system_prompt: "",
  model: "", // empty → backend uses DEFAULT_MODEL from .env
  temperature: 0.3,
  max_tokens: 1024,
  tools: [] as string[],
  memory: { strategy: "window", n: 6 },
  schedule: null as string | null,
  skills: [] as string[],
  can_talk_to: [] as string[],
  guardrails: { max_steps: 20, max_cost_usd: 1.0, denylist_regex: [] as string[] },
  channels: [] as string[],
};

export default function AgentsPage() {
  const qc = useQueryClient();
  const agents = useQuery({ queryKey: ["agents"], queryFn: api.agents.list });
  const tools = useQuery({ queryKey: ["tools"], queryFn: api.tools });
  const channels = useQuery({ queryKey: ["channels"], queryFn: api.channels });
  const [editing, setEditing] = useState<any | null>(null);

  const save = useMutation({
    mutationFn: (a: any) => (a.id ? api.agents.update(a.id, a) : api.agents.create(a)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      setEditing(null);
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.agents.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-5 space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Agents</h1>
          <button className="btn" onClick={() => setEditing({ ...empty })}>
            + New
          </button>
        </div>
        <div className="space-y-2">
          {agents.data?.map((a: any) => (
            <div
              key={a.id}
              onClick={() => setEditing(a)}
              className={`card cursor-pointer ${editing?.id === a.id ? "ring-1 ring-indigo-500" : ""}`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">{a.avatar}</span>
                <div className="flex-1">
                  <div className="font-medium">{a.name}</div>
                  <div className="text-xs text-white/50">{a.role || "—"}</div>
                </div>
                <span className="text-xs text-white/40">{a.model}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="col-span-7">
        {editing ? (
          <AgentForm
            value={editing}
            tools={tools.data || []}
            channels={channels.data || []}
            onSave={(v) => save.mutate(v)}
            onDelete={editing.id ? () => remove.mutate(editing.id) : undefined}
            onCancel={() => setEditing(null)}
            saving={save.isPending}
          />
        ) : (
          <div className="card text-white/50 text-sm">Select an agent to edit, or click + New.</div>
        )}
      </div>
    </div>
  );
}

function AgentForm({
  value,
  tools,
  channels,
  onSave,
  onDelete,
  onCancel,
  saving,
}: {
  value: any;
  tools: any[];
  channels: any[];
  onSave: (v: any) => void;
  onDelete?: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [v, setV] = useState<any>(value);
  const upd = (k: string, val: any) => setV({ ...v, [k]: val });

  return (
    <div className="card space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Name"><input className="input" value={v.name} onChange={(e) => upd("name", e.target.value)} /></Field>
        <Field label="Avatar"><input className="input" value={v.avatar} onChange={(e) => upd("avatar", e.target.value)} /></Field>
        <Field label="Role"><input className="input" value={v.role} onChange={(e) => upd("role", e.target.value)} /></Field>
        <Field label="Model"><input className="input" value={v.model} onChange={(e) => upd("model", e.target.value)} /></Field>
        <Field label="Temperature"><input type="number" step="0.1" className="input" value={v.temperature} onChange={(e) => upd("temperature", parseFloat(e.target.value))} /></Field>
        <Field label="Max tokens"><input type="number" className="input" value={v.max_tokens} onChange={(e) => upd("max_tokens", parseInt(e.target.value))} /></Field>
      </div>

      <Field label="System prompt">
        <textarea className="input min-h-[120px]" value={v.system_prompt} onChange={(e) => upd("system_prompt", e.target.value)} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Tools">
          <MultiSelect options={tools.map((t) => t.name)} selected={v.tools} onChange={(x) => upd("tools", x)} />
        </Field>
        <Field label="Channels">
          <MultiSelect options={channels.map((c) => c.name)} selected={v.channels} onChange={(x) => upd("channels", x)} />
        </Field>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Field label="Memory strategy">
          <select className="input" value={v.memory?.strategy || "window"} onChange={(e) => upd("memory", { ...v.memory, strategy: e.target.value })}>
            <option value="none">none</option>
            <option value="window">window</option>
            <option value="summary">summary</option>
          </select>
        </Field>
        <Field label="Memory N"><input type="number" className="input" value={v.memory?.n ?? 6} onChange={(e) => upd("memory", { ...v.memory, n: parseInt(e.target.value) })} /></Field>
        <Field label="Schedule (cron)"><input className="input" placeholder="e.g. */15 * * * *" value={v.schedule || ""} onChange={(e) => upd("schedule", e.target.value || null)} /></Field>
      </div>

      <details className="card bg-black/20">
        <summary className="cursor-pointer text-sm text-white/70">Guardrails</summary>
        <div className="grid grid-cols-3 gap-3 mt-3">
          <Field label="Max steps"><input type="number" className="input" value={v.guardrails.max_steps} onChange={(e) => upd("guardrails", { ...v.guardrails, max_steps: parseInt(e.target.value) })} /></Field>
          <Field label="Max cost $"><input type="number" step="0.01" className="input" value={v.guardrails.max_cost_usd} onChange={(e) => upd("guardrails", { ...v.guardrails, max_cost_usd: parseFloat(e.target.value) })} /></Field>
          <Field label="Denylist (regex, comma)">
            <input className="input" value={(v.guardrails.denylist_regex || []).join(",")} onChange={(e) => upd("guardrails", { ...v.guardrails, denylist_regex: e.target.value.split(",").filter(Boolean) })} />
          </Field>
        </div>
      </details>

      <div className="flex gap-2 pt-2">
        <button className="btn" disabled={saving} onClick={() => onSave(v)}>{saving ? "Saving…" : "Save"}</button>
        <button className="btn-ghost" onClick={onCancel}>Cancel</button>
        {onDelete && <button className="btn-ghost text-red-400 ml-auto" onClick={onDelete}>Delete</button>}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
    </label>
  );
}

function MultiSelect({ options, selected, onChange }: { options: string[]; selected: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = selected.includes(o);
        return (
          <button
            key={o}
            type="button"
            onClick={() => onChange(on ? selected.filter((x) => x !== o) : [...selected, o])}
            className={`px-2 py-1 rounded text-xs border ${on ? "bg-indigo-600 border-indigo-500" : "border-white/10 hover:bg-white/5"}`}
          >
            {o}
          </button>
        );
      })}
      {options.length === 0 && <span className="text-xs text-white/40">none available</span>}
    </div>
  );
}
