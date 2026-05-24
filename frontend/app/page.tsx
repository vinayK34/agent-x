"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";

export default function Dashboard() {
  const agents = useQuery({ queryKey: ["agents"], queryFn: api.agents.list });
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: api.workflows.list });
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs.list });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-white/60 text-sm mt-1">
          Configure agents, design workflows, run them, watch live.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat label="Agents" value={agents.data?.length ?? "—"} href="/agents" />
        <Stat label="Workflows" value={workflows.data?.length ?? "—"} href="/workflows" />
        <Stat label="Runs" value={runs.data?.length ?? "—"} href="/runs" />
      </div>

      <section className="card">
        <h2 className="font-semibold mb-3">Quick start</h2>
        <ol className="list-decimal list-inside space-y-1 text-sm text-white/80">
          <li>Open <Link href="/workflows">Workflows</Link>, pick a seeded template.</li>
          <li>Click <span className="font-mono">Run</span> and send a goal.</li>
          <li>Watch <Link href="/monitor">Live monitor</Link> for inter-agent traffic.</li>
          <li>Set <span className="font-mono">TELEGRAM_BOT_TOKEN</span> in <span className="font-mono">.env</span> and DM your bot.</li>
        </ol>
      </section>
    </div>
  );
}

function Stat({ label, value, href }: { label: string; value: any; href: string }) {
  return (
    <Link href={href} className="card hover:bg-white/[0.04]">
      <div className="text-xs uppercase text-white/50">{label}</div>
      <div className="text-3xl font-semibold mt-1">{value}</div>
    </Link>
  );
}
