"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function AttackChainPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/dashboard/overview`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) {
    return (
      <main className="mx-auto max-w-7xl p-10">
        <h1 className="text-4xl font-black bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
          Loading attack chains...
        </h1>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl p-10">
      <div className="mb-10">
        <h1 className="text-5xl font-black tracking-tight bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-500 bg-clip-text text-transparent">
          Attack Chain Explorer
        </h1>

        <p className="mt-3 text-zinc-400">
          Visualized behavior chains reconstructed from sandbox telemetry.
        </p>
      </div>

      <div className="space-y-8">
        {data.top_attack_chains.map(([chain, count]: any) => (
          <ChainCard key={chain} chain={chain} count={count} />
        ))}
      </div>
    </main>
  );
}

function ChainCard({ chain, count }: { chain: string; count: number }) {
  const stages = chain.split(" -> ");

  return (
    <div className="rounded-3xl border border-zinc-800 bg-zinc-950/70 p-8 shadow-xl shadow-violet-950/20 backdrop-blur">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-violet-300">
            Attack Chain
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Observed {count} time{count === 1 ? "" : "s"}
          </p>
        </div>

        <div className="rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-2 text-sm text-violet-300">
          severity path
        </div>
      </div>

      <div className="relative pl-8">
        <div className="absolute left-4 top-3 h-[calc(100%-24px)] w-px bg-gradient-to-b from-violet-500 via-fuchsia-500 to-purple-700" />

        <div className="space-y-7">
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
      <div className="absolute -left-[29px] mt-1 h-7 w-7 rounded-full border border-violet-400 bg-zinc-950 shadow-lg shadow-violet-500/40">
        <div className="m-2 h-3 w-3 rounded-full bg-gradient-to-r from-violet-400 to-fuchsia-500" />
      </div>

      <div className="flex-1 rounded-2xl border border-zinc-800 bg-black/40 p-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-zinc-100">
            {stage}
          </h3>

          <span className="text-xs text-zinc-500">
            Step {index + 1}
          </span>
        </div>

        <p className="text-sm text-zinc-400">
          {describeStage(stage)}
        </p>

        {!isLast && (
          <div className="mt-4 text-xs text-violet-400">
            ↓ next behavior stage
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