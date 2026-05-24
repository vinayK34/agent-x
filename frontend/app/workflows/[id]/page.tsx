"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useCallback } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, applyEdgeChanges, applyNodeChanges,
  Edge, Node, Connection,
} from "reactflow";
import "reactflow/dist/style.css";
import { api } from "@/lib/api";

export default function WorkflowEditor() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const wf = useQuery({ queryKey: ["workflow", id], queryFn: () => api.workflows.get(id) });
  const agents = useQuery({ queryKey: ["agents"], queryFn: api.agents.list });

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [entrypoint, setEntrypoint] = useState<string>("");
  const [runInput, setRunInput] = useState("Write a 150-word brief on AgentX's value proposition.");
  const [lastRunId, setLastRunId] = useState<string | null>(null);

  // Hydrate from server
  useEffect(() => {
    if (!wf.data) return;
    const spec = wf.data.spec || { nodes: [], edges: [] };
    setEntrypoint(spec.entrypoint || "");
    const ns: Node[] = (spec.nodes || []).map((n: any, i: number) => ({
      id: n.id,
      type: "default",
      position: { x: 80 + (i % 4) * 220, y: 80 + Math.floor(i / 4) * 140 },
      data: { ...n, label: nodeLabel(n, agents.data || []) },
    }));
    const es: Edge[] = (spec.edges || []).map((e: any, i: number) => ({
      id: `e${i}`,
      source: e.from,
      target: e.to === "__end__" ? "__end__" : e.to,
      label: e.when ?? "",
    }));
    if ((spec.edges || []).some((e: any) => e.to === "__end__")) {
      ns.push({ id: "__end__", type: "output", position: { x: 80 + ((spec.nodes?.length || 0) % 4) * 220, y: 80 + Math.floor((spec.nodes?.length || 0) / 4) * 140 + 140 }, data: { label: "END" } });
    }
    setNodes(ns);
    setEdges(es);
  }, [wf.data, agents.data]);

  const save = useMutation({
    mutationFn: () => {
      const spec = {
        entrypoint,
        nodes: nodes.filter((n) => n.id !== "__end__").map((n) => ({
          id: n.id,
          type: n.data.type,
          agent_id: n.data.agent_id,
          expr: n.data.expr,
        })),
        edges: edges.map((e) => ({ from: e.source, to: e.target, when: e.label || undefined })),
      };
      return api.workflows.update(id, { ...wf.data, spec });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflow", id] }),
  });

  const run = useMutation({
    mutationFn: () => api.runs.start(id, runInput),
    onSuccess: (r: any) => {
      setLastRunId(r.id);
      router.push(`/monitor?run=${r.id}`);
    },
  });

  const addAgentNode = (agent_id: string) => {
    const nid = `n_${Math.random().toString(36).slice(2, 7)}`;
    const a = (agents.data || []).find((x: any) => x.id === agent_id);
    setNodes((ns) => [
      ...ns,
      { id: nid, position: { x: 100, y: 100 + ns.length * 80 }, data: { id: nid, type: "agent", agent_id, label: `${a?.avatar || "🤖"} ${a?.name}` } },
    ]);
    if (!entrypoint) setEntrypoint(nid);
  };

  const addConditionNode = () => {
    const nid = `c_${Math.random().toString(36).slice(2, 7)}`;
    setNodes((ns) => [...ns, { id: nid, position: { x: 100, y: 100 + ns.length * 80 }, data: { id: nid, type: "condition", expr: "len(input) > 100", label: `❓ if len(input) > 100` } }]);
  };

  const addEndNode = () => {
    if (nodes.some((n) => n.id === "__end__")) return;
    setNodes((ns) => [...ns, { id: "__end__", type: "output", position: { x: 400, y: 400 }, data: { label: "END" } }]);
  };

  const onConnect = useCallback((c: Connection) => setEdges((es) => addEdge({ ...c, label: "" }, es)), []);

  if (!wf.data) return <div className="text-white/60">Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">{wf.data.name}</h1>
        <span className="text-xs text-white/40">entrypoint: {entrypoint || "—"}</span>
        <div className="ml-auto flex gap-2">
          <button className="btn-ghost" onClick={() => save.mutate()}>{save.isPending ? "Saving…" : "Save"}</button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <aside className="col-span-3 card space-y-3">
          <div>
            <div className="label">Add agent node</div>
            <select className="input" onChange={(e) => { if (e.target.value) { addAgentNode(e.target.value); e.target.value = ""; } }}>
              <option value="">— pick agent —</option>
              {(agents.data || []).map((a: any) => <option key={a.id} value={a.id}>{a.avatar} {a.name}</option>)}
            </select>
          </div>
          <button className="btn-ghost w-full" onClick={addConditionNode}>+ Condition</button>
          <button className="btn-ghost w-full" onClick={addEndNode}>+ End</button>

          <div className="pt-3 border-t border-white/10">
            <div className="label">Entrypoint</div>
            <select className="input" value={entrypoint} onChange={(e) => setEntrypoint(e.target.value)}>
              <option value="">—</option>
              {nodes.filter((n) => n.id !== "__end__").map((n) => <option key={n.id} value={n.id}>{n.id}</option>)}
            </select>
          </div>

          <div className="pt-3 border-t border-white/10">
            <div className="label">Run input</div>
            <textarea className="input min-h-[80px]" value={runInput} onChange={(e) => setRunInput(e.target.value)} />
            <button className="btn w-full mt-2" onClick={() => run.mutate()}>{run.isPending ? "Starting…" : "▶ Run"}</button>
            {lastRunId && <div className="text-xs text-white/50 mt-1">Last run: {lastRunId}</div>}
          </div>
        </aside>

        <div className="col-span-9 h-[70vh] card p-0 overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={(ch) => setNodes((ns) => applyNodeChanges(ch, ns))}
            onEdgesChange={(ch) => setEdges((es) => applyEdgeChanges(ch, es))}
            onConnect={onConnect}
            onEdgeDoubleClick={(_, edge) => {
              const label = prompt("Branch label (true / false / empty):", String(edge.label || "")) || "";
              setEdges((es) => es.map((e) => (e.id === edge.id ? { ...e, label } : e)));
            }}
            fitView
          >
            <Background gap={16} color="#222" />
            <MiniMap pannable className="!bg-black/40" />
            <Controls />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

function nodeLabel(n: any, agents: any[]) {
  if (n.type === "agent") {
    const a = agents.find((x) => x.id === n.agent_id);
    return `${a?.avatar || "🤖"} ${a?.name || n.agent_id}`;
  }
  if (n.type === "condition") return `❓ ${n.expr}`;
  return n.id;
}
