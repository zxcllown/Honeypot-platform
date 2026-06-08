"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function SessionsPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/sessions`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) {
    return (
      <main className="mx-auto max-w-7xl p-10">
        <h1 className="text-4xl font-black bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent">
          Loading sessions...
        </h1>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl p-10">
      <div className="mb-8">
        <h1 className="text-5xl font-black tracking-tight bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-500 bg-clip-text text-transparent">
          Sessions Explorer
        </h1>

        <p className="mt-3 text-zinc-400">
          Explore classified honeypot sessions, sandbox verdicts and telemetry severity.
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/70 shadow-xl shadow-violet-950/20">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-900/70 text-zinc-400">
            <tr>
              <th className="px-5 py-4">Session</th>
              <th className="px-5 py-4">Class</th>
              <th className="px-5 py-4">Confidence</th>
              <th className="px-5 py-4">Severity</th>
              <th className="px-5 py-4">Attack Chain</th>
              <th className="px-5 py-4">Sandbox</th>
              <th className="px-5 py-4"></th>
            </tr>
          </thead>

          <tbody>
            {data.items.map((session: any) => (
              <tr
                key={session.session_id}
                className="border-b border-zinc-900 transition hover:bg-violet-500/5"
              >
                <td className="px-5 py-4 font-mono text-violet-300">
                  {session.session_id}
                </td>

                <td className="px-5 py-4">
                  <Badge value={session.classification} />
                </td>

                <td className="px-5 py-4 text-zinc-300">
                  {(session.confidence * 100).toFixed(1)}%
                </td>

                <td className="px-5 py-4">
                  <Severity value={session.severity_score} />
                </td>

                <td className="px-5 py-4 text-zinc-300">
                  {session.attack_chain?.length
                    ? session.attack_chain.join(" → ")
                    : "—"}
                </td>

                <td className="px-5 py-4 text-zinc-400">
                  {session.sandbox?.level || "—"} / {session.sandbox?.exit_code ?? "—"}
                </td>

                <td className="px-5 py-4 text-right">
                  <Link
                    href={`/sessions/${session.session_id}`}
                    className="rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-2 text-violet-300 hover:bg-violet-500/20"
                  >
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

function Badge({ value }: { value: string }) {
  const color =
    value === "malicious"
      ? "bg-red-500/10 text-red-300 border-red-500/30"
      : value === "mixed"
      ? "bg-yellow-500/10 text-yellow-300 border-yellow-500/30"
      : "bg-emerald-500/10 text-emerald-300 border-emerald-500/30";

  return (
    <span className={`rounded-full border px-3 py-1 text-xs ${color}`}>
      {value}
    </span>
  );
}

function Severity({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-zinc-500">—</span>;
  }

  const percent = Math.round(value * 100);

  return (
    <div className="w-28">
      <div className="mb-1 flex justify-between text-xs text-zinc-400">
        <span>{percent}%</span>
      </div>

      <div className="h-2 rounded bg-zinc-800">
        <div
          className="h-2 rounded bg-gradient-to-r from-violet-500 to-fuchsia-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}