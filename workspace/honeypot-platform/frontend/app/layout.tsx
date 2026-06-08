import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

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
        <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-black to-zinc-950 text-zinc-100">
          <nav className="sticky top-0 z-50 border-b border-zinc-800 bg-black/50 backdrop-blur-xl">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-8 py-4">
              <Link
                href="/"
                className="text-lg font-black bg-gradient-to-r from-violet-400 to-fuchsia-500 bg-clip-text text-transparent"
              >
                Honeypot Platform
              </Link>

              <div className="flex gap-3 text-sm">
                <NavLink href="/">Overview</NavLink>
                <NavLink href="/sessions">Sessions</NavLink>
                <NavLink href="/attack-chain">Attack Chain</NavLink>
                <NavLink href="/honeypots">Honeypots</NavLink>
              </div>
            </div>
          </nav>

          {children}
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
      className="rounded-full border border-zinc-800 px-4 py-2 text-zinc-300 transition hover:border-violet-500/50 hover:bg-violet-500/10 hover:text-violet-200"
    >
      {children}
    </Link>
  );
}