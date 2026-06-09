"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Badge,
  ButtonLink,
  Empty,
  Hero,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
  TagList,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type ReplayStepData = {
  index: number;
  command: string;
  exit_code: number | null;
  status: string;
  stdout?: string;
  stderr?: string;
  network_indicators?: string[];
  related_syscalls?: string[];
};

type ReplayResponse = {
  session_id: string;
  sandbox: {
    sandbox_level: string;
    exit_code: number | null;
  };
  summary: {
    commands_total: number;
    failed_commands: number;
    syscalls_total: number;
    network_indicators: string[];
    files_created: string[];
    files_modified: string[];
  };
  steps: ReplayStepData[];
};

export default function SessionReplayPage() {
  const params = useParams();
  const sessionId = params.id;
  const [data, setData] = useState<ReplayResponse | null>(null);

  useEffect(() => {
    fetch(`${API}/sessions/${sessionId}/replay`)
      .then((res) => res.json())
      .then(setData);
  }, [sessionId]);

  if (!data) return <LoadingState title="Loading replay" />;

  return (
    <PageShell>
      <Hero
        kicker="Sandbox playback"
        title="Session Replay"
        description={`Command-by-command execution trace for session ${data.session_id}.`}
        variant="terminal"
        actions={
          <>
            <ButtonLink href={`/sessions/${data.session_id}`} tone="zinc">Dossier</ButtonLink>
            <ButtonLink href={`/sessions-timeline/${data.session_id}`}>Timeline</ButtonLink>
          </>
        }
        stats={
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Commands" value={data.summary.commands_total} detail="replayed steps" />
            <MetricCard title="Failed" value={data.summary.failed_commands} detail="non-zero exits" tone={data.summary.failed_commands ? "red" : "emerald"} />
            <MetricCard title="Syscalls" value={data.summary.syscalls_total} detail="captured by sandbox" />
            <MetricCard title="Exit Code" value={data.sandbox.exit_code ?? "-"} detail={data.sandbox.sandbox_level} tone={data.sandbox.exit_code === 0 ? "emerald" : "amber"} />
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Replay Summary" variant="terminal">
          <div className="space-y-5">
            <div>
              <div className="mb-2 text-sm text-zinc-500">Network Indicators</div>
              <TagList items={data.summary.network_indicators} tone="fuchsia" />
            </div>
            <div>
              <div className="mb-2 text-sm text-zinc-500">Files Created</div>
              <TagList items={data.summary.files_created} tone="emerald" />
            </div>
            <div>
              <div className="mb-2 text-sm text-zinc-500">Files Modified</div>
              <TagList items={data.summary.files_modified} tone="amber" />
            </div>
          </div>
        </Panel>

        <Panel title="Execution Steps" variant="terminal">
          {data.steps?.length ? (
            <div className="space-y-4">
              {data.steps.map((step) => (
                <ReplayStep key={step.index} step={step} />
              ))}
            </div>
          ) : (
            <Empty label="No command results captured" />
          )}
        </Panel>
      </div>
    </PageShell>
  );
}

function ReplayStep({ step }: { step: ReplayStepData }) {
  return (
    <div className="overflow-hidden rounded-xl border border-emerald-300/15 bg-black/55 shadow-[inset_0_1px_0_rgba(110,231,183,0.08)]">
      <div className="flex items-center justify-between border-b border-emerald-300/10 bg-emerald-300/[0.045] px-4 py-2">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-300/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-300/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-300/70" />
        </div>
        <Badge tone={step.exit_code === 0 ? "emerald" : "red"}>
          {step.status} / exit {step.exit_code}
        </Badge>
      </div>

      <div className="p-4">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-emerald-300/70">
            command #{step.index + 1}
          </div>
          <code className="mt-2 block overflow-x-auto text-sm text-emerald-100">
            $ {step.command}
          </code>
        </div>
      </div>

      {step.stdout ? <CodeBlock title="STDOUT" text={step.stdout} /> : null}
      {step.stderr ? <CodeBlock title="STDERR" text={step.stderr} danger /> : null}

      {step.network_indicators?.length ? (
        <div className="mt-4">
          <div className="mb-2 text-sm text-zinc-500">Network Indicators</div>
          <TagList items={step.network_indicators} tone="fuchsia" />
        </div>
      ) : null}

      {step.related_syscalls?.length ? (
        <div className="mt-4">
          <div className="mb-2 text-sm text-zinc-500">Related Syscalls</div>
          <div className="max-h-56 space-y-2 overflow-y-auto rounded-xl border border-white/10 bg-black/35 p-4">
            {step.related_syscalls.map((syscall: string, index: number) => (
              <code key={`${syscall}-${index}`} className="block text-xs text-zinc-400">
                {syscall}
              </code>
            ))}
          </div>
        </div>
      ) : null}
      </div>
    </div>
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
