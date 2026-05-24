"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";

export default function RunsPage() {
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs.list, refetchInterval: 2000 });
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Runs</h1>
      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-left text-white/60">
            <tr>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Trigger</th>
              <th className="px-3 py-2">Input</th>
              <th className="px-3 py-2">Cost</th>
              <th className="px-3 py-2">When</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.data?.map((r: any) => (
              <tr key={r.id} className="border-t border-white/5">
                <td className="px-3 py-2"><Badge status={r.status} /></td>
                <td className="px-3 py-2 text-white/70">{r.trigger}</td>
                <td className="px-3 py-2 max-w-[300px] truncate">{r.input}</td>
                <td className="px-3 py-2 text-white/70">${(r.cost_usd || 0).toFixed(4)}</td>
                <td className="px-3 py-2 text-white/50">{new Date(r.started_at).toLocaleTimeString()}</td>
                <td className="px-3 py-2"><Link className="text-indigo-400" href={`/runs/${r.id}`}>open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const color =
    status === "completed" ? "bg-green-500/20 text-green-300" :
    status === "running" ? "bg-indigo-500/20 text-indigo-300" :
    status.startsWith("guardrail") ? "bg-amber-500/20 text-amber-300" :
    "bg-red-500/20 text-red-300";
  return <span className={`px-2 py-0.5 rounded text-xs ${color}`}>{status}</span>;
}
