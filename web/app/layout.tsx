import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "EchoLoom · 让角色鲜活起来",
  description: "创造、塑造，与你的虚构角色相遇。",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="site-header">
          <Link href="/characters" className="brand">
            <span className="brand-mark">e</span> EchoLoom
            <span className="badge">studio</span>
          </Link>
          <nav>
            <Link href="/characters">我的角色</Link>
            <Link href="/characters/new" className="nav-create">
              ＋ 创造角色
            </Link>
          </nav>
        </header>
        {children}
        <footer className="site-footer">
          为想象留一个位置。<span>虚构角色 · AI 生成 · 本地单用户原型</span>
        </footer>
      </body>
    </html>
  );
}
