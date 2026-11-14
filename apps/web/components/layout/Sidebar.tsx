"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import {
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
  FireExtinguisher,
} from "lucide-react";
import { useChat } from "@/lib/context/ChatContext";

// Primary navigation: every page a judge needs is one click away, grouped like a mission console.
const NAV_GROUPS = [
  {
    label: "Mission",
    items: [
      { href: "/", label: "Fire Safety Dashboard", icon: ShieldCheck },
      { href: "/explorer", label: "Flame Outcome Explorer", icon: FlaskConical },
      { href: "/suppression", label: "Suppression Advisor", icon: FireExtinguisher },
      { href: "/experiments", label: "Flight Test Browser", icon: Sparkles },
    ],
  },
  {
    label: "Research",
    items: [
      { href: "/chat", label: "Ask the NASA Corpus", icon: MessageSquare },
      { href: "/search", label: "Search Evidence", icon: FileSearch },
      { href: "/knowledge", label: "Knowledge Graph", icon: Network },
    ],
  },
  {
    label: "Lab",
    items: [
      { href: "/analysis", label: "Image & Video Analysis", icon: Microscope },
      { href: "/history", label: "Analysis History", icon: History },
      { href: "/status", label: "System Status", icon: Activity },
    ],
  },
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

/** The brand mark: a spherical microgravity flame inside an orbit ring. */
export function FlameMark({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <defs>
        <radialGradient id="fm-core" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="30%" stopColor="#9CC6FF" />
          <stop offset="70%" stopColor="#4F8CFF" />
          <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="fm-ring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#22D3EE" />
          <stop offset="100%" stopColor="#A78BFA" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="11" fill="url(#fm-core)" className="flame-breathe" />
      <circle cx="20" cy="20" r="4" fill="#fff" opacity="0.9" />
      <g className="orbit-spin">
        <ellipse cx="20" cy="20" rx="18" ry="7" fill="none" stroke="url(#fm-ring)" strokeWidth="1.3" transform="rotate(-28 20 20)" opacity="0.9" />
        <circle cx="35.5" cy="12" r="1.8" fill="#22D3EE" />
      </g>
    </svg>
  );
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
        className={`fixed inset-y-0 left-0 z-50 flex h-full w-[280px] sm:w-[292px] flex-col shadow-2xl lg:sticky lg:top-0 lg:h-screen lg:z-auto ${
          isSidebarOpen
            ? "translate-x-0 opacity-100"
            : "-translate-x-full opacity-0 lg:w-0 lg:overflow-hidden lg:opacity-0 pointer-events-none lg:pointer-events-none"
        }`}
        style={{
          background: 'linear-gradient(180deg, rgba(12,15,26,0.92) 0%, rgba(7,9,15,0.95) 100%)',
          backdropFilter: 'blur(32px) saturate(1.4)',
          borderRight: '1px solid var(--border-default)',
          transition: 'all var(--transition-default)',
        }}
      >
        {/* Edge light along the sidebar's right border */}
        <div aria-hidden="true" className="pointer-events-none absolute right-0 top-0 h-full w-px"
             style={{ background: 'linear-gradient(180deg, transparent, rgba(79,140,255,0.5) 30%, rgba(167,139,250,0.35) 70%, transparent)' }} />

        {/* Branding Header */}
        <div className="flex h-16 shrink-0 items-center justify-between px-5"
             style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <Link href="/" className="group flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl"
                 style={{
                   background: 'radial-gradient(circle at 50% 50%, rgba(79,140,255,0.22), rgba(12,15,26,0.6) 70%)',
                   border: '1px solid rgba(124,180,255,0.28)',
                   boxShadow: '0 0 24px -6px rgba(79,140,255,0.7)',
                 }}>
              <FlameMark size={34} />
            </div>
            <div className="flex flex-col">
              <span className="text-[12px] font-extrabold tracking-[0.22em] uppercase"
                    style={{ color: 'var(--text-primary)' }}>
                Flame in Freefall
              </span>
              <span className="text-[10px] font-medium tracking-[0.12em] uppercase text-gradient-flame"
                    style={{ fontFamily: 'var(--font-mono)' }}>
                Fire-Safety Insights
              </span>
            </div>
          </Link>

          <button
            type="button"
            onClick={closeSidebar}
            aria-label="Close sidebar"
            className="btn-ghost flex h-8 w-8 items-center justify-center rounded-lg lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Primary navigation */}
        <nav aria-label="Main" className="shrink-0 px-3 pt-3">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-2">
              <p className="flex items-center gap-2 px-3 pb-1.5 pt-2 text-[9.5px] font-semibold uppercase tracking-[0.24em]"
                 style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {group.label}
                <span className="h-px flex-1" style={{ background: 'linear-gradient(90deg, var(--border-default), transparent)' }} />
              </p>
              <ul className="flex flex-col gap-0.5">
                {group.items.map(({ href, label, icon: Icon }) => {
                  const active = href === "/" ? pathname === "/" : pathname?.startsWith(href);
                  return (
                    <li key={href}>
                      <Link href={href} onClick={() => { if (typeof window !== "undefined" && window.innerWidth < 1024) closeSidebar(); }}
                            aria-current={active ? "page" : undefined}
                            className="nav-item flex items-center gap-2.5 rounded-lg px-3 py-[7px] text-[12.5px] font-medium"
                            style={{ color: active ? undefined : "var(--text-secondary)" }}>
                        <span className="flex h-6 w-6 items-center justify-center rounded-md"
                              style={{
                                background: active ? 'rgba(79,140,255,0.2)' : 'transparent',
                                boxShadow: active ? '0 0 14px -2px rgba(79,140,255,0.7)' : 'none',
                              }}>
                          <Icon className="h-[15px] w-[15px]" style={{ color: active ? "var(--accent-ember)" : "var(--text-muted)" }} aria-hidden="true" />
                        </span>
                        {label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* New Chat Button */}
        <div className="px-4 pb-2 pt-2">
          <button
            id="new-chat-btn"
            onClick={handleNewChat}
            className="btn-primary group flex w-full items-center justify-center gap-2.5 rounded-xl px-4 py-2.5 text-sm font-semibold"
          >
            <Plus className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
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
                aria-label="Search chat history"
                className="w-full rounded-lg py-2 pl-8 pr-3 text-xs focus:outline-none"
                style={{
                  background: 'rgba(124,180,255,0.05)',
                  border: '1px solid var(--border-default)',
                  color: 'var(--text-secondary)',
                }}
              />
            </div>
          </div>
        )}

        {/* History Header */}
        <div className="flex items-center justify-between px-5 pt-3 pb-2">
          <div className="flex items-center gap-1.5 text-[9.5px] font-semibold uppercase tracking-[0.22em]"
               style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            <Clock className="h-3.5 w-3.5" />
            <span>Chat log</span>
            <span className="ml-1 rounded-full px-1.5 py-0.5 text-[9px]"
                  style={{ background: 'rgba(124,180,255,0.08)', color: 'var(--text-secondary)' }}>
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
              className="text-[10px] font-medium hover:text-red-400"
              style={{ color: 'var(--text-dim)', transition: 'color var(--transition-fast)' }}
            >
              Clear all
            </button>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-3 py-1 space-y-0.5">
          {filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <div className="relative mb-3 flex h-12 w-12 items-center justify-center">
                <span className="ping-ring absolute inset-2 rounded-full" style={{ border: '1px solid rgba(79,140,255,0.4)' }} />
                <Sparkles className="h-5 w-5" style={{ color: 'var(--text-muted)' }} />
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
                  className="nav-item group relative flex items-center justify-between rounded-lg px-3 py-2 cursor-pointer"
                  aria-current={isActive ? "page" : undefined}
                  style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                >
                  <div className="flex min-w-0 items-center gap-2.5 flex-1 pr-2">
                    <MessageSquare
                      className="h-3.5 w-3.5 shrink-0"
                      style={{ color: isActive ? 'var(--accent-ember)' : 'var(--text-dim)' }}
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
                    aria-label="Delete chat"
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 rounded-md shrink-0 hover:bg-red-500/10 hover:text-red-400"
                    style={{ color: 'var(--text-dim)', transition: 'all var(--transition-fast)' }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Footer: mission patch */}
        <div className="p-4" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <div className="relative overflow-hidden rounded-xl p-3"
               style={{
                 background: 'linear-gradient(135deg, rgba(79,140,255,0.1), rgba(167,139,250,0.06))',
                 border: '1px solid var(--border-default)',
               }}>
            <div aria-hidden="true" className="absolute -right-6 -top-6 h-20 w-20 rounded-full"
                 style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.25), transparent 70%)' }} />
            <div className="relative flex items-center justify-between">
              <span className="text-[11px] font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
                NASA Space Apps
              </span>
              <span className="rounded-md px-2 py-0.5 text-[9px] font-bold"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      color: '#fff',
                      background: 'var(--grad-flame)',
                    }}>
                2026
              </span>
            </div>
            <p className="relative mt-1 text-[10px]" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              PSI flight data · NTRS reports
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
