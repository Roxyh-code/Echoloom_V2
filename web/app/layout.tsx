import type { Metadata } from "next";

import "./globals.css";
import { AppChrome } from "@/components/app-chrome";
export const metadata: Metadata = {
  title: "EchoLoom · Create characters. Discover their stories.",
  description:
    "Everyday companionship with your favorite fictional characters. Chat, share stories, and connect your daily plans.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
