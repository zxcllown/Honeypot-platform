"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Badge,
  ButtonLink,
  CommandList,
  Empty,
  Hero,
  LoadingState,
  PageShell,
  Panel,
  TagList,
  formatLabel,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type TimelineData = Record<string, string | number | boolean | string[] | null | undefined>;

type TimelineEventData = TimelineData & {
  classification?: string;
  confidence?: number;
  tactics?: string[];
  reason?: string[];
  commands_to_sandbox?: string[];
  commands_executed?: string[];
  network_connections?: string[];
  behaviors?: string[];
  severity_score?: number;
  action_type?: string;
  status?: string;
  priority?: string;
};

type TimelineEventItem = {
  stage: string;
  time: string | null;
  title: string;
  description: string;
  data?: TimelineEventData | null;
};

type TimelineResponse = {
  session_id: string;
  timeline: TimelineEventItem[];
  count: number;
};

export default function SessionTimelinePage() {
  const params = useParams();
  const sessionId = params.id;
  const [data, setData] = useState<TimelineResponse | null>(null);

  useEffect(() => {
    fetch(`${API}/sessions/${sessionId}/timeline`)
      .then((res) => res.json())
      .then(setData);
  }, [sessionId]);

  if (!data) return <LoadingState title="Loading timeline" />;

  return (
    <PageShell>
      <Hero
        kicker="Attack reconstruction"
        title="Session Timeline"
        description={`Session ${data.session_id} arranged as a decision path from classification to adaptive response.`}
        variant="investigation"
        actions={
          <>
            <ButtonLink href={`/sessions/${data.session_id}`} tone="zinc">Dossier</ButtonLink>
            <ButtonLink href={`/sessions-replay/${data.session_id}`}>Replay</ButtonLink>
          </>
        }
      />

      <Panel title={`${data.count} timeline events`} variant="calm">
        {data.timeline?.length ? (
          <div className="relative pl-10">
            <div className="absolute left-4 top-2 h-full w-px bg-gradient-to-b from-violet-300 via-fuchsia-300 to-transparent" />
            <div className="space-y-5">
              {data.timeline.map((event, index) => (
                <TimelineEvent key={`${event.stage}-${index}`} event={event} index={index} />
              ))}
            </div>
          </div>
        ) : (
          <Empty />
        )}
      </Panel>
    </PageShell>
  );
}

function TimelineEvent({ event, index }: { event: TimelineEventItem; index: number }) {
  return (
    <div className="relative">
      <div className="absolute -left-[42px] top-5 h-7 w-7 rounded-full border border-violet-300 bg-zinc-950 shadow-lg shadow-violet-500/30">
        <div className="m-2 h-3 w-3 rounded-full bg-violet-300" />
      </div>
      <div className={`rounded-2xl border p-5 transition ${stageCard(event.stage)}`}>
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className={`text-xs uppercase tracking-[0.2em] ${stageText(event.stage)}`}>
              {formatLabel(event.stage)}
            </div>
            <h2 className="mt-1 text-xl font-semibold text-white">{event.title}</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="zinc">Step {index + 1}</Badge>
            <Badge>{event.time ?? "no timestamp"}</Badge>
          </div>
        </div>
        <p className="mb-4 text-sm leading-6 text-zinc-400">{event.description}</p>
        <StagePreview stage={event.stage} data={event.data} />
      </div>
    </div>
  );
}

function stageCard(stage: string) {
  if (stage === "classification") return "border-cyan-300/18 bg-cyan-300/[0.045] hover:bg-cyan-300/[0.07]";
  if (stage === "risk") return "border-amber-300/18 bg-amber-300/[0.045] hover:bg-amber-300/[0.07]";
  if (stage === "sandbox") return "border-emerald-300/18 bg-black/45 hover:bg-emerald-300/[0.055]";
  if (stage === "telemetry") return "border-sky-300/18 bg-sky-300/[0.045] hover:bg-sky-300/[0.07]";
  if (stage.startsWith("adaptive")) return "border-violet-300/18 bg-violet-300/[0.045] hover:bg-violet-300/[0.07]";
  return "border-white/10 bg-white/[0.04] hover:bg-white/[0.06]";
}

function stageText(stage: string) {
  if (stage === "classification") return "text-cyan-200";
  if (stage === "risk") return "text-amber-200";
  if (stage === "sandbox") return "text-emerald-200";
  if (stage === "telemetry") return "text-sky-200";
  if (stage.startsWith("adaptive")) return "text-violet-200";
  return "text-zinc-300";
}

function StagePreview({ stage, data }: { stage: string; data?: TimelineEventData | null }) {
  if (!data) return null;

  if (stage === "classification") {
    return (
      <div className="flex flex-wrap gap-2">
        <Badge>{formatLabel(data.classification)}</Badge>
        <Badge tone="zinc">{Math.round((data.confidence ?? 0) * 100)}% confidence</Badge>
        <TagList items={data.tactics} />
      </div>
    );
  }

  if (stage === "risk") {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-sm text-zinc-500">Reasons</div>
          <TagList items={data.reason} tone="amber" />
        </div>
        <div>
          <div className="mb-2 text-sm text-zinc-500">Sandbox Window</div>
          <CommandList items={data.commands_to_sandbox} />
        </div>
      </div>
    );
  }

  if (stage === "sandbox") {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-sm text-zinc-500">Executed Commands</div>
          <CommandList items={data.commands_executed} />
        </div>
        <div>
          <div className="mb-2 text-sm text-zinc-500">Network Indicators</div>
          <TagList items={data.network_connections} tone="fuchsia" />
        </div>
      </div>
    );
  }

  if (stage === "telemetry") {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-2 text-sm text-zinc-500">Behaviors</div>
          <TagList items={data.behaviors} tone="fuchsia" />
        </div>
        <div>
          <div className="mb-2 text-sm text-zinc-500">Severity</div>
          <Badge tone="amber">{Math.round((data.severity_score ?? 0) * 100)}%</Badge>
        </div>
      </div>
    );
  }

  if (stage === "adaptive_recommendation" || stage === "adaptive_action") {
    return (
      <div className="flex flex-wrap gap-2">
        <Badge>{formatLabel(data.action_type)}</Badge>
        <Badge tone={data.status === "applied" ? "emerald" : "zinc"}>{data.status}</Badge>
        {data.priority ? <Badge tone={data.priority === "critical" ? "red" : "amber"}>{data.priority}</Badge> : null}
      </div>
    );
  }

  return <Empty />;
}
