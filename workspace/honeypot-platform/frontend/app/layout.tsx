import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import AuthGate from "./components/AuthGate";

export const metadata: Metadata = {
  title: "Honeypot Platform",
  description: "Adaptive Deception Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen text-zinc-100">
          <nav className="sticky top-0 z-50 border-b border-white/10 bg-black/45 backdrop-blur-xl">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
              <Link
                href="/"
                className="text-lg font-black bg-gradient-to-r from-violet-300 to-fuchsia-300 bg-clip-text text-transparent"
              >
                Honeypot Platform
              </Link>

              <div className="flex gap-2 overflow-x-auto text-sm">
                <NavLink href="/">Overview</NavLink>
                <NavLink href="/dashboard/recent-sessions">Recent</NavLink>
                <NavLink href="/dashboard/global-threat-view">Global</NavLink>
                <NavLink href="/sessions">Sessions</NavLink>
                <NavLink href="/honeypots">Honeypots</NavLink>
                <NavLink href="/admin/users">Admin</NavLink>
              </div>
            </div>
          </nav>

          <AuthGate>{children}</AuthGate>
        </div>
      </body>
    </html>
  );
}

function NavLink({
  href,
  children,

}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="shrink-0 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2 text-zinc-300 transition hover:border-violet-300/35 hover:bg-violet-300/10 hover:text-violet-100"
    >
      {children}
    </Link>

  );
}
