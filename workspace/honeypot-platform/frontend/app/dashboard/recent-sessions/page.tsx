"use client";

import { useEffect, useState } from "react";
import {
  Badge,
  ButtonLink,
  Empty,
  Hero,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
  SeverityBar,
  classificationTone,
  formatLabel,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type RecentSession = {
  session_id: string;
  classification: string;
  confidence: number;
  tactics: string[];
  severity_score: number | null;
  behaviors: string[];
  attack_chain: string[];
  sandbox_level: string | null;
  sandbox_exit_code: number | null;
  classified_at: string | null;
};

type RecentSessionsResponse = {
  items: RecentSession[];
  count: number;
};

export default function RecentSessionsPage() {
  const [data, setData] = useState<RecentSessionsResponse | null>(null);

  useEffect(() => {
    fetch(`${API}/dashboard/recent-sessions`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) return <LoadingState title="Loading recent sessions" />;

  const malicious = data.items.filter((item) => item.classification === "malicious").length;
  const sandboxed = data.items.filter((item) => item.sandbox_level).length;
  const maxSeverity = Math.max(...data.items.map((item) => item.severity_score ?? 0), 0);

  return (
    <PageShell>
      <Hero
        kicker="Dashboard"
        title="Recent Sessions"
        description="Latest classified attacks with risk, chain, and sandbox signals compressed into a triage view."
        variant="investigation"
        actions={<ButtonLink href="/sessions">Open Explorer</ButtonLink>}
        stats={
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard title="Loaded" value={data.count} detail="recent sessions" />
            <MetricCard title="Malicious" value={malicious} detail="high attention" tone="red" />
            <MetricCard title="Peak Severity" value={`${Math.round(maxSeverity * 100)}%`} detail="latest window" tone="amber" />
          </div>
        }
      />

      <Panel title="Triage Queue" variant="table">
        {data.items.length ? (
          <div className="overflow-hidden rounded-2xl border border-white/10">
            <div className="grid grid-cols-[1.2fr_0.7fr_0.9fr_1fr_0.7fr] gap-4 bg-white/[0.04] px-4 py-3 text-xs uppercase tracking-[0.18em] text-zinc-500 max-lg:hidden">
              <span>Session</span>
              <span>Class</span>
              <span>Severity</span>
              <span>Chain</span>
              <span>Action</span>
            </div>
            <div className="divide-y divide-white/10">
              {data.items.map((session) => (
                <div
                  key={session.session_id}
                  className={`grid gap-4 border-l-2 px-4 py-4 transition lg:grid-cols-[1.2fr_0.7fr_0.9fr_1fr_0.7fr] lg:items-center ${rowTone(session.classification)}`}
                >
                  <div>
                    <div className="font-mono text-sm text-violet-200">{session.session_id}</div>
                    <div className="mt-1 text-xs text-zinc-500">{session.classified_at ?? "-"}</div>
                  </div>
                  <Badge tone={classificationTone(session.classification)}>
                    {formatLabel(session.classification)}
                  </Badge>
                  <SeverityBar value={session.severity_score} />
                  <div className="text-sm text-zinc-300">
                    {session.attack_chain?.length ? session.attack_chain.join(" / ") : "No chain"}
                    <div className="mt-1 text-xs text-zinc-500">
                      {session.sandbox_level ? `${session.sandbox_level} sandbox, exit ${session.sandbox_exit_code ?? "-"}` : "No sandbox run"}
                    </div>
                  </div>
                  <ButtonLink href={`/sessions/${session.session_id}`} tone="zinc">
                    Inspect
                  </ButtonLink>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <Empty />
        )}
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Behavior Snapshot" variant="dossier">
          <div className="flex flex-wrap gap-2">
            {Array.from(new Set(data.items.flatMap((item) => item.behaviors))).slice(0, 16).map((item) => (
              <Badge key={item} tone="fuchsia">{formatLabel(item)}</Badge>
            ))}
            {!data.items.some((item) => item.behaviors.length) ? <Empty /> : null}
          </div>
        </Panel>
        <Panel title="Sandbox Coverage" variant="calm">
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div className="liquid-progress h-2 rounded-full" style={{ width: `${data.count ? (sandboxed / data.count) * 100 : 0}%` }} />
          </div>
          <p className="mt-3 text-sm text-zinc-400">
            {sandboxed} of {data.count} recent sessions include sandbox execution context.
          </p>
        </Panel>
      </div>
    </PageShell>
  );
}

function rowTone(classification: string) {
  if (classification === "malicious") return "border-l-red-300/70 hover:bg-red-300/5";
  if (classification === "mixed") return "border-l-amber-300/70 hover:bg-amber-300/5";
  if (classification === "benign") return "border-l-emerald-300/70 hover:bg-emerald-300/5";
  return "border-l-violet-300/70 hover:bg-violet-300/5";
}
