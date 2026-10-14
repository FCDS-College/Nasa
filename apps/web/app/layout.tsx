import type { Metadata } from "next";
import "./globals.css";

import { AppShell } from "@/components/layout/AppShell";
import { ChatProvider } from "@/lib/context/ChatContext";

import { Inter, JetBrains_Mono } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

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
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <ChatProvider>
          <AppShell>{children}</AppShell>
        </ChatProvider>
      </body>
    </html>
  );
}
