import type { Metadata } from "next";
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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <ChatProvider>
          <AppShell>{children}</AppShell>
        </ChatProvider>
      </body>
    </html>
  );
}
