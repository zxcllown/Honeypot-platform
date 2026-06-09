"use client";

import { useEffect, useMemo, useState } from "react";
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
} from "../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type SessionRow = {
  session_id: string;
  classification: string;
  confidence: number;
  tactics: string[];
  severity_score: number | null;
  behaviors: string[];
  attack_chain: string[];
  sandbox?: {
    level: string | null;
    exit_code: number | null;
  };
  classified_at: string | null;
};

type SessionsResponse = {
  items: SessionRow[];
  count: number;
};

export default function SessionsPage() {
  const [data, setData] = useState<SessionsResponse | null>(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch(`${API}/sessions`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data.items;
    return data.items.filter((session) => session.classification === filter);
  }, [data, filter]);

  if (!data) return <LoadingState title="Loading sessions" />;

  const classes = Array.from(new Set(data.items.map((item) => item.classification))).filter(Boolean);
  const avgSeverity = data.items.length
    ? data.items.reduce((sum, item) => sum + (item.severity_score ?? 0), 0) / data.items.length
    : 0;
  const sandboxed = data.items.filter((item) => item.sandbox?.level).length;

  return (
    <PageShell>
      <Hero
        kicker="Investigation"
        title="Sessions Explorer"
        description="Classified honeypot sessions with model confidence, sandbox verdicts, and reconstructed attack chains."
        variant="investigation"
        actions={<ButtonLink href="/dashboard/recent-sessions">Recent Queue</ButtonLink>}
        stats={
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard title="Sessions" value={data.count} detail="loaded from classifier" />
            <MetricCard title="Avg Severity" value={`${Math.round(avgSeverity * 100)}%`} detail="across current page" tone="amber" />
            <MetricCard title="Sandboxed" value={sandboxed} detail="with execution evidence" tone="emerald" />
          </div>
        }
      />

      <Panel
        title="Session Table"
        variant="table"
        action={
          <div className="flex gap-2">
            {["all", ...classes].map((item) => (
              <button
                key={item}
                onClick={() => setFilter(item)}
                className={`rounded-lg px-3 py-1.5 text-xs transition ${
                  filter === item ? "bg-violet-300/15 text-violet-100" : "text-zinc-400 hover:bg-white/10"
                }`}
              >
                {formatLabel(item)}
              </button>
            ))}
          </div>
        }
      >
        {filtered.length ? (
          <div className="overflow-hidden rounded-2xl border border-white/10">
            <div className="grid grid-cols-[1.1fr_0.65fr_0.7fr_0.9fr_1fr_0.55fr] gap-4 bg-white/[0.04] px-4 py-3 text-xs uppercase tracking-[0.18em] text-zinc-500 max-xl:hidden">
              <span>Session</span>
              <span>Class</span>
              <span>Confidence</span>
              <span>Severity</span>
              <span>Attack Chain</span>
              <span>Open</span>
            </div>
            <div className="divide-y divide-white/10">
              {filtered.map((session) => (
                <div
                  key={session.session_id}
                  className={`grid gap-4 border-l-2 px-4 py-4 transition xl:grid-cols-[1.1fr_0.65fr_0.7fr_0.9fr_1fr_0.55fr] xl:items-center ${rowTone(session.classification)}`}
                >
                  <div>
                    <div className="font-mono text-sm text-violet-200">{session.session_id}</div>
                    <div className="mt-1 text-xs text-zinc-500">{session.classified_at ?? "-"}</div>
                  </div>
                  <Badge tone={classificationTone(session.classification)}>
                    {formatLabel(session.classification)}
                  </Badge>
                  <span className="text-sm text-zinc-300">
                    {Math.round((session.confidence ?? 0) * 100)}%
                  </span>
                  <SeverityBar value={session.severity_score} />
                  <div className="text-sm text-zinc-300">
                    {session.attack_chain?.length ? session.attack_chain.join(" / ") : "No chain"}
                    <div className="mt-1 text-xs text-zinc-500">
                      {session.sandbox?.level ? `${session.sandbox.level}, exit ${session.sandbox.exit_code ?? "-"}` : "No sandbox verdict"}
                    </div>
                  </div>
                  <ButtonLink href={`/sessions/${session.session_id}`} tone="zinc">
                    Open
                  </ButtonLink>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <Empty label="No sessions match this filter" />
        )}
      </Panel>
    </PageShell>
  );
}

function rowTone(classification: string) {
  if (classification === "malicious") {
    return "border-l-red-300/70 hover:bg-red-300/5";
  }
  if (classification === "mixed") {
    return "border-l-amber-300/70 hover:bg-amber-300/5";
  }
  if (classification === "benign") {
    return "border-l-emerald-300/70 hover:bg-emerald-300/5";
  }

  return "border-l-violet-300/70 hover:bg-violet-300/5";
}
