"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const run = useQuery({ queryKey: ["run", id], queryFn: () => api.runs.get(id), refetchInterval: 1500 });
  const msgs = useQuery({ queryKey: ["run-messages", id], queryFn: () => api.runs.messages(id), refetchInterval: 1500 });

  if (!run.data) return <div className="text-white/60">Loading…</div>;
  return (
    <div className="space-y-4">
      <div className="card">
        <div className="text-sm text-white/60">Status</div>
        <div className="text-lg font-medium">{run.data.status}</div>
        <div className="text-xs text-white/50 mt-1">cost ${run.data.cost_usd.toFixed(4)} · {run.data.tokens} tokens</div>
        {run.data.error && <div className="text-red-300 mt-2 text-sm">{run.data.error}</div>}
      </div>
      <h2 className="font-semibold">Conversation</h2>
      <div className="space-y-2">
        {msgs.data?.map((m: any) => (
          <div key={m.id} className="card">
            <div className="text-xs text-white/40 mb-1">{m.role} · {new Date(m.created_at).toLocaleTimeString()} {m.channel ? `· ${m.channel}` : ""}</div>
            <pre className="whitespace-pre-wrap text-sm">{m.content}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
