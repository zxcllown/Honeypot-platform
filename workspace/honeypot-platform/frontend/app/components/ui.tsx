"use client";

import Link from "next/link";
import { type ReactNode, useState } from "react";

export const numberFormatter = new Intl.NumberFormat("en-US");

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <main className="liquid-shell min-h-screen px-5 py-6 text-zinc-100 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl">{children}</div>
    </main>
  );
}

export function LoadingState({
  kicker = "Syncing telemetry",
  title,
}: {
  kicker?: string;
  title: string;
}) {
  return (
    <PageShell>
      <div className="flex min-h-[70vh] items-center">
        <div>
          <div className="mb-5 h-2 w-32 overflow-hidden rounded-full bg-zinc-800">
            <div className="liquid-progress h-full w-2/3 rounded-full" />
          </div>
          <p className="text-sm font-medium uppercase tracking-[0.22em] text-violet-200">
            {kicker}
          </p>
          <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">
            {title}
          </h1>
        </div>
      </div>
    </PageShell>
  );
}

export function Hero({
  kicker,
  title,
  description,
  actions,
  stats,
  variant = "command",
}: {
  kicker: string;
  title: string;
  description: string;
  actions?: ReactNode;
  stats?: ReactNode;
  variant?: "command" | "investigation" | "control" | "terminal" | "federated";
}) {
  return (
    <header className={`mb-8 rounded-2xl p-6 ${heroSurface(variant)}`}>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className={`text-xs font-semibold uppercase tracking-[0.24em] ${heroKicker(variant)}`}>
            {kicker}
          </p>
          <h1 className="mt-3 text-4xl font-semibold text-white sm:text-6xl">
            {title}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
            {description}
          </p>
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
      {stats ? <div className="mt-6">{stats}</div> : null}
    </header>
  );
}

export function Panel({
  title,
  children,
  action,
  className = "",
  variant = "glass",
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
  variant?: "glass" | "table" | "dossier" | "terminal" | "control" | "calm";
}) {
  return (
    <section className={`${panelSurface(variant)} h-full rounded-2xl p-5 ${className}`}>
      <div className="mb-5 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        <span className={`h-px flex-1 ${panelRule(variant)}`} />
        {action}
      </div>
      {children}
    </section>
  );
}

function heroSurface(variant: "command" | "investigation" | "control" | "terminal" | "federated") {
  if (variant === "investigation") {
    return "glass-panel border-cyan-200/15 bg-[linear-gradient(135deg,rgba(34,211,238,0.12),rgba(255,255,255,0.05)_42%,rgba(99,102,241,0.08))]";
  }
  if (variant === "control") {
    return "glass-panel border-emerald-200/15 bg-[linear-gradient(135deg,rgba(16,185,129,0.12),rgba(255,255,255,0.045)_46%,rgba(245,158,11,0.08))]";
  }
  if (variant === "terminal") {
    return "border border-emerald-300/20 bg-[linear-gradient(180deg,rgba(2,6,23,0.92),rgba(3,7,18,0.78))] shadow-[0_24px_80px_rgba(0,0,0,0.48),inset_0_1px_0_rgba(110,231,183,0.12)]";
  }
  if (variant === "federated") {
    return "glass-panel border-sky-200/15 bg-[linear-gradient(135deg,rgba(14,165,233,0.11),rgba(255,255,255,0.045)_44%,rgba(16,185,129,0.08))]";
  }
  return "glass-panel";
}

function heroKicker(variant: "command" | "investigation" | "control" | "terminal" | "federated") {
  if (variant === "investigation") return "text-cyan-200";
  if (variant === "control") return "text-emerald-200";
  if (variant === "terminal") return "text-emerald-200";
  if (variant === "federated") return "text-sky-200";
  return "text-violet-200";
}

