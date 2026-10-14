"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { ChatRequest, ChatResponse } from "@/lib/api/types";
import { submitChat } from "@/lib/api/client";

export interface ChatTurn {
  id: string;
  req: ChatRequest;
  res?: ChatResponse;
  loading?: boolean;
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: ChatTurn[];
}

interface ChatContextType {
  sessions: ChatSession[];
  activeSessionId: string | null;
  activeSession: ChatSession | null;
  createNewSession: () => string;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => void;
  clearAllSessions: () => void;
  renameSession: (id: string, newTitle: string) => void;
  sendMessage: (query: string) => Promise<void>;
  isSending: boolean;
  isSidebarOpen: boolean;
  setIsSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
  toggleSidebar: () => void;
  closeSidebar: () => void;
  openSidebar: () => void;
}

const STORAGE_KEY_SESSIONS = "flame_chat_sessions_v1";
const STORAGE_KEY_ACTIVE = "flame_active_session_id_v1";

const INITIAL_SESSIONS: ChatSession[] = [
  {
    id: "sess-soot-microgravity",
    title: "Microgravity Soot Formation",
    createdAt: Date.now() - 1000 * 60 * 45, // 45 mins ago
    updatedAt: Date.now() - 1000 * 60 * 45,
    turns: [
      {
        id: "turn-1",
        req: { query: "How does microgravity alter soot formation?" },
        res: {
          request_id: "req_101",
          answer:
            "In microgravity, buoyancy-induced convection is nearly eliminated. This causes flames to become spherical and soot residence times to increase significantly, altering soot formation pathways and radiative heat loss. The CLD Flame experiment observed larger primary soot particles compared to normal gravity (1g) conditions.",
          sources: [
            {
              evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T5",
              document_id: "doc_991",
              title: "Soot Formation in Microgravity",
              location: "p. 4, §2.1",
              url: "https://ntrs.nasa.gov/",
            },
          ],
          memory_used: true,
          cache_hit: false,
          model: { provider: "vllm", name: "Llama-3-8B-Instruct", version: "v1.0" },
          knowledge_version: "2026-10-03",
          warnings: [],
        },
        timestamp: Date.now() - 1000 * 60 * 45,
      },
    ],
  },
  {
    id: "sess-bass-ii-temp",
    title: "BASS-II Temperature Profiles",
    createdAt: Date.now() - 1000 * 60 * 60 * 18, // 18 hours ago
    updatedAt: Date.now() - 1000 * 60 * 60 * 18,
    turns: [
      {
        id: "turn-2",
        req: { query: "What are the temperature profiles of BASS-II flames?" },
        res: {
          request_id: "req_102",
          answer:
            "BASS-II (Burning and Suppression of Solids - II) tests aboard the ISS demonstrated peak flame temperatures ranging from 1150 K to 1420 K depending on forced oxidizer flow velocity. Due to reduced heat losses via natural convection, radiative extinction thresholds shifted toward lower oxygen indices.",
          sources: [
            {
              evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T6",
              document_id: "doc_992",
              title: "BASS-II Flame Quenching & Temperature Diagnostics",
              location: "Section 3.4, Table 2",
              url: "https://ntrs.nasa.gov/",
            },
          ],
          memory_used: true,
          cache_hit: true,
          model: { provider: "vllm", name: "Llama-3-8B-Instruct", version: "v1.0" },
          knowledge_version: "2026-10-03",
          warnings: [],
        },
        timestamp: Date.now() - 1000 * 60 * 60 * 18,
      },
    ],
  },
  {
    id: "sess-droplet-combustion",
    title: "Droplet Extinction Dynamics",
    createdAt: Date.now() - 1000 * 60 * 60 * 48, // 2 days ago
    updatedAt: Date.now() - 1000 * 60 * 60 * 48,
    turns: [
      {
        id: "turn-3",
        req: { query: "How does cool flame behavior manifest in isolated droplet combustion?" },
        res: {
          request_id: "req_103",
          answer:
            "In the FLEX (Flame Extinction Experiment) investigation, large alkane droplets exhibited a two-stage burning process. After conventional radiative extinction of the hot flame (~1700 K), a low-temperature 'cool flame' (~700-900 K) continued burning quasi-steadily without visible chemiluminescence until final extinction.",
          sources: [
            {
              evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T7",
              document_id: "doc_993",
              title: "FLEX Droplet Combustion & Cool Flame Regime",
              location: "p. 12, Fig. 5",
              url: "https://ntrs.nasa.gov/",
            },
          ],
          memory_used: true,
          cache_hit: false,
          model: { provider: "vllm", name: "Llama-3-8B-Instruct", version: "v1.0" },
          knowledge_version: "2026-10-03",
          warnings: [],
        },
        timestamp: Date.now() - 1000 * 60 * 60 * 48,
      },
    ],
  },
];

function getInitialSessions(): ChatSession[] {
  if (typeof window !== "undefined") {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY_SESSIONS);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.error("Failed to load chat sessions from localStorage:", e);
    }
  }
  return INITIAL_SESSIONS;
}

