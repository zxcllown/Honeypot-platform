"use client";

import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL;
const TOKEN_KEY = "honeypot_access_token";

type User = {
  id: number;
  email: string;
  username: string;
  role: string;
};

type AuthResponse = {
  access_token: string;
  user: User;
};

export default function AuthGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"checking" | "login" | "bootstrap" | "ready">(
    API ? "checking" : "ready",
  );
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!API) {
      return;
    }

    installAuthorizedFetch();

    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      fetch(`${API}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => {
          if (!res.ok) throw new Error("Session expired");
          return res.json();
        })
        .then((payload: User) => {
          setUser(payload);
          setStatus("ready");
        })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          loadBootstrapStatus(setStatus, setError);
        });
      return;
    }

    loadBootstrapStatus(setStatus, setError);
  }, []);

  const authContext = useMemo(() => ({ user }), [user]);

  if (status === "checking") {
    return (
      <main className="liquid-shell flex min-h-screen items-center px-5 py-6 text-zinc-100">
        <div className="mx-auto max-w-xl">
          <div className="mb-5 h-2 w-32 overflow-hidden rounded-full bg-zinc-800">
            <div className="liquid-progress h-full w-2/3 rounded-full" />
          </div>
          <p className="text-sm font-medium uppercase tracking-[0.22em] text-violet-200">
            Checking access
          </p>
          <h1 className="mt-3 text-4xl font-semibold text-white">Preparing workspace</h1>
        </div>
      </main>
    );
  }

  if (status === "login" || status === "bootstrap") {
    return (
      <AuthScreen
        mode={status}
        error={error}
        onAuthenticated={(payload) => {
          localStorage.setItem(TOKEN_KEY, payload.access_token);
          setUser(payload.user);
          setStatus("ready");
          setError(null);
        }}
        onError={setError}
      />
    );
  }

  return <AuthContextMarker value={authContext}>{children}</AuthContextMarker>;
}

function AuthContextMarker({
  children,
}: {
  value: { user: User | null };
  children: ReactNode;
}) {
  return <>{children}</>;
}

function AuthScreen({
  mode,
  error,
  onAuthenticated,
  onError,
}: {
  mode: "login" | "bootstrap";
  error: string | null;
  onAuthenticated: (payload: AuthResponse) => void;
  onError: (message: string | null) => void;
}) {
  const [email, setEmail] = useState(mode === "bootstrap" ? "admin@honeypot.local" : "");
  const [username, setUsername] = useState("Admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    onError(null);
    setBusy(true);

    try {
      const response = await fetch(`${API}/auth/${mode}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(
          mode === "bootstrap"
            ? { email, username, password }
            : { email, password },
        ),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail ?? "Authentication failed");
      }

      onAuthenticated(payload);
    } catch (authError) {
      onError(authError instanceof Error ? authError.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="liquid-shell flex min-h-screen items-center px-5 py-6 text-zinc-100">
      <section className="mx-auto grid w-full max-w-5xl gap-5 lg:grid-cols-[1fr_0.85fr]">
        <div className="glass-panel rounded-2xl p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">
            {mode === "bootstrap" ? "First owner setup" : "Secure access"}
          </p>
          <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">
            {mode === "bootstrap" ? "Create platform owner" : "Sign in"}
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-zinc-400">
            {mode === "bootstrap"
              ? "The first account becomes the admin owner and claims existing local telemetry."
              : "Use your platform account to access honeypots, sessions, telemetry, and global views."}
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <Field label="Email" value={email} onChange={setEmail} type="email" />
            {mode === "bootstrap" ? (
              <Field label="Username" value={username} onChange={setUsername} />
            ) : null}
            <Field label="Password" value={password} onChange={setPassword} type="password" />

            {error ? (
              <div className="rounded-xl border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
                {error}
              </div>
            ) : null}

            <button
              disabled={busy}
              className="glass-button inline-flex w-full justify-center rounded-xl px-4 py-3 text-sm font-medium text-violet-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? "Working..." : mode === "bootstrap" ? "Create owner" : "Sign in"}
            </button>
          </form>
        </div>

        <aside className="rounded-2xl border border-emerald-300/15 bg-black/45 p-7 shadow-[0_24px_80px_rgba(0,0,0,0.42)]">
          <h2 className="text-base font-semibold text-white">Security model</h2>
          <div className="mt-5 space-y-4 text-sm leading-6 text-zinc-400">
            <p>Passwords are stored with salted PBKDF2 hashes.</p>
            <p>Access tokens are random bearer tokens stored hashed in the database.</p>
            <p>Honeypots and telemetry are scoped to the authenticated user.</p>
          </div>
        </aside>
      </section>
    </main>
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
        className="w-full rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-violet-300/45"
      />
    </label>
  );
}

function loadBootstrapStatus(
  setStatus: (status: "login" | "bootstrap") => void,
  setError: (message: string | null) => void,
) {
  fetch(`${API}/auth/bootstrap-status`)
    .then((res) => res.json())
    .then((payload: { bootstrap_required: boolean }) => {
      setStatus(payload.bootstrap_required ? "bootstrap" : "login");
    })
    .catch(() => {
      setError("API is not reachable");
      setStatus("login");
    });
}

function installAuthorizedFetch() {
  if (typeof window === "undefined") return;

  const marker = "__honeypotAuthorizedFetchInstalled";
  const win = window as Window & {
    [marker]?: boolean;
  };

  if (win[marker]) return;

  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const token = localStorage.getItem(TOKEN_KEY);
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

    if (token && API && url.startsWith(API)) {
      const headers = new Headers(init.headers);
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return originalFetch(input, { ...init, headers });
    }

    return originalFetch(input, init);
  };

  win[marker] = true;
}
