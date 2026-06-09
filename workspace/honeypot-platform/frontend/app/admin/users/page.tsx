"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  ActionButton,
  Badge,
  Empty,
  Hero,
  LoadingState,
  MetricCard,
  PageShell,
  Panel,
} from "../../components/ui";

const API = process.env.NEXT_PUBLIC_API_URL;

type Role = "admin" | "analyst";

type CurrentUser = {
  id: number;
  email: string;
  username: string;
  role: Role;
};

type User = {
  id: number;
  email: string;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type UsersResponse = {
  items: User[];
  count: number;
};

type Notice = {
  tone: "emerald" | "red";
  message: string;
};

export default function AdminUsersPage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [data, setData] = useState<UsersResponse | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  async function loadInitial() {
    try {
      const [me, users] = await Promise.all([
        requestJson<CurrentUser>("/auth/me"),
        requestJson<UsersResponse>("/auth/users"),
      ]);
      setForbidden(false);
      setNotice(null);
      setCurrentUser(me);
      setData(users);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load users";
      if (message.includes("403")) {
        setForbidden(true);
      } else {
        setNotice({ tone: "red", message });
      }
      setData({ items: [], count: 0 });
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadInitial();
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  async function createUser(payload: {
    email: string;
    username: string;
    password: string;
    role: Role;
  }) {
    await mutate("create", async () => {
      const user = await requestJson<User>("/auth/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setNotice({ tone: "emerald", message: `${user.email} created` });
    });
  }

  async function updateUser(userId: number, payload: Partial<Pick<User, "role" | "is_active" | "username">>) {
    await mutate(`update-${userId}`, async () => {
      const user = await requestJson<User>(`/auth/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setNotice({ tone: "emerald", message: `${user.email} updated` });
    });
  }

  async function resetPassword(userId: number, password: string) {
    await mutate(`reset-${userId}`, async () => {
      await requestJson(`/auth/users/${userId}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      setNotice({ tone: "emerald", message: "Password rotated and active sessions revoked" });
    });
  }

  async function mutate(key: string, action: () => Promise<void>) {
    setBusy(key);
    setNotice(null);
    try {
      await action();
      const users = await requestJson<UsersResponse>("/auth/users");
      setData(users);
    } catch (mutationError) {
      setNotice({
        tone: "red",
        message: mutationError instanceof Error ? mutationError.message : "Action failed",
      });
    } finally {
      setBusy(null);
    }
  }

  if (!data) return <LoadingState title="Loading users" />;

  if (forbidden || currentUser?.role !== "admin") {
    return (
      <PageShell>
        <Hero
          kicker="Administration"
          title="Users"
          description="Only admins can create accounts, change roles, disable access, and rotate passwords."
          variant="control"
        />
        <Panel title="Access Required" variant="control">
          <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-5 text-sm leading-6 text-amber-100">
            This page is protected by the API. Sign in with an admin account to manage users.
          </div>
        </Panel>
      </PageShell>
    );
  }

  const admins = data.items.filter((user) => user.role === "admin").length;
  const active = data.items.filter((user) => user.is_active).length;
  const disabled = data.items.length - active;

  return (
    <PageShell>
      <Hero
        kicker="Administration"
        title="Users"
        description="Create accounts, assign operational roles, disable access, and rotate credentials from one place."
        variant="control"
        stats={
          <div className="grid gap-4 md:grid-cols-4">
            <MetricCard title="Users" value={data.count} detail="total accounts" />
            <MetricCard title="Active" value={active} detail="can sign in" tone="emerald" />
            <MetricCard title="Disabled" value={disabled} detail="access locked" tone="red" />
            <MetricCard title="Admins" value={admins} detail="can manage users" tone="amber" />
          </div>
        }
      />

      {notice ? <NoticeBanner notice={notice} /> : null}

      <div className="grid gap-4 xl:grid-cols-[0.78fr_1.22fr]">
        <Panel
          title="Create Account"
          variant="control"
          action={<Badge tone="emerald">admin only</Badge>}
        >
          <CreateUserForm busy={busy === "create"} onSubmit={createUser} />
        </Panel>

        <Panel title="Accounts" variant="table">
          {data.items.length ? (
            <div className="grid gap-3">
              {data.items.map((user) => (
                <UserCard
                  key={`${user.id}-${user.username}`}
                  user={user}
                  currentUserId={currentUser.id}
                  busy={busy}
                  onUpdate={updateUser}
                  onResetPassword={resetPassword}
                />
              ))}
            </div>
          ) : (
            <Empty label="No users found" />
          )}
        </Panel>
      </div>
    </PageShell>
  );
}

function CreateUserForm({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (payload: {
    email: string;
    username: string;
    password: string;
    role: Role;
  }) => void;
}) {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("analyst");
  const passwordScore = useMemo(() => scorePassword(password), [password]);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({ email, username, password, role });
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Email" value={email} onChange={setEmail} type="email" autoComplete="email" />
      <Field label="Username" value={username} onChange={setUsername} autoComplete="username" />
      <Field
        label="Temporary password"
        value={password}
        onChange={setPassword}
        type="password"
        autoComplete="new-password"
      />
      <PasswordMeter score={passwordScore} />

      <SegmentedRole value={role} onChange={setRole} />

      <ActionButton disabled={busy || passwordScore < 4} tone="emerald">
        {busy ? "Creating..." : "Create user"}
      </ActionButton>
    </form>
  );
}

function UserCard({
  user,
  currentUserId,
  busy,
  onUpdate,
  onResetPassword,
}: {
  user: User;
  currentUserId: number;
  busy: string | null;
  onUpdate: (userId: number, payload: Partial<Pick<User, "role" | "is_active" | "username">>) => void;
  onResetPassword: (userId: number, password: string) => void;
}) {
  const [username, setUsername] = useState(user.username);
  const [newPassword, setNewPassword] = useState("");
  const isSelf = user.id === currentUserId;
  const rowBusy = busy === `update-${user.id}` || busy === `reset-${user.id}`;
  const passwordScore = useMemo(() => scorePassword(newPassword), [newPassword]);

  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 shadow-[0_16px_45px_rgba(0,0,0,0.22)]">
      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-base font-semibold text-white">{user.email}</h3>
            {isSelf ? <Badge tone="fuchsia">you</Badge> : null}
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-500">
            <span>created {formatDate(user.created_at)}</span>
            <span>updated {formatDate(user.updated_at)}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 lg:justify-end">
          <Badge tone={user.role === "admin" ? "amber" : "violet"}>{user.role}</Badge>
          <Badge tone={user.is_active ? "emerald" : "red"}>
            {user.is_active ? "active" : "disabled"}
          </Badge>
        </div>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_17rem_11rem]">
        <Field label="Username" value={username} onChange={setUsername} />
        <SegmentedRole
          value={user.role}
          onChange={(role) => onUpdate(user.id, { role })}
          disabled={isSelf || rowBusy}
        />
        <div className="flex items-end">
          <ActionButton
            disabled={isSelf || rowBusy}
            tone={user.is_active ? "red" : "emerald"}
            onClick={() => onUpdate(user.id, { is_active: !user.is_active })}
          >
            {user.is_active ? "Disable" : "Enable"}
          </ActionButton>
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto_auto]">
        <div>
          <Field
            label="New password"
            value={newPassword}
            onChange={setNewPassword}
            type="password"
            autoComplete="new-password"
          />
          {newPassword ? <PasswordMeter score={passwordScore} compact /> : null}
        </div>
        <div className="flex items-end">
          <ActionButton
            disabled={rowBusy || username.trim() === user.username}
            tone="zinc"
            onClick={() => onUpdate(user.id, { username })}
          >
            Save name
          </ActionButton>
        </div>
        <div className="flex items-end">
          <ActionButton
            disabled={rowBusy || passwordScore < 4}
            tone="amber"
            onClick={() => {
              onResetPassword(user.id, newPassword);
              setNewPassword("");
            }}
          >
            Reset password
          </ActionButton>
        </div>
      </div>
    </article>
  );
}

