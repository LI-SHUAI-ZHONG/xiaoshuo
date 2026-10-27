import { AgentCenter } from "../../../../../features/agents/agent-center";
import { Suspense } from "react";

export default function AgentsPage() {
  return <Suspense fallback={<p>正在读取 Agent 任务…</p>}><AgentCenter /></Suspense>;
}
