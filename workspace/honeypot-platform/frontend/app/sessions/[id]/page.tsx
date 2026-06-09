"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Badge,
  ButtonLink,
  CommandList,
  Empty,
  Hero,
  InfoGrid,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
  SeverityBar,
  Tabs,
  TagList,
  classificationTone,
  formatLabel,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type CommandResult = {
  command: string;
  exit_code: number | null;
  stdout?: string;
  stderr?: string;
  network_indicators?: string[];
};

type AdaptiveRecommendation = {
  id: number;
  action_type: string;
  action_name: string;
  reason: string;
  priority: string;
  status: string;
};

type AdaptiveAction = {
  id: number;
  action_name: string;
  status: string;
  created_at: string | null;
};

type SessionDetail = {
  session_id: string;
  classification: {
    classification: string;
    confidence: number;
    tactics: string[];
    model_name: string;
    model_version: string;
    classified_at: string | null;
    correlation_id: string;
  };
  risk?: {
    risk_score: number;
    sandbox_required: boolean;
    reason: string[];
    decided_at: string | null;
  } | null;
  sandbox?: {
    sandbox_level: string;
    exit_code: number | null;
    executed_at: string | null;
    commands_executed: string[];
    command_results: CommandResult[];
    network_connections: string[];
    syscalls: string[];
  } | null;
  telemetry?: {
    severity_score: number;
    summary: string;
    behaviors: string[];
    attack_chain: string[];
    file_activity?: {
      created?: string[];
      modified?: string[];
      sensitive_access?: string[];
    };
    process_activity?: {
      suspicious_processes?: string[];
      failed_commands?: string[];
    };
  } | null;
  adaptive?: {
    recommendations: AdaptiveRecommendation[];
    actions_log: AdaptiveAction[];
  };
};

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.id;
  const [data, setData] = useState<SessionDetail | null>(null);

  useEffect(() => {
    fetch(`${API}/sessions/${sessionId}`)
      .then((res) => res.json())
      .then(setData);
  }, [sessionId]);

  if (!data) return <LoadingState title="Loading session" />;

  const confidence = Math.round((data.classification?.confidence ?? 0) * 100);
  const severity = data.telemetry?.severity_score ?? data.risk?.risk_score ?? 0;

  return (
    <PageShell>
      <Hero
        kicker="Session dossier"
        title={data.session_id}
        description="A compact investigation view for classification, risk decision, sandbox execution, telemetry analysis, and adaptive response."
        variant="investigation"
        actions={
          <>
            <ButtonLink href={`/sessions-timeline/${data.session_id}`}>Timeline</ButtonLink>
            <ButtonLink href={`/sessions-replay/${data.session_id}`} tone="zinc">Replay</ButtonLink>
          </>
        }
        stats={
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Classification"
              value={<Badge tone={classificationTone(data.classification?.classification)}>{formatLabel(data.classification?.classification)}</Badge>}
              detail={`${confidence}% confidence`}
            />
            <MetricCard title="Severity" value={<SeverityBar value={severity} />} detail="risk posture" tone="amber" />
            <MetricCard title="Sandbox" value={data.sandbox?.sandbox_level ?? "-"} detail={`exit ${data.sandbox?.exit_code ?? "-"}`} tone={data.sandbox ? "emerald" : "zinc"} />
            <MetricCard title="Adaptive" value={data.adaptive?.recommendations?.length ?? 0} detail="recommendations" />
          </div>
        }
      />

      <Tabs
        tabs={[
          {
            id: "overview",
            label: "Overview",
            content: (
              <div className="grid gap-4 lg:grid-cols-2">
                <Panel title="Classification" variant="dossier">
                  <InfoGrid
                    data={[
                      ["Model", data.classification?.model_name],
                      ["Version", data.classification?.model_version],
                      ["Classified", data.classification?.classified_at],
                      ["Correlation", data.classification?.correlation_id],
                    ]}
                  />
                  <div className="mt-5">
                    <div className="mb-2 text-sm text-zinc-500">Tactics</div>
                    <TagList items={data.classification?.tactics} />
                  </div>
                </Panel>
                <Panel title="Risk Decision" variant="calm">
                  {data.risk ? (
                    <>
                      <InfoGrid
                        data={[
                          ["Risk score", data.risk.risk_score],
                          ["Sandbox required", String(data.risk.sandbox_required)],
                          ["Decided", data.risk.decided_at],
                        ]}
                      />
                      <div className="mt-5">
                        <div className="mb-2 text-sm text-zinc-500">Reasons</div>
                        <TagList items={data.risk.reason} tone="amber" />
                      </div>
                    </>
                  ) : (
                    <Empty />
                  )}
                </Panel>
              </div>
            ),
          },
          {
            id: "sandbox",
            label: "Sandbox",
            hidden: !data.sandbox,
            content: (
              <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
                <Panel title="Run Summary" variant="terminal">
                  {data.sandbox ? (
                    <>
                      <InfoGrid
                        data={[
                          ["Level", data.sandbox.sandbox_level],
                          ["Exit code", data.sandbox.exit_code],
                          ["Executed", data.sandbox.executed_at],
                          ["Commands", data.sandbox.commands_executed?.length ?? 0],
                          ["Syscalls", data.sandbox.syscalls?.length ?? 0],
                        ]}
                      />
                      <div className="mt-5">
                        <div className="mb-2 text-sm text-zinc-500">Network Indicators</div>
                        <TagList items={data.sandbox.network_connections} tone="fuchsia" />
                      </div>
                    </>
                  ) : (
                    <Empty />
                  )}
                </Panel>
                <Panel title="Command Results" variant="terminal">
                  {data.sandbox?.command_results?.length ? (
                    <div className="space-y-4">
                      {data.sandbox.command_results.map((cmd, index) => (
                        <div key={index} className="rounded-xl border border-emerald-300/15 bg-black/45 p-4 shadow-[inset_0_1px_0_rgba(110,231,183,0.08)]">
                          <div className="mb-3 flex items-center justify-between gap-4">
                            <code className="min-w-0 overflow-x-auto text-sm text-violet-200">{cmd.command}</code>
                            <Badge tone={cmd.exit_code === 0 ? "emerald" : "red"}>exit {cmd.exit_code}</Badge>
                          </div>
                          {cmd.stdout ? <CodeBlock title="STDOUT" text={cmd.stdout} /> : null}
                          {cmd.stderr ? <CodeBlock title="STDERR" text={cmd.stderr} danger /> : null}
                          {cmd.network_indicators?.length ? (
                            <div className="mt-3">
                              <TagList items={cmd.network_indicators} tone="fuchsia" />
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <CommandList items={data.sandbox?.commands_executed} />
                  )}
                </Panel>
              </div>
            ),
          },
          {
            id: "telemetry",
            label: "Telemetry",
            hidden: !data.telemetry,
            content: (
              <div className="grid gap-4 lg:grid-cols-2">
                <Panel title="Analysis" variant="dossier">
                  {data.telemetry ? (
                    <>
                      <p className="mb-5 rounded-xl border border-white/10 bg-black/30 p-4 text-sm leading-6 text-zinc-300">
                        {data.telemetry.summary}
                      </p>
                      <div className="mb-5">
                        <div className="mb-2 text-sm text-zinc-500">Behaviors</div>
                        <TagList items={data.telemetry.behaviors} tone="fuchsia" />
                      </div>
                      <div>
                        <div className="mb-2 text-sm text-zinc-500">Attack Chain</div>
                        <TagList items={data.telemetry.attack_chain} />
                      </div>
                    </>
                  ) : (
                    <Empty />
                  )}
                </Panel>
                <Panel title="Activity" variant="table">
                  <div className="space-y-5">
                    <Activity title="Files Created" items={data.telemetry?.file_activity?.created} />
                    <Activity title="Files Modified" items={data.telemetry?.file_activity?.modified} />
                    <Activity title="Sensitive Access" items={data.telemetry?.file_activity?.sensitive_access} tone="amber" />
                    <Activity title="Suspicious Processes" items={data.telemetry?.process_activity?.suspicious_processes} tone="red" />
                    <Activity title="Failed Commands" items={data.telemetry?.process_activity?.failed_commands} tone="zinc" />
                  </div>
                </Panel>
              </div>
            ),
          },
          {
            id: "adaptive",
            label: "Adaptive",
            hidden: !data.adaptive?.recommendations?.length && !data.adaptive?.actions_log?.length,
            content: (
              <div className="grid gap-4 lg:grid-cols-2">
                <Panel title="Recommendations" variant="control">
                  {data.adaptive?.recommendations?.length ? (
                    <div className="space-y-3">
                      {data.adaptive.recommendations.map((rec) => (
                        <div key={rec.id} className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.045] p-4">
                          <div className="mb-2 flex items-center justify-between gap-3">
                            <h3 className="font-semibold text-white">{rec.action_name}</h3>
                            <Badge tone={rec.priority === "critical" ? "red" : rec.priority === "high" ? "amber" : "violet"}>
                              {rec.priority}
                            </Badge>
                          </div>
                          <p className="text-sm leading-6 text-zinc-400">{rec.reason}</p>
                          <div className="mt-3 flex gap-2">
                            <Badge tone="emerald">{rec.status}</Badge>
                            <Badge tone="zinc">{rec.action_type}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty />
                  )}
                </Panel>
                <Panel title="Actions Log" variant="calm">
                  {data.adaptive?.actions_log?.length ? (
                    <div className="space-y-3">
                      {data.adaptive.actions_log.map((action) => (
                        <div key={action.id} className="rounded-xl border border-white/10 bg-black/30 p-4 text-sm">
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-zinc-200">{action.action_name}</span>
                            <Badge tone={action.status === "applied" ? "emerald" : "zinc"}>{action.status}</Badge>
                          </div>
                          <div className="mt-2 text-xs text-zinc-500">{action.created_at}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty />
                  )}
                </Panel>
              </div>
            ),
          },
        ]}
      />
    </PageShell>
  );
}

function CodeBlock({ title, text, danger }: { title: string; text: string; danger?: boolean }) {
  return (
    <div className="mt-3">
      <div className="mb-2 text-xs text-zinc-500">{title}</div>
      <pre className={`max-h-56 overflow-auto rounded-xl border p-4 text-xs ${danger ? "border-red-400/20 bg-red-950/20 text-red-100" : "border-white/10 bg-black/40 text-zinc-300"}`}>
        {text}
      </pre>
    </div>
  );
}

function Activity({
  title,
  items,
  tone = "violet",
}: {
  title: string;
  items?: string[];
  tone?: "violet" | "red" | "amber" | "zinc";
}) {
  return (
    <div>
      <div className="mb-2 text-sm text-zinc-500">{title}</div>
      <TagList items={items} tone={tone} />
    </div>
  );
}