function panelSurface(variant: "glass" | "table" | "dossier" | "terminal" | "control" | "calm") {
  if (variant === "table") {
    return "border border-white/10 bg-black/30 shadow-[0_18px_60px_rgba(0,0,0,0.34)]";
  }
  if (variant === "dossier") {
    return "border border-cyan-200/14 bg-[linear-gradient(180deg,rgba(8,47,73,0.22),rgba(17,24,39,0.66))] shadow-[0_20px_70px_rgba(8,47,73,0.16)]";
  }
  if (variant === "terminal") {
    return "border border-emerald-300/18 bg-[linear-gradient(180deg,rgba(0,0,0,0.72),rgba(2,6,23,0.88))] shadow-[0_20px_70px_rgba(0,0,0,0.42)]";
  }
  if (variant === "control") {
    return "border border-emerald-200/14 bg-[linear-gradient(135deg,rgba(6,78,59,0.26),rgba(24,24,27,0.68))] shadow-[0_20px_70px_rgba(6,78,59,0.14)]";
  }
  if (variant === "calm") {
    return "border border-white/10 bg-white/[0.035] shadow-[0_16px_52px_rgba(0,0,0,0.28)]";
  }
  return "glass-panel";
}

function panelRule(variant: "glass" | "table" | "dossier" | "terminal" | "control" | "calm") {
  if (variant === "dossier") return "bg-gradient-to-r from-cyan-300/50 to-transparent";
  if (variant === "terminal") return "bg-gradient-to-r from-emerald-300/45 to-transparent";
  if (variant === "control") return "bg-gradient-to-r from-emerald-300/45 to-transparent";
  if (variant === "table") return "bg-gradient-to-r from-zinc-300/25 to-transparent";
  if (variant === "calm") return "bg-gradient-to-r from-sky-300/30 to-transparent";
  return "bg-gradient-to-r from-violet-300/60 to-transparent";
}

export function MetricCard({
  title,
  value,
  detail,
  tone = "violet",
}: {
  title: string;
  value: ReactNode;
  detail?: string;
  tone?: "violet" | "emerald" | "red" | "amber" | "zinc";
}) {
  const dot = {
    violet: "bg-violet-300 shadow-[0_0_14px_rgba(167,139,250,0.42)]",
    emerald: "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.34)]",
    red: "bg-red-300 shadow-[0_0_14px_rgba(252,165,165,0.34)]",
    amber: "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.34)]",
    zinc: "bg-zinc-300 shadow-[0_0_14px_rgba(212,212,216,0.24)]",
  }[tone];

  return (
    <div className="glass-panel rounded-2xl p-5 transition duration-300 hover:-translate-y-1">
      <div className="mb-5 flex items-center justify-between">
        <p className="text-sm text-zinc-400">{title}</p>
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
      </div>
      <div className="text-3xl font-semibold text-white sm:text-4xl">
        {typeof value === "number" ? numberFormatter.format(value) : value}
      </div>
      {detail ? <p className="mt-3 text-sm text-zinc-500">{detail}</p> : null}
    </div>
  );
}

export function ButtonLink({
  href,
  children,
  tone = "violet",
}: {
  href: string;
  children: ReactNode;
  tone?: "violet" | "zinc" | "emerald" | "red";
}) {
  return (
    <Link href={href} className={`inline-flex items-center rounded-xl px-4 py-3 text-sm font-medium ${buttonTone(tone)}`}>
      {children}
    </Link>
  );
}

