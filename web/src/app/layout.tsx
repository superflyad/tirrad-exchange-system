import type { Metadata } from "next";
import Link from "next/link";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "TES Dashboard",
  description: "Operator dashboard for Tirrad Exchange System runs",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <Link href="/" className="brand"><span>TES</span><small>Exchange Ops</small></Link>
            <nav>
              <Link href="/">Dashboard</Link>
              <Link href="/runs">Runs</Link>
              <Link href="/health">Health</Link>
            </nav>
          </aside>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
