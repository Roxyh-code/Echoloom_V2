import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { AccountShell } from "@/components/account-shell";
export const metadata: Metadata = {
  title: "EchoLoom · Your favorite character, by your side",
  description:
    "Everyday companionship with your favorite fictional characters. Chat, share stories, and connect your daily plans.",
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
            <span className="badge">companion</span>
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
          A little closer, every day.
          <span>
            Fictional characters · AI generated · Local single-user prototype
          </span>
        </footer>
      </body>
    </html>
  );
}
