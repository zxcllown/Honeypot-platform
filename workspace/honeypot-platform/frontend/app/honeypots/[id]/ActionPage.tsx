"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ActionButton,
  Badge,
  ButtonLink,
  Empty,
  Hero,
  InfoGrid,
  LoadingState,
  PageShell,
  Panel,
  formatLabel,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type ActionName = "enable" | "disable";

type HoneypotNode = {
  node_id: string;
  name?: string;
  status: string;
  honeypot_type?: string;
  host?: string;
  port?: number;
  updated_at?: string;
};

type ActionPhase = {
  name: string;
  status: string;
};

type ActionResult = {
  node_id: string;
  action: string;
  status: string;
  message?: string;
  phases?: ActionPhase[];
};

const actionCopy: Record<
  ActionName,
  {
    kicker: string;
    title: string;
    description: string;
    button: string;
    tone: "emerald" | "red" | "violet";
    steps: string[];
  }
> = {
  enable: {
    kicker: "Lifecycle action",
    title: "Enable Honeypot",
    description: "Bring the deception listener online and mark the node as running.",
    button: "Run enable",
    tone: "emerald",
    steps: ["validate node profile", "bind listener", "publish running state"],
  },
  disable: {
    kicker: "Lifecycle action",
    title: "Disable Honeypot",
    description: "Stop exposing the service while preserving node metadata and historical telemetry.",
    button: "Run disable",
    tone: "red",
    steps: ["stop listener", "close exposed port", "publish stopped state"],
  },
};

export default function HoneypotActionPage({ action }: { action: ActionName }) {
  const params = useParams();
  const nodeId = String(params.id);
  const copy = actionCopy[action];
  const [node, setNode] = useState<HoneypotNode | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ActionResult | null>(null);

  useEffect(() => {
    fetch(`${API}/honeypots/${nodeId}`)
      .then((res) => res.json())
      .then(setNode);
  }, [nodeId]);

  async function runAction() {
    setRunning(true);
    setResult(null);
    try {
      const response = await fetch(`${API}/honeypots/${nodeId}/${action}`, {
        method: "POST",
      });
      const payload = await response.json();
      setResult(payload);
      const fresh = await fetch(`${API}/honeypots/${nodeId}`).then((res) => res.json());
      setNode(fresh);
    } finally {
      window.setTimeout(() => setRunning(false), 250);
    }
  }

  if (!node) return <LoadingState title={`Loading ${action} action`} />;

  const phases = result?.phases?.length
    ? result.phases.map((phase) => formatLabel(phase.name))
    : copy.steps;

  return (
    <PageShell>
      <Hero
        kicker={copy.kicker}
        title={copy.title}
        description={`${copy.description} Target node: ${node.name ?? node.node_id}.`}
        variant="control"
        actions={
          <>
            <ButtonLink href={`/honeypots/${node.node_id}`} tone="zinc">Node Profile</ButtonLink>
            <ButtonLink href="/honeypots" tone="zinc">All Honeypots</ButtonLink>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Target" variant="control">
          <InfoGrid
            data={[
              ["Node", <span className="font-mono text-violet-200" key="node">{node.node_id}</span>],
              ["Status", <Badge tone={node.status === "running" ? "emerald" : "red"} key="status">{node.status}</Badge>],
              ["Endpoint", `${node.host}:${node.port}`],
              ["Type", formatLabel(node.honeypot_type)],
              ["Updated", node.updated_at],
            ]}
          />
          <div className="mt-6">
            <ActionButton onClick={runAction} disabled={running} tone={copy.tone}>
              {running ? "Running..." : copy.button}
            </ActionButton>
          </div>
        </Panel>

        <Panel title="Execution Plan" variant="control">
          <div className="space-y-4">
            {phases.map((phase: string, index: number) => {
              const complete = Boolean(result) || (running && index < 2);
              return (
                <div key={phase} className="rounded-2xl border border-emerald-300/15 bg-black/25 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-zinc-100">{phase}</span>
                    <Badge tone={complete ? "emerald" : running ? "amber" : "zinc"}>
                      {complete ? "completed" : running ? "running" : "ready"}
                    </Badge>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="liquid-progress h-2 rounded-full transition-all"
                      style={{ width: complete ? "100%" : running ? "58%" : "8%" }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {result ? (
            <div className="mt-5 rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-4">
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="font-medium text-emerald-100">{result.message ?? "Action completed"}</span>
                <Badge tone="emerald">{result.status}</Badge>
              </div>
              <p className="text-sm text-zinc-400">
                Action `{result.action}` completed for `{result.node_id}`.
              </p>
            </div>
          ) : (
            <div className="mt-5">
              <Empty label="Run the action to see execution results" />
            </div>
          )}
        </Panel>
      </div>
    </PageShell>
  );
}
