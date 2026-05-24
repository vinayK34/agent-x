"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";

export default function WorkflowsPage() {
  const qc = useQueryClient();
  const wfs = useQuery({ queryKey: ["workflows"], queryFn: api.workflows.list });
  const remove = useMutation({
    mutationFn: (id: string) => api.workflows.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
  const [creating, setCreating] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Workflows</h1>
        <button className="btn" onClick={() => setCreating(true)}>+ New blank</button>
      </div>

      {creating && <NewBlank onDone={() => { setCreating(false); qc.invalidateQueries({ queryKey: ["workflows"] }); }} />}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {wfs.data?.map((w: any) => (
          <div key={w.id} className="card space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Link href={`/workflows/${w.id}`} className="font-medium hover:underline">{w.name}</Link>
                <p className="text-sm text-white/60 mt-1">{w.description || "—"}</p>
              </div>
              <button className="btn-ghost text-xs text-red-400" onClick={() => remove.mutate(w.id)}>Delete</button>
            </div>
            <div className="text-xs text-white/40">
              {w.spec?.nodes?.length || 0} nodes · {w.spec?.edges?.length || 0} edges
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function NewBlank({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: () =>
      api.workflows.create({
        name,
        description: "",
        spec: { entrypoint: "", nodes: [], edges: [] },
      }),
    onSuccess: onDone,
  });
  return (
    <div className="card flex gap-2">
      <input className="input" placeholder="Workflow name" value={name} onChange={(e) => setName(e.target.value)} />
      <button className="btn" disabled={!name || create.isPending} onClick={() => create.mutate()}>Create</button>
    </div>
  );
}
