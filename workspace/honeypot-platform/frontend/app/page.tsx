"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL;

type CountPair = [string, number];

type DashboardOverview = {
  sessions: {
    classified_total: number;
    telemetry_analyzed_total: number;
    by_classification: Record<string, number>;
  };
  severity: {
    avg: number;
    max: number;
  };
  top_tactics: CountPair[];
  top_behaviors: CountPair[];
  top_attack_chains: CountPair[];
  adaptive: {
    by_status: Record<string, number>;
    by_priority: Record<string, number>;
  };
};

const numberFormatter = new Intl.NumberFormat("en-US");

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);

  useEffect(() => {
    fetch(`${API}/dashboard/overview`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) {
    return (
      <main className="liquid-shell min-h-screen px-5 py-6 text-zinc-100 sm:px-8 lg:px-10">
        <div className="mx-auto flex min-h-[70vh] max-w-7xl items-center">
          <div>
            <div className="mb-5 h-2 w-32 overflow-hidden rounded-full bg-zinc-800">
              <div className="liquid-progress h-full w-2/3 animate-pulse rounded-full bg-gradient-to-r from-violet-800 via-violet-600 to-violet-300" />
            </div>
            <p className="text-sm font-medium uppercase tracking-[0.22em] text-violet-200">
              Syncing telemetry
            </p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">
              Loading command center
            </h1>
          </div>
        </div>
      </main>
    );
  }

  const totalAdaptive = Object.values(data.adaptive.by_status).reduce(
    (sum, count) => sum + count,
    0,
  );

  return (
    <main className="liquid-shell min-h-screen px-5 py-6 text-zinc-100 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <header className="glass-panel mb-8 flex flex-col gap-6 rounded-2xl p-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-200">
              Threat intelligence
            </p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-6xl">
              Honeypot Platform
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
              Live deception telemetry, behavior scoring, and adaptive response
              signals in one operational view.
            </p>
          </div>

          <Link
            href="/dashboard/recent-sessions"
            className="glass-button inline-flex w-fit items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-violet-50"
          >
            Open Triage Queue
            <span className="text-violet-200">-&gt;</span>
          </Link>
        </header>

        <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            delay="0ms"
            detail="Classified sessions"
            title="Sessions"
            value={data.sessions.classified_total}
          />
          <MetricCard
            delay="80ms"
            detail="Analyzed telemetry events"
            title="Telemetry"
            value={data.sessions.telemetry_analyzed_total}
          />
          <MetricCard
            delay="160ms"
            detail="Mean risk score"
            title="Avg Severity"
            value={data.severity.avg}
          />
          <MetricCard
            delay="240ms"
            detail="Highest observed score"
            title="Max Severity"
            value={data.severity.max}
          />
        </section>

        <section className="mb-8 grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
          <Panel title="Behavior Spectrum" className="border-cyan-200/14 bg-[linear-gradient(180deg,rgba(8,47,73,0.20),rgba(17,17,28,0.66))]">
            <ProgressList items={data.top_behaviors} />
          </Panel>

          <Panel title="Adaptive Response" className="border-emerald-200/14 bg-[linear-gradient(180deg,rgba(6,78,59,0.20),rgba(17,17,28,0.66))]">
            <div className="glass-panel mb-5 rounded-xl p-4">
              <div className="text-3xl font-semibold text-white">
                {numberFormatter.format(totalAdaptive)}
              </div>
              <div className="mt-1 text-sm text-violet-100">
                recommendations processed
              </div>
            </div>
            <KeyValueList data={data.adaptive.by_status} />
          </Panel>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <Panel title="Classifications" className="bg-black/30">
            <KeyValueList data={data.sessions.by_classification} />
          </Panel>

          <Panel title="Top Tactics" className="border-amber-200/14 bg-[linear-gradient(180deg,rgba(120,53,15,0.18),rgba(17,17,28,0.66))]">
            <PairList items={data.top_tactics} />
          </Panel>

          <Panel title="Adaptive Priority" className="border-emerald-200/14 bg-[linear-gradient(180deg,rgba(6,78,59,0.18),rgba(17,17,28,0.66))]">
            <KeyValueList data={data.adaptive.by_priority} />
          </Panel>
        </section>

        <section className="mt-4">
          <Panel title="Observed Chain Patterns" className="border-sky-200/14 bg-[linear-gradient(180deg,rgba(12,74,110,0.18),rgba(17,17,28,0.66))]">
            <ChainPatternList items={data.top_attack_chains} />
          </Panel>
        </section>
      </div>
    </main>
  );
}

function MetricCard({
  delay,
  detail,
  title,
  value,
}: {
  delay: string;
  detail: string;
  title: string;
  value: string | number;
}) {
  return (
    <div
      className="glass-panel rounded-2xl p-5 transition duration-300 hover:-translate-y-1"
      style={{ animationDelay: delay }}
    >
      <div className="mb-5 flex items-center justify-between">
        <p className="text-sm text-zinc-400">{title}</p>
        <span className="h-2.5 w-2.5 rounded-full bg-violet-300/85 shadow-[0_0_14px_rgba(167,139,250,0.42)]" />
      </div>
      <div className="text-4xl font-semibold text-white">
        {typeof value === "number" ? numberFormatter.format(value) : value}
      </div>
      <p className="mt-3 text-sm text-zinc-500">{detail}</p>
    </div>
  );
}

function Panel({
  title,
  children,
  className = "",
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`glass-panel h-full rounded-2xl p-5 ${className}`}>
      <div className="mb-5 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        <span className="h-px flex-1 bg-gradient-to-r from-violet-300/60 to-transparent" />
      </div>
      {children}
    </div>
  );
}