function getInitialActiveSessionId(initialSessions: ChatSession[]): string | null {
  if (typeof window !== "undefined") {
    try {
      const storedActive = window.localStorage.getItem(STORAGE_KEY_ACTIVE);
      if (storedActive && initialSessions.some((s) => s.id === storedActive)) {
        return storedActive;
      }
    } catch (e) {
      console.error("Failed to load active session ID from localStorage:", e);
    }
  }
  return initialSessions[0]?.id || null;
}

function getInitialSidebarOpen(): boolean {
  if (typeof window !== "undefined") {
    return window.innerWidth >= 1024;
  }
  return false;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>(getInitialSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() =>
    getInitialActiveSessionId(sessions)
  );
  const [isSending, setIsSending] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(getInitialSidebarOpen);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleResize = () => {
      // Responsive layout adjustments if needed
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => !prev);
  }, []);

  const closeSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const openSidebar = useCallback(() => {
    setIsSidebarOpen(true);
  }, []);

  // Save changes to LocalStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions));
      if (activeSessionId) {
        window.localStorage.setItem(STORAGE_KEY_ACTIVE, activeSessionId);
      } else {
        window.localStorage.removeItem(STORAGE_KEY_ACTIVE);
      }
    } catch (e) {
      console.error("Failed to persist chat sessions:", e);
    }
  }, [sessions, activeSessionId]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  const createNewSession = useCallback((): string => {
    const newId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const newSession: ChatSession = {
      id: newId,
      title: "New Research Chat",
      createdAt: Date.now(),
      updatedAt: Date.now(),
      turns: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
    return newId;
  }, []);

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  }, []);

  const deleteSession = useCallback((id: string) => {
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== id);
      return filtered;
    });
    setActiveSessionId((curr) => {
      if (curr === id) {
        return null;
      }
      return curr;
    });
  }, []);

  const clearAllSessions = useCallback(() => {
    setSessions([]);
    setActiveSessionId(null);
  }, []);

  const renameSession = useCallback((id: string, newTitle: string) => {
    if (!newTitle.trim()) return;
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle.trim(), updatedAt: Date.now() } : s))
    );
  }, []);

  const sendMessage = useCallback(
    async (query: string) => {
      const cleanQuery = query.trim();
      if (!cleanQuery) return;

      let currentId = activeSessionId;
      let session = sessions.find((s) => s.id === currentId);

      // If no active session or current session is null, create one automatically
      if (!session) {
        currentId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
        session = {
          id: currentId,
          title: cleanQuery.slice(0, 36) + (cleanQuery.length > 36 ? "..." : ""),
          createdAt: Date.now(),
          updatedAt: Date.now(),
          turns: [],
        };
        setSessions((prev) => [session!, ...prev]);
        setActiveSessionId(currentId);
      }

      const turnId = `turn_${Date.now()}`;
      const req: ChatRequest = {
        query: cleanQuery,
        conversation_id: currentId || undefined,
      };

      const newTurn: ChatTurn = {
        id: turnId,
        req,
        loading: true,
        timestamp: Date.now(),
      };

      // Auto update title if this is the first turn and title is still "New Research Chat"
      const shouldUpdateTitle = session.turns.length === 0 || session.title === "New Research Chat";
      const generatedTitle = shouldUpdateTitle
        ? cleanQuery.slice(0, 36) + (cleanQuery.length > 36 ? "..." : "")
        : session.title;

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === currentId) {
            return {
              ...s,
              title: generatedTitle,
              updatedAt: Date.now(),
              turns: [...s.turns, newTurn],
            };
          }
          return s;
        })
      );

      setIsSending(true);

      try {
        const res = await submitChat(req);
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id === currentId) {
              return {
                ...s,
                updatedAt: Date.now(),
                turns: s.turns.map((t) => (t.id === turnId ? { ...t, res, loading: false } : t)),
              };
            }
            return s;
          })
        );
      } catch (err) {
        console.error("Chat submission error:", err);
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id === currentId) {
              return {
                ...s,
                turns: s.turns.map((t) =>
                  t.id === turnId
                    ? {
                        ...t,
                        loading: false,
                        res: {
                          request_id: "err_" + Date.now(),
                          answer:
                            "An error occurred while connecting to the scientific inference service. Please verify server status.",
                          sources: [],
                          memory_used: false,
                          cache_hit: false,
                          model: { provider: "error", name: "offline", version: "0.0" },
                          knowledge_version: "2026-10-03",
                          warnings: ["Inference timeout or connection failed"],
                        },
                      }
                    : t
                ),
              };
            }
            return s;
          })
        );
      } finally {
        setIsSending(false);
      }
    },
    [activeSessionId, sessions]
  );

  return (
    <ChatContext.Provider
      value={{
        sessions,
        activeSessionId,
        activeSession,
        createNewSession,
        selectSession,
        deleteSession,
        clearAllSessions,
        renameSession,
        sendMessage,
        isSending,
        isSidebarOpen,
        setIsSidebarOpen,
        toggleSidebar,
        closeSidebar,
        openSidebar,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
}