export function ActionButton({
  children,
  onClick,
  tone = "violet",
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  tone?: "violet" | "zinc" | "emerald" | "red" | "amber";
  disabled?: boolean;
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center rounded-xl px-4 py-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${buttonTone(tone)}`}
    >
      {children}
    </button>
  );
}

function buttonTone(tone: "violet" | "zinc" | "emerald" | "red" | "amber") {
  if (tone === "emerald") {
    return "border border-emerald-400/30 bg-emerald-400/10 text-emerald-100 hover:bg-emerald-400/20";
  }
  if (tone === "red") {
    return "border border-red-400/30 bg-red-400/10 text-red-100 hover:bg-red-400/20";
  }
  if (tone === "amber") {
    return "border border-amber-400/30 bg-amber-400/10 text-amber-100 hover:bg-amber-400/20";
  }
  if (tone === "zinc") {
    return "border border-white/10 bg-white/[0.045] text-zinc-200 hover:bg-white/10";
  }
  return "glass-button text-violet-50";
}

export function Badge({
  children,
  tone = "violet",
}: {
  children: ReactNode;
  tone?: "violet" | "emerald" | "red" | "amber" | "zinc" | "fuchsia";
}) {
  const className = {
    violet: "border-violet-300/20 bg-violet-300/10 text-violet-100",
    emerald: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
    red: "border-red-300/25 bg-red-300/10 text-red-100",
    amber: "border-amber-300/25 bg-amber-300/10 text-amber-100",
    zinc: "border-white/10 bg-white/[0.045] text-zinc-300",
    fuchsia: "border-fuchsia-300/25 bg-fuchsia-300/10 text-fuchsia-100",
  }[tone];

  return (
    <span className={`inline-flex rounded-lg border px-2.5 py-1 text-xs font-semibold ${className}`}>
      {children}
    </span>
  );
}

export function Empty({ label = "No data yet" }: { label?: string }) {
  return <p className="text-sm text-zinc-500">{label}</p>;
}

export function InfoGrid({ data }: { data: Array<[string, ReactNode]> }) {
  return (
    <div className="grid gap-3 text-sm">
      {data.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-4 border-b border-white/10 pb-3 last:border-b-0 last:pb-0">
          <span className="text-zinc-500">{label}</span>
          <span className="min-w-0 text-right text-zinc-200">{value ?? "-"}</span>
        </div>
      ))}
    </div>
  );
}

export function TagList({
  items,
  tone = "violet",
}: {
  items?: Array<string | number | boolean>;
  tone?: "violet" | "emerald" | "red" | "amber" | "zinc" | "fuchsia";
}) {
  if (!items || items.length === 0) return <Empty />;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <Badge key={`${String(item)}-${index}`} tone={tone}>
          {String(item)}
        </Badge>
      ))}
    </div>
  );
}

export function CommandList({ items }: { items?: string[] }) {
  if (!items || items.length === 0) return <Empty />;
  return (
    <div className="space-y-2">
      {items.map((cmd, index) => (
        <code
          key={`${cmd}-${index}`}
          className="block overflow-x-auto rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-xs text-zinc-300"
        >
          {cmd}
        </code>
      ))}
    </div>
  );
}

export function SeverityBar({ value }: { value?: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-zinc-500">-</span>;
  }

  const percent = value <= 1 ? Math.round(value * 100) : Math.round(value);
  const tone = percent >= 80 ? "bg-red-300" : percent >= 50 ? "bg-amber-300" : "bg-violet-300";

  return (
    <div className="w-32">
      <div className="mb-1 flex justify-between text-xs text-zinc-400">
        <span>{percent}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className={`h-2 rounded-full ${tone}`} style={{ width: `${Math.min(Math.max(percent, 4), 100)}%` }} />
      </div>
    </div>
  );
}

export function Tabs({
  tabs,
}: {
  tabs: Array<{ id: string; label: string; content: ReactNode; hidden?: boolean }>;
}) {
  const visibleTabs = tabs.filter((tab) => !tab.hidden);
  const [active, setActive] = useState(visibleTabs[0]?.id);
  const current = visibleTabs.find((tab) => tab.id === active) ?? visibleTabs[0];

  return (
    <div>
      <div className="mb-5 flex gap-2 overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.035] p-1">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`shrink-0 rounded-xl px-4 py-2 text-sm transition ${
              active === tab.id
                ? "bg-violet-300/15 text-violet-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.16)]"
                : "text-zinc-400 hover:bg-white/[0.055] hover:text-zinc-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {current?.content}
    </div>
  );
}

export function ProgressList({ items }: { items?: Array<[string, number]> }) {
  if (!items || items.length === 0) return <Empty />;

  const max = Math.max(...items.map((item) => item[1]), 1);
  return (
    <div className="space-y-4">
      {items.map(([name, count]) => (
        <div key={name}>
          <div className="mb-2 flex justify-between gap-4 text-sm">
            <span className="min-w-0 text-zinc-300">{formatLabel(name)}</span>
            <span className="font-medium text-violet-100">{numberFormatter.format(count)}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="liquid-progress h-2 rounded-full"
              style={{ width: `${Math.max((count / max) * 100, 8)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function formatLabel(value?: string | null) {
  if (!value) return "-";
  return value.replaceAll("_", " ");
}

export function classificationTone(value?: string | null) {
  if (value === "malicious") return "red";
  if (value === "mixed") return "amber";
  if (value === "benign") return "emerald";
  return "violet";
}