function PairList({ items }: { items: CountPair[] }) {
  if (!items || items.length === 0) {
    return <Empty />;
  }

  return (
    <div className="space-y-3">
      {items.map(([name, count]) => (
        <div
          key={name}
          className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm transition hover:border-violet-300/40 hover:bg-violet-300/10"
        >
          <span className="min-w-0 text-zinc-200">{name}</span>
          <span
            className="shrink-0 rounded-lg border border-violet-300/20 bg-violet-300/10 px-2.5 py-1 text-xs font-semibold text-violet-100/90"
          >
            {numberFormatter.format(count)}
          </span>
        </div>
      ))}
    </div>
  );
}

function ChainPatternList({ items }: { items: CountPair[] }) {
  if (!items || items.length === 0) {
    return <Empty />;
  }

  return (
    <div className="space-y-3">
      {items.map(([name, count]) => {
        const stages = name.split(" -> ");

        return (
          <div
            key={name}
            className="rounded-xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm transition hover:border-violet-300/40 hover:bg-violet-300/10"
          >
            <div className="mb-3 flex items-center justify-between gap-4">
              <span className="text-zinc-200">Pattern observed</span>
              <span className="shrink-0 rounded-lg border border-violet-300/20 bg-violet-300/10 px-2.5 py-1 text-xs font-semibold text-violet-100/90">
                {numberFormatter.format(count)}
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {stages.map((stage, index) => (
                <span
                  key={`${stage}-${index}`}
                  className="rounded-lg border border-white/10 bg-black/25 px-2.5 py-1 text-xs text-zinc-300"
                >
                  {stage}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function KeyValueList({ data }: { data: Record<string, string | number> }) {
  if (!data || Object.keys(data).length === 0) {
    return <Empty />;
  }

  return (
    <div className="space-y-3">
      {Object.entries(data).map(([key, value]) => (
        <div
          key={key}
          className="flex items-center justify-between gap-4 border-b border-white/10 pb-3 text-sm last:border-b-0 last:pb-0"
        >
          <span className="capitalize text-zinc-300">{key.replaceAll("_", " ")}</span>
          <span className="rounded-lg border border-violet-300/20 bg-violet-300/10 px-2.5 py-1 text-xs font-semibold text-violet-100/90">
            {String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

function ProgressList({ items }: { items: CountPair[] }) {
  if (!items || items.length === 0) {
    return <Empty />;
  }

  const max = Math.max(...items.map((item) => item[1]), 1);

  return (
    <div className="space-y-4">
      {items.map(([name, count]) => (
        <div key={name}>
          <div className="mb-2 flex justify-between gap-4 text-sm">
            <span className="min-w-0 text-zinc-300">{name.replaceAll("_", " ")}</span>
            <span className="font-medium text-violet-100">
              {numberFormatter.format(count)}
            </span>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="liquid-progress h-2 rounded-full bg-gradient-to-r from-violet-800 via-violet-600 to-violet-300"
              style={{
                width: `${Math.max((count / max) * 100, 8)}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function Empty() {
  return <p className="text-sm text-zinc-500">No data yet</p>;
}
