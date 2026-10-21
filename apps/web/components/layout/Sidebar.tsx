"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import {
  Flame,
  Plus,
  MessageSquare,
  Trash2,
  Search,
  Clock,
  X,
  Sparkles,
  LayoutDashboard,
  FileText,
  Fingerprint,
  Beaker,
  Network,
  Activity,
} from "lucide-react";
import { useChat } from "@/lib/context/ChatContext";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Research Chat", href: "/chat", icon: MessageSquare },
  { label: "Flame Analysis", href: "/analysis", icon: Flame },
  { label: "Scientific Search", href: "/search", icon: Search },
  { label: "Document Explorer", href: "/documents", icon: FileText },
  { label: "Evidence Inspector", href: "/evidence", icon: Fingerprint },
  { label: "Experiment Matrix", href: "/experiments", icon: Beaker },
  { label: "Analysis History", href: "/history", icon: Clock },
  { label: "Knowledge Base", href: "/knowledge", icon: Network },
  { label: "System Status", href: "/status", icon: Activity },
];

function formatRelativeTime(timestamp: number) {
  const diff = Math.max(0, Date.now() - timestamp);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

export function Sidebar() {
  const {
    sessions,
    activeSessionId,
    selectSession,
    createNewSession,
    deleteSession,
    clearAllSessions,
    isSidebarOpen,
    closeSidebar,
  } = useChat();

  const router = useRouter();
  const pathname = usePathname();
  const [filterText, setFilterText] = useState("");

  const handleNewChat = () => {
    createNewSession();
    if (pathname !== "/chat") {
      router.push("/chat");
    }
  };

  const handleSelectSession = (id: string) => {
    selectSession(id);
    if (pathname !== "/chat") {
      router.push("/chat");
    }
  };

  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(filterText.toLowerCase())
  );

  return (
    <>
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div
          onClick={closeSidebar}
          aria-hidden="true"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-md lg:hidden"
          style={{ transition: 'opacity var(--transition-default)' }}
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-full w-[280px] sm:w-[300px] flex-col shadow-2xl lg:sticky lg:top-0 lg:h-screen lg:z-auto ${
          isSidebarOpen
            ? "translate-x-0 opacity-100"
            : "-translate-x-full opacity-0 lg:w-0 lg:overflow-hidden lg:opacity-0 pointer-events-none lg:pointer-events-none"
        }`}
        style={{
          background: 'var(--bg-card)',
          backdropFilter: 'blur(32px) saturate(1.4)',
          borderRight: '1px solid var(--border-subtle)',
          transition: 'all var(--transition-default)',
        }}
      >
        {/* Branding Header */}
        <div className="flex h-16 shrink-0 items-center justify-between px-5"
             style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <Link href="/dashboard" className="group flex items-center gap-3">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl"
                 style={{
                   background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(96,165,250,0.1))',
                   border: '1px solid rgba(59,130,246,0.25)',
                 }}>
              <Flame className="h-5 w-5" style={{ color: 'var(--accent-flame)' }} />
              <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100"
                   style={{
                     background: 'linear-gradient(135deg, rgba(59,130,246,0.25), rgba(96,165,250,0.15))',
                     transition: 'opacity var(--transition-default)',
                   }} />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] font-bold tracking-[0.2em] uppercase"
                    style={{ color: 'var(--text-primary)' }}>
                Flame in Freefall
              </span>
              <span className="text-[10px] font-medium tracking-wide"
                    style={{ color: 'var(--accent-flame)', fontFamily: 'var(--font-mono)', opacity: 0.8 }}>
                NASA Space Apps
              </span>
            </div>
          </Link>

          <button
            type="button"
            onClick={closeSidebar}
            aria-label="Close sidebar"
            className="flex h-8 w-8 items-center justify-center rounded-lg lg:hidden"
            style={{
              color: 'var(--text-muted)',
              transition: 'all var(--transition-fast)',
            }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* 10 Platform Navigation Modules (Task R8) */}
        <div className="px-3 py-2.5 shrink-0" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="px-2 pb-1.5 text-[10px] font-bold uppercase tracking-[0.15em]"
               style={{ color: 'var(--text-dim)' }}>
            Platform Modules
          </div>
          <div className="space-y-0.5 max-h-[220px] overflow-y-auto pr-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => {
                    if (typeof window !== "undefined" && window.innerWidth < 1024) {
                      closeSidebar();
                    }
                  }}
                  className="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all"
                  style={{
                    background: isActive ? 'rgba(59,130,246,0.1)' : 'transparent',
                    color: isActive ? 'var(--accent-flame)' : 'var(--text-secondary)',
                    border: isActive ? '1px solid rgba(59,130,246,0.25)' : '1px solid transparent',
                  }}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" style={{ color: isActive ? 'var(--accent-flame)' : 'var(--text-dim)' }} />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-3 pb-2 shrink-0">
          <button
            id="new-chat-btn"
            onClick={handleNewChat}
            className="group relative flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold"
            style={{
              background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(96,165,250,0.12))',
              border: '1px solid rgba(59,130,246,0.3)',
              color: 'var(--text-primary)',
              transition: 'all var(--transition-default)',
            }}
          >
            <Plus className="h-3.5 w-3.5" style={{ color: 'var(--accent-flame)' }} />
            <span>New Research Chat</span>
          </button>
        </div>

        {/* History Header */}
        <div className="flex items-center justify-between px-5 pt-3 pb-1.5 shrink-0">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.15em]"
               style={{ color: 'var(--text-muted)' }}>
            <Clock className="h-3.5 w-3.5" style={{ color: 'var(--text-dim)' }} />
            <span>Conversations</span>
            <span className="ml-1 rounded-full px-1.5 py-0.2 text-[9px]"
                  style={{
                    background: 'var(--border-subtle)',
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono)',
                  }}>
              {sessions.length}
            </span>
          </div>
          {sessions.length > 0 && (
            <button
              onClick={() => {
                if (confirm("Are you sure you want to clear all chat history?")) {
                  clearAllSessions();
                }
              }}
              title="Clear all conversations"
              className="text-[10px] font-medium"
              style={{
                color: 'var(--text-dim)',
              }}
            >
              Clear
            </button>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-3 py-1 space-y-0.5">
          {filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <Sparkles className="h-5 w-5 mb-2" style={{ color: 'var(--text-dim)', opacity: 0.5 }} />
              <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                No active conversations
              </p>
              <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-dim)' }}>
                Start a research question above
              </p>
            </div>
          ) : (
            filteredSessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  className="group relative flex items-center justify-between rounded-xl px-2.5 py-2 cursor-pointer"
                  style={{
                    background: isActive
                      ? 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(96,165,250,0.06))'
                      : 'transparent',
                    border: isActive
                      ? '1px solid rgba(59,130,246,0.2)'
                      : '1px solid transparent',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}
                >
                  <div className="flex min-w-0 items-center gap-2 flex-1 pr-1.5">
                    <MessageSquare
                      className="h-3.5 w-3.5 shrink-0"
                      style={{ color: isActive ? 'var(--accent-flame)' : 'var(--text-dim)' }}
                    />
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="truncate text-xs font-medium leading-snug">
                        {session.title || "Untitled Chat"}
                      </span>
                      <span className="text-[9px] mt-0.5"
                            style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        {formatRelativeTime(session.updatedAt || session.createdAt)}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSession(session.id);
                    }}
                    title="Delete chat"
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-md shrink-0 text-zinc-500 hover:text-red-400"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-3 shrink-0" style={{ borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.05)' }}>
          <div className="rounded-xl p-2.5 text-[11px]"
               style={{
                 background: 'var(--border-subtle)',
                 border: '1px solid var(--border-subtle)',
               }}>
            <div className="flex items-center justify-between">
              <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>
                NASA Space Apps
              </span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold font-mono"
                    style={{
                      color: 'var(--accent-flame)',
                      background: 'rgba(59,130,246,0.08)',
                    }}>
                v0.1.0
              </span>
            </div>
            <p className="text-[10px] mt-1" style={{ color: 'var(--text-dim)' }}>
              Evidence Grounded • NTRS & PSI
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
