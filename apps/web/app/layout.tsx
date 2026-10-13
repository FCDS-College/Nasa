import type { Metadata } from "next";
// Self-hosted fonts (Sub-phase 2H): bundled at build time, so the UI renders the same with no internet.
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

import { AppShell } from "@/components/layout/AppShell";
import { ChatProvider } from "@/lib/context/ChatContext";

export const metadata: Metadata = {
  title: "Flame in Freefall — NASA Space Apps Research Lab",
  description:
    "AI-powered scientific research platform for NASA microgravity combustion experiments. Synthesize evidence, analyze flame imagery, and explore the knowledge graph.",
  keywords: [
    "NASA",
    "Space Apps",
    "microgravity",
    "combustion",
    "flame analysis",
    "scientific research",
    "AI",
  ],
  authors: [{ name: "Flame in Freefall Team" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ChatProvider>
          <AppShell>{children}</AppShell>
        </ChatProvider>
      </body>
    </html>
  );
}
