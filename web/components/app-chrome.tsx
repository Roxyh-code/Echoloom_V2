"use client";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { AccountShell } from "./account-shell";
export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const creator = ["/creator", "/rehearsal"].some((p) =>
    pathname.startsWith(p),
  );
  return (
    <>
      {!creator && (
        <header className="site-header">
          <Link href="/companion" className="brand">
            <span className="brand-mark">e</span> EchoLoom
            <span className="badge">companion</span>
          </Link>
          <nav>
            <Link href="/rehearsal">Rehearsal studio ↗</Link>
            <Link href="/companion">My Characters</Link>
            <Link href="/companion/new" className="nav-create">
              ＋ Create Character
            </Link>
          </nav>
        </header>
      )}
      <AccountShell hideStatus={creator}>{children}</AccountShell>
      {!creator && (
        <footer className="site-footer">
          A little closer, every day.
          <span>
            Fictional characters · AI generated · Local single-user prototype
          </span>
        </footer>
      )}
    </>
  );
}
