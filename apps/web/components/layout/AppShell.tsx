import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen w-full flex-col lg:flex-row noise-overlay"
      style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>

      {/* Ambient Background Orbs */}
      <div className="pointer-events-none absolute -left-[15%] -top-[20%] h-[55vw] w-[55vw] rounded-full animate-pulse-glow"
        style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)' }} />
      <div className="pointer-events-none absolute -bottom-[25%] -right-[15%] h-[50vw] w-[50vw] rounded-full animate-pulse-glow"
        style={{ background: 'radial-gradient(circle, rgba(96,165,250,0.1) 0%, transparent 70%)', animationDelay: '2.5s' }} />
      <div className="pointer-events-none absolute left-[35%] top-[20%] h-[35vw] w-[35vw] rounded-full animate-pulse-glow"
        style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.06) 0%, transparent 70%)', animationDelay: '4s' }} />

      {/* Grid Pattern Overlay */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `
               linear-gradient(var(--border-subtle) 1px, transparent 1px),
               linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)
             `,
          backgroundSize: '60px 60px'
        }} />

      {/* Main Layout */}
      <div className="relative z-10 flex flex-col lg:flex-row min-h-screen w-full">
        <Sidebar />
        <div className="relative flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="relative flex flex-col flex-1 w-full">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}