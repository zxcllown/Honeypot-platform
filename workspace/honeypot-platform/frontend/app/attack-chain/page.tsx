"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL;

type CountPair = [string, number];

type DashboardOverview = {
  top_attack_chains: CountPair[];
};

export default function AttackChainPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);

  useEffect(() => {
    fetch(`${API}/dashboard/overview`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) {
    return (
      <main className="liquid-shell min-h-screen px-5 py-6 text-zinc-100 sm:px-8 lg:px-10">
        <div className="mx-auto flex min-h-[70vh] max-w-6xl items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-200">
              Reconstructing path
            </p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">
              Loading attack chains
            </h1>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="liquid-shell min-h-screen px-5 py-6 text-zinc-100 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <header className="glass-panel mb-8 flex flex-col gap-6 rounded-2xl p-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-200">
              Behavior graph
            </p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-6xl">
              Attack Chain Explorer
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
              Reconstructed behavior paths from sandbox telemetry, grouped by
              observed sequence and frequency.
            </p>
          </div>

          <Link
            href="/"
            className="glass-button inline-flex w-fit items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-violet-50"
          >
            <span className="text-violet-200">←</span>
            Dashboard
          </Link>
        </header>

        <div className="space-y-5">
          {data.top_attack_chains.map(([chain, count]) => (
            <ChainCard key={chain} chain={chain} count={count} />
          ))}
        </div>
      </div>
    </main>
  );
}

function ChainCard({ chain, count }: { chain: string; count: number }) {
  const stages = chain.split(" -> ");

  return (
    <div className="glass-panel rounded-2xl p-5 sm:p-6">
      <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">
            Attack Chain
          </h2>

          <p className="mt-2 text-sm text-zinc-400">
            Observed {count} time{count === 1 ? "" : "s"}
          </p>
        </div>

        <div className="rounded-xl border border-violet-300/20 bg-violet-300/10 px-3 py-2 text-sm font-medium text-violet-100/90">
          {stages.length} stages
        </div>
      </div>

      <div className="relative pl-8">
        <div className="absolute left-4 top-3 h-[calc(100%-24px)] w-px bg-gradient-to-b from-violet-300/80 via-violet-400/80 to-violet-700/80 shadow-[0_0_12px_rgba(139,92,246,0.34)]" />

        <div className="space-y-5">
          {stages.map((stage, index) => (
            <ChainNode
              key={`${stage}-${index}`}
              stage={stage}
              index={index}
              isLast={index === stages.length - 1}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ChainNode({
  stage,
  index,
  isLast,
}: {
  stage: string;
  index: number;
  isLast: boolean;
}) {
  return (
    <div className="relative flex items-start gap-5">
      <div className="glass-panel absolute -left-[29px] mt-1 grid h-7 w-7 place-items-center rounded-full border-violet-300/45 shadow-lg shadow-violet-950/40">
        <div className="h-2.5 w-2.5 rounded-full bg-violet-300/85 shadow-[0_0_12px_rgba(167,139,250,0.48)]" />
      </div>

      <div className="glass-panel flex-1 rounded-2xl p-4 transition duration-300 hover:-translate-y-0.5 hover:border-violet-300/45 sm:p-5">
        <div className="mb-2 flex items-start justify-between gap-4">
          <h3 className="text-lg font-semibold text-zinc-100">
            {stage}
          </h3>

          <span className="shrink-0 rounded-lg border border-violet-300/16 bg-violet-300/8 px-2.5 py-1 text-xs text-violet-100/85">
            {String(index + 1).padStart(2, "0")}
          </span>
        </div>

        <p className="text-sm leading-6 text-zinc-400">
          {describeStage(stage)}
        </p>

        {!isLast && (
          <div className="mt-4 text-xs font-medium uppercase tracking-[0.18em] text-violet-200">
            Next behavior stage
          </div>
        )}
      </div>
    </div>
  );
}

function describeStage(stage: string) {
  const descriptions: Record<string, string> = {
    Discovery:
      "Attacker collects environment information such as user, files, system state or available commands.",
    Execution:
      "Attacker attempts to execute commands, scripts or shell-based payloads.",
    "Command and Control":
      "Attacker attempts outbound communication or reverse shell behavior.",
    "Privilege Escalation":
      "Attacker attempts to gain elevated privileges or abuse sudo-like behavior.",
    Persistence:
      "Attacker attempts to maintain access through scheduled jobs, startup files or services.",
    "Payload Download":
      "Attacker attempts to retrieve external payloads using tools such as wget or curl.",
    "Defense Evasion / Cleanup":
      "Attacker attempts to remove traces, rename files or hide activity.",
  };

  return descriptions[stage] || "Observed behavior stage reconstructed from telemetry.";
}
