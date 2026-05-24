"use client";
import { useEffect, useRef, useState } from "react";
import { openMonitorSocket } from "@/lib/ws";

type Event = { type: string; [k: string]: any };

export default function Monitor() {
  const [events, setEvents] = useState<Event[]>([]);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const close = openMonitorSocket((e) => setEvents((cur) => [...cur.slice(-499), e]));
    return close;
  }, []);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [events]);

  const cost = events
    .filter((e) => typeof e.cost_usd === "number")
    .reduce((acc, e) => acc + (e.cost_usd || 0), 0);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Live monitor</h1>
        <div className="text-sm text-white/60">running cost: <span className="text-white">${cost.toFixed(4)}</span></div>
      </div>
      <div ref={ref} className="card h-[70vh] overflow-y-auto font-mono text-xs space-y-1">
        {events.length === 0 && <div className="text-white/40">Waiting for runtime events…</div>}
        {events.map((e, i) => (
          <div key={i} className="border-l-2 pl-2" style={{ borderColor: color(e.type) }}>
            <span className="text-white/40">[{e.type}]</span>{" "}
            {e.agent && <span className="text-indigo-300">{e.agent}</span>}{" "}
            {e.tool && <span className="text-amber-300">{e.tool}</span>}{" "}
            <span className="text-white/80">{summarize(e)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function color(t: string) {
  if (t.startsWith("run_")) return "#a78bfa";
  if (t === "node_start" || t === "node_end") return "#60a5fa";
  if (t === "message") return "#34d399";
  if (t.startsWith("tool_")) return "#fbbf24";
  if (t.startsWith("guardrail")) return "#f87171";
  return "#9ca3af";
}

function summarize(e: Event): string {
  if (e.type === "message") return (e.content || "").slice(0, 240);
  if (e.type === "tool_call") return JSON.stringify(e.args || {});
  if (e.type === "tool_result") return (e.result || "").slice(0, 240);
  if (e.type === "run_end") return `→ ${(e.output || "").slice(0, 240)}`;
  if (e.type === "run_failed") return `${e.status}: ${e.error}`;
  return e.input || e.node || "";
}
