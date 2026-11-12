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
  ShieldCheck,
  FlaskConical,
  Microscope,
  Activity,
  FileSearch,
  History,
  Network,
} from "lucide-react";

// Primary navigation: every page a judge needs is one click away.
const NAV = [
  { href: "/", label: "Fire Safety Dashboard", icon: ShieldCheck },
  { href: "/explorer", label: "Flame Outcome Explorer", icon: FlaskConical },
  { href: "/experiments", label: "Flight Test Browser", icon: Sparkles },
  { href: "/chat", label: "Ask the NASA Corpus", icon: MessageSquare },
  { href: "/search", label: "Search Evidence", icon: FileSearch },
  { href: "/knowledge", label: "Knowledge Graph", icon: Network },
  { href: "/analysis", label: "Image & Video Analysis", icon: Microscope },
  { href: "/history", label: "Analysis History", icon: History },
  { href: "/status", label: "System Status", icon: Activity },
];
import { useChat } from "@/lib/context/ChatContext";

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
          <Link href="/" className="group flex items-center gap-3">
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
                Fire-Safety Insights
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
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--border-subtle)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--text-muted)';
            }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Primary navigation */}
        <nav aria-label="Main" className="px-3 pt-3">
          <ul className="flex flex-col gap-0.5">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname?.startsWith(href);
              return (
                <li key={href}>
                  <Link href={href} onClick={() => { if (typeof window !== "undefined" && window.innerWidth < 1024) closeSidebar(); }}
                        aria-current={active ? "page" : undefined}
                        className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium"
                        style={{
                          background: active ? "rgba(59,130,246,0.12)" : "transparent",
                          border: `1px solid ${active ? "rgba(59,130,246,0.25)" : "transparent"}`,
                          color: active ? "var(--text-primary)" : "var(--text-secondary)",
                        }}>
                    <Icon className="h-4 w-4" style={{ color: active ? "var(--accent-flame)" : "var(--text-dim)" }} aria-hidden="true" />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="mx-4 mt-3" style={{ borderTop: "1px solid var(--border-subtle)" }} />

        {/* New Chat Button */}
        <div className="p-4 pb-2">
          <button
            id="new-chat-btn"
            onClick={handleNewChat}
            className="group relative flex w-full items-center justify-center gap-2.5 rounded-xl px-4 py-3 text-sm font-semibold"
            style={{
              background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(96,165,250,0.12))',
              border: '1px solid rgba(59,130,246,0.3)',
              color: 'var(--text-primary)',
              transition: 'all var(--transition-default)',
              boxShadow: 'var(--shadow-glow-sm)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(59,130,246,0.5)';
              e.currentTarget.style.boxShadow = 'var(--shadow-glow-md)';
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(59,130,246,0.22), rgba(96,165,250,0.18))';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(59,130,246,0.3)';
              e.currentTarget.style.boxShadow = 'var(--shadow-glow-sm)';
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(96,165,250,0.12))';
            }}
          >
            <Plus className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90"
                  style={{ color: 'var(--accent-flame)' }} />
            <span>New Research Chat</span>
          </button>
        </div>

        {/* Search Filter */}
        {sessions.length > 2 && (
          <div className="px-4 py-1">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5" style={{ color: 'var(--text-dim)' }} />
              <input
                id="sidebar-search"
                type="text"
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                placeholder="Search history..."
                className="w-full rounded-lg py-2 pl-8 pr-3 text-xs focus:outline-none"
                style={{
                  background: 'var(--border-subtle)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-sans)',
                  transition: 'border-color var(--transition-fast)',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'rgba(59,130,246,0.4)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
              />
            </div>
          </div>
        )}

        {/* History Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-2">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.15em]"
               style={{ color: 'var(--text-muted)' }}>
            <Clock className="h-3.5 w-3.5" style={{ color: 'var(--text-dim)' }} />
            <span>Chat History</span>
            <span className="ml-1.5 rounded-full px-1.5 py-0.5 text-[9px]"
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
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent-danger)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-dim)'; }}
            >
              Clear all
            </button>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
          {filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl mb-4"
                   style={{
                     background: 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(96,165,250,0.05))',
                     border: '1px solid var(--border-subtle)',
                   }}>
                <Sparkles className="h-7 w-7" style={{ color: 'var(--text-dim)', opacity: 0.6 }} />
              </div>
              <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                No conversations yet
              </p>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-dim)' }}>
                Start a new research chat
              </p>
            </div>
          ) : (
            filteredSessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  className="group relative flex items-center justify-between rounded-xl px-3 py-2.5 cursor-pointer"
                  style={{
                    background: isActive
                      ? 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(96,165,250,0.06))'
                      : 'transparent',
                    border: isActive
                      ? '1px solid rgba(59,130,246,0.2)'
                      : '1px solid transparent',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    transition: 'all var(--transition-fast)',
                    boxShadow: isActive ? '0 2px 12px rgba(59,130,246,0.08)' : 'none',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'var(--border-subtle)';
                      e.currentTarget.style.color = 'var(--text-primary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-secondary)';
                    }
                  }}
                >
                  <div className="flex min-w-0 items-center gap-2.5 flex-1 pr-2">
                    <MessageSquare
                      className="h-4 w-4 shrink-0"
                      style={{
                        color: isActive ? 'var(--accent-flame)' : 'var(--text-dim)',
                        transition: 'color var(--transition-fast)',
                      }}
                    />
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="truncate text-xs font-medium leading-snug">
                        {session.title || "Untitled Chat"}
                      </span>
                      <span className="text-[10px] mt-0.5"
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
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-md shrink-0"
                    style={{
                      color: 'var(--text-dim)',
                      transition: 'all var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = 'var(--accent-danger)';
                      e.currentTarget.style.background = 'rgba(239,68,68,0.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = 'var(--text-dim)';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4" style={{ borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.05)' }}>
          <div className="rounded-xl p-3 text-[11px]"
               style={{
                 background: 'var(--border-subtle)',
                 border: '1px solid var(--border-subtle)',
                 color: 'var(--text-muted)',
               }}>
            <div className="flex items-center justify-between">
              <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>
                NASA Space Apps
              </span>
              <span className="px-2 py-0.5 rounded-md text-[9px] font-semibold"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--accent-flame)',
                      background: 'rgba(59,130,246,0.08)',
                      border: '1px solid rgba(59,130,246,0.15)',
                    }}>
                2026
              </span>
            </div>
            <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-dim)' }}>
              NASA PSI flight data · NTRS reports
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
