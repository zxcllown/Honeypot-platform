"use client";

import { useEffect, useState } from "react";
import {
  Badge,
  Empty,
  Hero,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
  ProgressList,
  formatLabel,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type CountPair = [string, number];

type GlobalThreatView = {
  available: boolean;
  message?: string;
  data?: {
    generated_at: string;
    privacy_mode: string;
    nodes: {
      count: number;
      node_ids: string[];
      regions: Record<string, number>;
    };
    global_telemetry: {
      sessions_analyzed: number;
      avg_severity: number;
      max_severity: number;
      top_behaviors: CountPair[];
      top_indicators: CountPair[];
      top_attack_chains: CountPair[];
    };
    global_adaptive: {
      recommendations_total: number;
      by_status: Record<string, number>;
      by_priority: Record<string, number>;
      top_actions: CountPair[];
    };
  };
};

export default function GlobalThreatViewPage() {
  const [payload, setPayload] = useState<GlobalThreatView | null>(null);

  useEffect(() => {
    fetch(`${API}/dashboard/global-threat-view`)
      .then((res) => res.json())
      .then(setPayload);
  }, []);

  if (!payload) return <LoadingState title="Loading global threat view" />;

  if (!payload.available || !payload.data) {
    return (
      <PageShell>
        <Hero
        kicker="Federated intelligence"
        title="Global Threat View"
        description={payload.message ?? "Federated threat data is not available yet."}
          variant="federated"
        />
      </PageShell>
    );
  }

  const data = payload.data;

  return (
    <PageShell>
      <Hero
        kicker="Federated intelligence"
        title="Global Threat View"
        description="Aggregated-only threat posture across honeypot nodes, without exposing raw logs."
        variant="federated"
        stats={
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Nodes" value={data.nodes.count} detail="federated contributors" />
            <MetricCard title="Sessions" value={data.global_telemetry.sessions_analyzed} detail="analyzed globally" />
            <MetricCard title="Avg Severity" value={`${Math.round(data.global_telemetry.avg_severity * 100)}%`} detail="global mean" tone="amber" />
            <MetricCard title="Adaptive" value={data.global_adaptive.recommendations_total} detail="recommendations" tone="emerald" />
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Panel title="Global Behaviors" variant="calm">
          <ProgressList items={data.global_telemetry.top_behaviors} />
        </Panel>
        <Panel title="Federation" variant="dossier">
          <div className="space-y-4">
            <div>
              <div className="mb-2 text-sm text-zinc-500">Privacy</div>
              <Badge tone="emerald">{formatLabel(data.privacy_mode)}</Badge>
            </div>
            <div>
              <div className="mb-2 text-sm text-zinc-500">Regions</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(data.nodes.regions).map(([region, count]) => (
                  <Badge key={region}>{region}: {count}</Badge>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-2 text-sm text-zinc-500">Generated</div>
              <p className="text-sm text-zinc-300">{data.generated_at}</p>
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Panel title="Top Indicators" variant="table">
          <CountList items={data.global_telemetry.top_indicators} />
        </Panel>
        <Panel title="Global Chain Patterns" variant="calm">
          <CountList items={data.global_telemetry.top_attack_chains} />
        </Panel>
        <Panel title="Adaptive Actions" variant="control">
          <CountList items={data.global_adaptive.top_actions} />
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Panel title="Recommendation Status" variant="control">
          <KeyBadges data={data.global_adaptive.by_status} />
        </Panel>
        <Panel title="Priority Mix" variant="calm">
          <KeyBadges data={data.global_adaptive.by_priority} />
        </Panel>
      </div>
    </PageShell>
  );
}

function CountList({ items }: { items?: CountPair[] }) {
  if (!items || items.length === 0) return <Empty />;
  return (
    <div className="space-y-3">
      {items.map(([name, count]) => (
        <div key={name} className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm">
          <span className="min-w-0 text-zinc-300">{formatLabel(name)}</span>
          <Badge>{count}</Badge>
        </div>
      ))}
    </div>
  );
}

function KeyBadges({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  if (!entries.length) return <Empty />;
  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([key, value]) => (
        <Badge key={key} tone={key === "critical" ? "red" : key === "high" ? "amber" : "violet"}>
          {formatLabel(key)}: {value}
        </Badge>
      ))}
    </div>
  );
}
