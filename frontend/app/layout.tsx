import "./globals.css";
import Link from "next/link";
import { Providers } from "./providers";

export const metadata = { title: "AgentX · Agent Orchestration" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <Providers>
          <div className="flex min-h-screen">
            <aside className="w-56 border-r border-white/10 p-4 space-y-2">
              <div className="text-lg font-semibold mb-4">⚡ AgentX</div>
              <NavLink href="/">Dashboard</NavLink>
              <NavLink href="/agents">Agents</NavLink>
              <NavLink href="/workflows">Workflows</NavLink>
              <NavLink href="/runs">Runs</NavLink>
              <NavLink href="/monitor">Live monitor</NavLink>
            </aside>
            <main className="flex-1 p-6">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="block px-2 py-1.5 rounded hover:bg-white/5 text-sm">
      {children}
    </Link>
  );
}
