export function openMonitorSocket(onEvent: (e: any) => void): () => void {
  const url =
    (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws") +
    "/ws/monitor";
  const ws = new WebSocket(url);
  ws.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data));
    } catch {
      /* ignore */
    }
  };
  return () => ws.close();
}
