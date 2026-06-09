"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  ActionButton,
  Badge,
  ButtonLink,
  Empty,
  Hero,
  InfoGrid,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
  formatLabel,
} from "../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type HoneypotStatus = "running" | "stopped" | "restarting" | "maintenance";

type HoneypotNode = {
  node_id: string;
  name: string;
  status: HoneypotStatus;
  honeypot_type: string;
  host: string;
  port: number;
  version: string | null;
  sessions_total?: number;
  updated_at: string;
};

type HoneypotsResponse = {
  items: HoneypotNode[];
  count: number;
};

type HoneypotDraft = {
  node_id: string;
  name: string;
  honeypot_type: string;
  host: string;
  port: string;
  version: string;
  status: HoneypotStatus;
};

type Notice = {
  tone: "emerald" | "red";
  message: string;
};

const emptyDraft: HoneypotDraft = {
  node_id: "",
  name: "",
  honeypot_type: "ssh",
  host: "0.0.0.0",
  port: "2222",
  version: "1.0.0",
  status: "stopped",
};

export default function HoneypotsPage() {
  const [data, setData] = useState<HoneypotsResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  async function load() {
    try {
      setData(await requestJson<HoneypotsResponse>("/honeypots"));
    } catch (loadError) {
      setNotice({
        tone: "red",
        message: loadError instanceof Error ? loadError.message : "Failed to load honeypots",
      });
      setData({ items: [], count: 0 });
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  async function createHoneypot(draft: HoneypotDraft) {
    setBusy("create");
    setNotice(null);
    try {
      const node = await requestJson<HoneypotNode>("/honeypots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(draft)),
      });
      setNotice({ tone: "emerald", message: `${node.name} created` });
      await load();
      return true;
    } catch (createError) {
      setNotice({
        tone: "red",
        message: createError instanceof Error ? createError.message : "Failed to create honeypot",
      });
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function action(nodeId: string, actionName: "enable" | "disable" | "restart") {
    setBusy(`${nodeId}-${actionName}`);
    setNotice(null);
    try {
      await requestJson(`/honeypots/${nodeId}/${actionName}`, { method: "POST" });
      window.setTimeout(load, actionName === "restart" ? 900 : 150);
    } catch (actionError) {
      setNotice({
        tone: "red",
        message: actionError instanceof Error ? actionError.message : "Action failed",
      });
    } finally {
      window.setTimeout(() => {
        setBusy(null);
      }, actionName === "restart" ? 1200 : 250);
    }
  }

  if (!data) return <LoadingState title="Loading honeypots" />;

  const running = data.items.filter((node) => node.status === "running").length;
  const stopped = data.items.filter((node) => node.status !== "running").length;
  const sessions = data.items.reduce((sum, node) => sum + (node.sessions_total ?? 0), 0);

  return (
    <PageShell>
      <Hero
        kicker="Control plane"
        title="Honeypot Management"
        description="Create deception nodes, tune exposed services, and control lifecycle state from your account scope."
        variant="control"
        stats={
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard title="Nodes" value={data.count} detail="registered honeypots" />
            <MetricCard title="Running" value={running} detail={`${stopped} not running`} tone="emerald" />
            <MetricCard title="Sessions" value={sessions} detail="captured by nodes" />
          </div>
        }
      />

      {notice ? <NoticeBanner notice={notice} /> : null}

      <div className="grid gap-4 xl:grid-cols-[0.76fr_1.24fr]">
        <Panel title="Add Honeypot" variant="control" action={<Badge tone="emerald">owner scoped</Badge>}>
          <HoneypotForm busy={busy === "create"} mode="create" onSubmit={createHoneypot} />
        </Panel>

        <Panel title="Fleet" variant="table">
          {data.items.length ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {data.items.map((node) => {
                const nodeBusy = busy?.startsWith(`${node.node_id}-`)
                  ? busy.split("-").at(-1) ?? null
                  : null;
                return (
                  <NodeCard
                    key={node.node_id}
                    node={node}
                    busy={nodeBusy}
                    onAction={action}
                  />
                );
              })}
            </div>
          ) : (
            <Empty label="No honeypots yet" />
          )}
        </Panel>
      </div>
    </PageShell>
  );
}

function HoneypotForm({
  busy,
  mode,
  initial,
  onSubmit,
}: {
  busy: boolean;
  mode: "create" | "edit";
  initial?: HoneypotNode;
  onSubmit: (draft: HoneypotDraft) => Promise<boolean> | boolean;
}) {
  const [draft, setDraft] = useState<HoneypotDraft>(() =>
    initial
      ? {
          node_id: initial.node_id,
          name: initial.name,
          honeypot_type: initial.honeypot_type,
          host: initial.host,
          port: String(initial.port),
          version: initial.version ?? "",
          status: initial.status,
        }
      : emptyDraft,
  );
  const canSubmit = useMemo(() => {
    return (
      draft.node_id.trim().length >= 3 &&
      draft.name.trim().length >= 2 &&
      draft.honeypot_type.trim().length >= 2 &&
      draft.host.trim().length >= 2 &&
      Number(draft.port) >= 1 &&
      Number(draft.port) <= 65535
    );
  }, [draft]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const ok = await onSubmit(draft);
    if (ok && mode === "create") {
      setDraft(emptyDraft);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="Node ID"
          value={draft.node_id}
          onChange={(value) => setDraft((current) => ({ ...current, node_id: slugify(value) }))}
          disabled={mode === "edit"}
        />
        <Field
          label="Name"
          value={draft.name}
          onChange={(value) => setDraft((current) => ({ ...current, name: value }))}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="Type"
          value={draft.honeypot_type}
          onChange={(value) => setDraft((current) => ({ ...current, honeypot_type: value }))}
        />
        <Field
          label="Version"
          value={draft.version}
          onChange={(value) => setDraft((current) => ({ ...current, version: value }))}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_8rem]">
        <Field
          label="Host"
          value={draft.host}
          onChange={(value) => setDraft((current) => ({ ...current, host: value }))}
        />
        <Field
          label="Port"
          value={draft.port}
          type="number"
          onChange={(value) => setDraft((current) => ({ ...current, port: value }))}
        />
      </div>

      <label className="block">
        <span className="mb-2 block text-sm text-zinc-400">Status</span>
        <select
          value={draft.status}
          onChange={(event) =>
            setDraft((current) => ({ ...current, status: event.target.value as HoneypotStatus }))
          }
          className="w-full rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm text-white outline-none transition focus:border-emerald-300/45"
        >
          <option value="stopped">Stopped</option>
          <option value="running">Running</option>
          <option value="maintenance">Maintenance</option>
        </select>
      </label>

      <ActionButton disabled={busy || !canSubmit} tone={mode === "create" ? "emerald" : "violet"}>
        {busy ? "Saving..." : mode === "create" ? "Create honeypot" : "Save changes"}
      </ActionButton>
    </form>
  );
}

function NodeCard({
  node,
  busy,
  onAction,
}: {
  node: HoneypotNode;
  busy: string | null;
  onAction: (nodeId: string, actionName: "enable" | "disable" | "restart") => void;
}) {
  const visibleStatus = busy === "restart" ? "restarting" : node.status;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-white">{node.name}</h2>
          <p className="mt-1 font-mono text-xs text-emerald-100">{node.node_id}</p>
        </div>
        <Status value={visibleStatus} />
      </div>

      <InfoGrid
        data={[
          ["Type", formatLabel(node.honeypot_type)],
          ["Endpoint", `${node.host}:${node.port}`],
          ["Version", node.version ?? "-"],
          ["Sessions", node.sessions_total ?? 0],
          ["Updated", node.updated_at],
        ]}
      />

      {busy === "restart" ? (
        <div className="mt-5 rounded-2xl border border-violet-300/20 bg-violet-300/10 p-4">
          <div className="mb-3 flex items-center justify-between text-sm">
            <span className="text-violet-100">Restart sequence</span>
            <span className="text-zinc-400">health probe</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div className="liquid-progress h-2 w-3/4 rounded-full" />
          </div>
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-3">
        <ButtonLink href={`/honeypots/${node.node_id}`} tone="zinc">Inspect</ButtonLink>
        <ActionButton
          onClick={() => onAction(node.node_id, "enable")}
          tone="emerald"
          disabled={busy !== null || node.status === "running"}
        >
          Enable
        </ActionButton>
        <ActionButton
          onClick={() => onAction(node.node_id, "disable")}
          tone="red"
          disabled={busy !== null || node.status !== "running"}
        >
          Disable
        </ActionButton>
        <ActionButton
          onClick={() => onAction(node.node_id, "restart")}
          tone="violet"
          disabled={busy !== null}
        >
          Restart
        </ActionButton>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm text-zinc-400">{label}</span>
      <input
        value={value}
        type={type}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm text-white outline-none transition disabled:cursor-not-allowed disabled:opacity-55 focus:border-emerald-300/45"
      />
    </label>
  );
}

function Status({ value }: { value: string }) {
  if (value === "running") return <Badge tone="emerald">running</Badge>;
  if (value === "restarting") return <Badge tone="amber">restarting</Badge>;
  if (value === "maintenance") return <Badge tone="violet">maintenance</Badge>;
  return <Badge tone="red">{value}</Badge>;
}

function NoticeBanner({ notice }: { notice: Notice }) {
  const styles =
    notice.tone === "emerald"
      ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100"
      : "border-red-300/25 bg-red-300/10 text-red-100";

  return <div className={`mb-4 rounded-2xl border p-4 text-sm ${styles}`}>{notice.message}</div>;
}

async function requestJson<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  if (!API) throw new Error("NEXT_PUBLIC_API_URL is not configured");

  const response = await fetch(`${API}${path}`, init);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return payload as T;
}

function toPayload(draft: HoneypotDraft) {
  return {
    node_id: draft.node_id.trim(),
    name: draft.name.trim(),
    honeypot_type: draft.honeypot_type.trim(),
    host: draft.host.trim(),
    port: Number(draft.port),
    version: draft.version.trim() || null,
    status: draft.status,
  };
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9-_]/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 80);
}
