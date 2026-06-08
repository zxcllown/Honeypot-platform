"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/dashboard/overview`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) {
    return (
      <main className="min-h-screen bg-gradient-to-b from-zinc-950 via-black to-zinc-950 p-10 text-zinc-100">
        <h1 className="text-5xl font-black tracking-tight bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-500 bg-clip-text text-transparent">
          Loading...
        </h1>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-zinc-950 via-black to-zinc-950 p-10 text-zinc-100">
      <div className="mb-10">
        <h1 className="text-5xl font-black tracking-tight bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-500 bg-clip-text text-transparent">
          Honeypot Platform
        </h1>

        <p className="mt-3 text-zinc-400">
          Adaptive Deception & Threat Analysis Dashboard
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-4">
        <Card title="Sessions" value={data.sessions.classified_total} />
        <Card title="Telemetry" value={data.sessions.telemetry_analyzed_total} />
        <Card title="Avg Severity" value={data.severity.avg} />
        <Card title="Max Severity" value={data.severity.max} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Section title="Classifications">
          <KeyValueList data={data.sessions.by_classification} />
        </Section>

        <Section title="Top Tactics">
          <PairList items={data.top_tactics} />
        </Section>

        <Section title="Top Behaviors">
          <ProgressList items={data.top_behaviors} />
        </Section>

        <Section title="Top Attack Chains">
          <PairList items={data.top_attack_chains} />
          <a
            href="/attack-chain"
  className="mt-5 inline-flex rounded-full border border-violet-500/30 bg-violet-500/10 px-5 py-2 text-sm text-violet-300 hover:bg-violet-500/20"
>
  Open Attack Chain Explorer
</a>
        </Section>

        <Section title="Adaptive Status">
          <KeyValueList data={data.adaptive.by_status} />
        </Section>

        <Section title="Adaptive Priority">
          <KeyValueList data={data.adaptive.by_priority} />
        </Section>
      </div>
    </main>
  );
}

function Card({ title, value }: { title: string; value: any }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6 shadow-lg shadow-violet-950/20 backdrop-blur">
      <div className="text-sm text-zinc-400">{title}</div>

      <div className="mt-3 text-4xl font-bold bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
        {value}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6 shadow-lg shadow-black/30 backdrop-blur">
      <h2 className="mb-4 text-xl font-semibold text-violet-300">{title}</h2>
      {children}
    </div>
  );
}

function PairList({ items }: { items: any[] }) {
  if (!items || items.length === 0) {
    return <Empty />;
  }

  return (
    <div className="space-y-2">
      {items.map(([name, count]: any) => (
        <div
          key={name}
          className="flex items-center justify-between border-b border-zinc-800 py-2 text-sm"
        >
          <span className="text-zinc-300">{name}</span>
          <span className="rounded-full bg-violet-500/15 px-3 py-1 text-violet-300">
            {count}
          </span>
        </div>
      ))}
    </div>
  );
}

function KeyValueList({ data }: { data: Record<string, any> }) {
  if (!data || Object.keys(data).length === 0) {
    return <Empty />;
  }

  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, value]) => (
        <div
          key={key}
          className="flex items-center justify-between border-b border-zinc-800 py-2 text-sm"
        >
          <span className="text-zinc-300">{key}</span>
          <span className="rounded-full bg-fuchsia-500/15 px-3 py-1 text-fuchsia-300">
            {String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

function ProgressList({ items }: { items: any[] }) {
  if (!items || items.length === 0) {
    return <Empty />;
  }

  const max = Math.max(...items.map((item: any) => item[1]), 1);

  return (
    <div className="space-y-4">
      {items.map(([name, count]: any) => (
        <div key={name}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-zinc-300">{name}</span>
            <span className="text-violet-400">{count}</span>
          </div>

          <div className="h-2 rounded bg-zinc-800">
            <div
              className="h-2 rounded bg-gradient-to-r from-violet-500 to-fuchsia-500"
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