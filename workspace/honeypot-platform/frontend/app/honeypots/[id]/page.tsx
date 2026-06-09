"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ActionButton,
  Badge,
  ButtonLink,
  Hero,
  InfoGrid,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
  formatLabel,
} from "../../components/ui";

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
  updated_at?: string;
};

type HoneypotDraft = {
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

export default function HoneypotDetailPage() {
  const params = useParams();
  const router = useRouter();
  const nodeId = String(params.id);
  const [node, setNode] = useState<HoneypotNode | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const load = useCallback(async () => {
    try {
      setNode(await requestJson<HoneypotNode>(`/honeypots/${nodeId}`));
    } catch (loadError) {
      setNotice({
        tone: "red",
        message: loadError instanceof Error ? loadError.message : "Failed to load honeypot",
      });
    }
  }, [nodeId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [load]);

  async function save(draft: HoneypotDraft) {
    setBusy("save");
    setNotice(null);
    try {
      const updated = await requestJson<HoneypotNode>(`/honeypots/${nodeId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(draft)),
      });
      setNode(updated);
      setNotice({ tone: "emerald", message: `${updated.name} updated` });
      return true;
    } catch (saveError) {
      setNotice({
        tone: "red",
        message: saveError instanceof Error ? saveError.message : "Failed to update honeypot",
      });
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function lifecycle(actionName: "enable" | "disable" | "restart") {
    setBusy(actionName);
    setNotice(null);
    try {
      const result = await requestJson<{ node: HoneypotNode }>(`/honeypots/${nodeId}/${actionName}`, {
        method: "POST",
      });
      setNode(result.node);
      setNotice({ tone: "emerald", message: `${formatLabel(actionName)} completed` });
    } catch (actionError) {
      setNotice({
        tone: "red",
        message: actionError instanceof Error ? actionError.message : "Action failed",
      });
    } finally {
      window.setTimeout(() => setBusy(null), actionName === "restart" ? 900 : 150);
    }
  }

  async function remove() {
    setBusy("delete");
    setNotice(null);
    try {
      await requestJson(`/honeypots/${nodeId}`, { method: "DELETE" });
      router.push("/honeypots");
    } catch (deleteError) {
      setNotice({
        tone: "red",
        message: deleteError instanceof Error ? deleteError.message : "Failed to delete honeypot",
      });
      setBusy(null);
    }
  }

  if (!node) return <LoadingState title="Loading honeypot" />;

  const displayStatus = busy === "restart" ? "restarting" : node.status;

  return (
    <PageShell>
      <Hero
        kicker="Node profile"
        title={node.name ?? node.node_id}
        description="Edit the service profile, control lifecycle state, and keep the node scoped to your account."
        variant="control"
        actions={
          <>
            <ButtonLink href="/honeypots" tone="zinc">Fleet</ButtonLink>
            <ActionButton
              onClick={() => lifecycle("enable")}
              tone="emerald"
              disabled={busy !== null || node.status === "running"}
            >
              Enable
            </ActionButton>
            <ActionButton
              onClick={() => lifecycle("disable")}
              tone="red"
              disabled={busy !== null || node.status !== "running"}
            >
              Disable
            </ActionButton>
            <ActionButton onClick={() => lifecycle("restart")} disabled={busy !== null}>
              Restart
            </ActionButton>
          </>
        }
        stats={
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard
              title="Status"
              value={<Status value={displayStatus} />}
              detail="current lifecycle state"
              tone={node.status === "running" ? "emerald" : "red"}
            />
            <MetricCard title="Port" value={node.port ?? "-"} detail={node.host} />
            <MetricCard title="Sessions" value={node.sessions_total ?? 0} detail="captured locally" />
          </div>
        }
      />

      {notice ? <NoticeBanner notice={notice} /> : null}

      <div className="grid gap-4 lg:grid-cols-[0.82fr_1.18fr]">
        <Panel title="Service" variant="control">
          <InfoGrid
            data={[
              ["Node ID", <span className="font-mono text-violet-200" key="node">{node.node_id}</span>],
              ["Type", formatLabel(node.honeypot_type)],
              ["Host", node.host],
              ["Port", node.port],
              ["Version", node.version ?? "-"],
              ["Updated", node.updated_at ?? "-"],
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
        </Panel>

        <Panel title="Edit Honeypot" variant="table" action={<Badge tone="emerald">user owned</Badge>}>
          <HoneypotForm initial={node} busy={busy === "save"} onSubmit={save} />
        </Panel>
      </div>

      <div className="mt-4">
        <Panel title="Danger Zone" variant="calm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-semibold text-white">Delete honeypot</div>
              <p className="mt-1 text-sm text-zinc-500">
                Removes only this node profile from your account.
              </p>
            </div>
            <ActionButton disabled={busy !== null} tone="red" onClick={remove}>
              {busy === "delete" ? "Deleting..." : "Delete"}
            </ActionButton>
          </div>
        </Panel>
      </div>
    </PageShell>
  );
}

function HoneypotForm({
  initial,
  busy,
  onSubmit,
}: {
  initial: HoneypotNode;
  busy: boolean;
  onSubmit: (draft: HoneypotDraft) => Promise<boolean> | boolean;
}) {
  const [draft, setDraft] = useState<HoneypotDraft>(() => ({
    name: initial.name,
    honeypot_type: initial.honeypot_type,
    host: initial.host,
    port: String(initial.port),
    version: initial.version ?? "",
    status: initial.status,
  }));
  const canSubmit = useMemo(() => {
    return (
      draft.name.trim().length >= 2 &&
      draft.honeypot_type.trim().length >= 2 &&
      draft.host.trim().length >= 2 &&
      Number(draft.port) >= 1 &&
      Number(draft.port) <= 65535
    );
  }, [draft]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSubmit(draft);
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="Name"
          value={draft.name}
          onChange={(value) => setDraft((current) => ({ ...current, name: value }))}
        />
        <Field
          label="Type"
          value={draft.honeypot_type}
          onChange={(value) => setDraft((current) => ({ ...current, honeypot_type: value }))}
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

      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="Version"
          value={draft.version}
          onChange={(value) => setDraft((current) => ({ ...current, version: value }))}
        />
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
      </div>

      <ActionButton disabled={busy || !canSubmit} tone="violet">
        {busy ? "Saving..." : "Save changes"}
      </ActionButton>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm text-zinc-400">{label}</span>
      <input
        value={value}
        type={type}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm text-white outline-none transition focus:border-emerald-300/45"
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
    name: draft.name.trim(),
    honeypot_type: draft.honeypot_type.trim(),
    host: draft.host.trim(),
    port: Number(draft.port),
    version: draft.version.trim() || null,
    status: draft.status,
  };
}
