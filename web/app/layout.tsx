import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { AccountShell } from "@/components/account-shell";
export const metadata: Metadata = {
  title: "EchoLoom · Bring characters to life",
  description: "Create, shape and meet your fictional characters.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/characters" className="brand">
            <span className="brand-mark">e</span> EchoLoom
            <span className="badge">studio</span>
          </Link>
          <nav>
            <Link href="/characters">My Characters</Link>
            <Link href="/characters/new" className="nav-create">
              ＋ Create Character
            </Link>
          </nav>
        </header>
        <AccountShell>{children}</AccountShell>
        <footer className="site-footer">
          Make room for imagination.
          <span>
            Fictional characters · AI generated · Local single-user prototype
          </span>
        </footer>
      </body>
    </html>
  );
}
