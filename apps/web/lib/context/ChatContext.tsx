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

const INITIAL_SESSIONS: ChatSession[] = [];

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Auto-detect desktop screen to keep sidebar open by default on desktop, closed on mobile
  useEffect(() => {
    if (typeof window !== "undefined") {
      setIsSidebarOpen(window.innerWidth >= 1024);
      const handleResize = () => {
        if (window.innerWidth < 1024) {
          // Keep it closed on mobile resize
        }
      };
      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }
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

  // Initialize from LocalStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_SESSIONS);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSessions(parsed);
          const storedActive = localStorage.getItem(STORAGE_KEY_ACTIVE);
          if (storedActive && parsed.some((s) => s.id === storedActive)) {
            setActiveSessionId(storedActive);
          } else {
            setActiveSessionId(parsed[0].id);
          }
          setIsHydrated(true);
          return;
        }
      }
    } catch (e) {
      console.error("Failed to load chat sessions from localStorage:", e);
    }

    // Default seed
    setSessions(INITIAL_SESSIONS);
    setActiveSessionId(INITIAL_SESSIONS[0].id);
    setIsHydrated(true);
  }, []);

  // Save changes to LocalStorage
  useEffect(() => {
    if (!isHydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions));
      if (activeSessionId) {
        localStorage.setItem(STORAGE_KEY_ACTIVE, activeSessionId);
      } else {
        localStorage.removeItem(STORAGE_KEY_ACTIVE);
      }
    } catch (e) {
      console.error("Failed to persist chat sessions:", e);
    }
  }, [sessions, activeSessionId, isHydrated]);

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