function SegmentedRole({
  value,
  onChange,
  disabled,
}: {
  value: Role;
  onChange: (role: Role) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <span className="mb-2 block text-sm text-zinc-400">Role</span>
      <div className="grid grid-cols-2 gap-1 rounded-xl border border-white/10 bg-black/35 p-1">
        {(["analyst", "admin"] as Role[]).map((role) => (
          <button
            key={role}
            type="button"
            disabled={disabled}
            onClick={() => onChange(role)}
            className={`rounded-lg px-3 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
              value === role
                ? "bg-emerald-300/15 text-emerald-100"
                : "text-zinc-400 hover:bg-white/[0.06] hover:text-zinc-200"
            }`}
          >
            {role}
          </button>
        ))}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm text-zinc-400">{label}</span>
      <input
        value={value}
        type={type}
        autoComplete={autoComplete}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-emerald-300/45"
      />
    </label>
  );
}

function PasswordMeter({ score, compact = false }: { score: number; compact?: boolean }) {
  const width = `${Math.max(score * 25, 6)}%`;
  const tone = score >= 4 ? "bg-emerald-300" : score >= 3 ? "bg-amber-300" : "bg-red-300";

  return (
    <div className={compact ? "mt-2" : ""}>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${tone}`} style={{ width }} />
      </div>
      {!compact ? (
        <p className="mt-2 text-xs text-zinc-500">
          12+ chars, uppercase, lowercase, and digit.
        </p>
      ) : null}
    </div>
  );
}

function NoticeBanner({ notice }: { notice: Notice }) {
  const styles =
    notice.tone === "emerald"
      ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100"
      : "border-red-300/25 bg-red-300/10 text-red-100";

  return (
    <div className={`mb-4 rounded-2xl border p-4 text-sm ${styles}`}>
      {notice.message}
    </div>
  );
}

async function requestJson<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  if (!API) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured");
  }

  const response = await fetch(`${API}${path}`, init);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : `HTTP ${response.status}`;
    throw new Error(`${response.status}: ${detail}`);
  }

  return payload as T;
}

function scorePassword(password: string) {
  return [
    password.length >= 12,
    /[a-z]/.test(password),
    /[A-Z]/.test(password),
    /\d/.test(password),
  ].filter(Boolean).length;
}

function formatDate(value: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
