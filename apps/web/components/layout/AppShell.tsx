import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative flex min-h-screen w-full flex-col lg:flex-row noise-overlay"
      style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>

      {/* Deep-space backdrop: stars, two nebulae and a faint horizon glow. Fixed, so it stays put while pages scroll. */}
      <div aria-hidden="true" className="starfield"><span /></div>
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute -left-[12%] -top-[22%] h-[60vw] w-[60vw] rounded-full animate-pulse-glow"
          style={{ background: 'radial-gradient(circle, rgba(79,140,255,0.16) 0%, transparent 65%)' }} />
        <div className="absolute -bottom-[30%] -right-[10%] h-[55vw] w-[55vw] rounded-full animate-pulse-glow"
          style={{ background: 'radial-gradient(circle, rgba(167,139,250,0.12) 0%, transparent 65%)', animationDelay: '2.5s' }} />
        <div className="absolute left-[40%] top-[30%] h-[30vw] w-[30vw] rounded-full animate-pulse-glow"
          style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.07) 0%, transparent 70%)', animationDelay: '4s' }} />
        {/* Perspective grid: the "deck" of the console */}
        <div className="absolute inset-x-0 bottom-0 h-[45vh] opacity-[0.22]"
          style={{
            backgroundImage: `linear-gradient(rgba(124,180,255,0.18) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(124,180,255,0.18) 1px, transparent 1px)`,
            backgroundSize: '64px 64px',
            maskImage: 'linear-gradient(to top, black, transparent)',
            WebkitMaskImage: 'linear-gradient(to top, black, transparent)',
            transform: 'perspective(600px) rotateX(58deg)',
            transformOrigin: 'bottom',
          }} />
      </div>

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
