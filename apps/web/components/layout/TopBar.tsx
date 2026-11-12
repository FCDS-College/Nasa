"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { fetchHealth } from "@/lib/api/client";
import { SystemHealth } from "@/lib/api/types";
import {
  Activity,
  RefreshCw,
  PanelLeft,
  Flame,
  Plus,
} from "lucide-react";
import { useChat } from "@/lib/context/ChatContext";

export function TopBar() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const { toggleSidebar, isSidebarOpen, activeSession, createNewSession } = useChat();
  const pathname = usePathname() ?? "/";
  const PAGE_TITLES: [string, string][] = [
    ["/explorer", "Flame Outcome Explorer"], ["/investigations", "Investigation"], ["/experiments", "Flight Test Browser"],
    ["/search", "Search Evidence"], ["/analysis", "Image & Video Analysis"], ["/history", "Analysis History"],
    ["/evidence", "Evidence"], ["/status", "System Status"], ["/knowledge", "Knowledge Graph"],
  ];
  const title = pathname === "/" ? "Fire Safety Dashboard"
    : pathname.startsWith("/chat") ? (activeSession?.title || "Ask the NASA Corpus")
    : PAGE_TITLES.find(([prefix]) => pathname.startsWith(prefix))?.[1] ?? "Flame in Freefall";

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const data = await fetchHealth();
        if (mounted) {
          setHealth(data);
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    };
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const getStatusColor = (status: "ok" | "degraded" | "down" | undefined) => {
    switch (status) {
      case "ok": return "var(--accent-success)";
      case "degraded": return "var(--accent-warning)";
      case "down": return "var(--accent-danger)";
      default: return "var(--text-dim)";
    }
  };

  const getStatusDotColor = (status: "ok" | "degraded" | "down" | undefined) => {
    switch (status) {
      case "ok": return "rgba(16,185,129,0.8)";
      case "degraded": return "rgba(245,158,11,0.8)";
      case "down": return "rgba(239,68,68,0.8)";
      default: return "rgba(71,85,105,0.8)";
    }
  };

  return (
    <header
      className="sticky top-0 flex h-14 sm:h-[60px] shrink-0 items-center justify-between px-4 sm:px-6 z-40"
      style={{
        background: 'var(--bg-secondary)',
        backdropFilter: 'blur(20px) saturate(1.3)',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      {/* Left */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        <button
          id="toggle-sidebar-btn"
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle navigation"
          className="flex h-9 w-9 items-center justify-center rounded-lg active:scale-95"
          title={isSidebarOpen ? "Collapse history" : "Open history"}
          style={{
            background: 'var(--border-subtle)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--accent-flame)',
            transition: 'all var(--transition-fast)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--border-subtle)';
            e.currentTarget.style.borderColor = 'rgba(59,130,246,0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--border-subtle)';
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
          }}
        >
          <PanelLeft className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={createNewSession}
          aria-label="New chat"
          className="flex h-9 w-9 items-center justify-center rounded-lg active:scale-95 sm:hidden"
          style={{
            background: 'var(--border-subtle)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--accent-flame)',
            transition: 'all var(--transition-fast)',
          }}
        >
          <Plus className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg sm:hidden"
               style={{
                 background: 'rgba(59,130,246,0.1)',
                 border: '1px solid rgba(59,130,246,0.2)',
               }}>
            <Flame className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
          </div>
          <div className="flex flex-col min-w-0">
            <h1 className="text-xs sm:text-sm font-semibold flex items-center gap-1.5 truncate max-w-[200px] sm:max-w-md"
                style={{ color: 'var(--text-primary)' }}>
              <span className="truncate">{title}</span>
            </h1>
            <span className="text-[9px] sm:text-[10px] hidden sm:inline truncate"
                  style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              Build: {health?.metrics.build_id || "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Status Indicator */}
        <div className="flex items-center gap-2 rounded-full px-3 py-1.5"
             style={{
               background: 'var(--border-subtle)',
               border: '1px solid var(--border-subtle)',
             }}>
          {loading ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin" style={{ color: 'var(--text-muted)' }} />
          ) : (
            <div className="relative flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full"
                   style={{
                     background: getStatusDotColor(health?.status),
                     boxShadow: `0 0 8px ${getStatusDotColor(health?.status)}`,
                   }} />
              <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4"
                        style={{ color: getStatusColor(health?.status) }} />
            </div>
          )}
          <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            {health?.status ? health.status.toUpperCase() : "…"}
          </span>
        </div>

        {/* Version Badge */}
        {health?.version && (
          <div className="hidden md:flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px]"
               style={{
                 background: 'var(--border-subtle)',
                 border: '1px solid var(--border-subtle)',
                 fontFamily: 'var(--font-mono)',
                 color: 'var(--text-secondary)',
               }}>
            v{health.version}
          </div>
        )}
      </div>
    </header>
  );
}
