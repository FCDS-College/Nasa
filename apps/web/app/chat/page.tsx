"use client";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@/lib/context/ChatContext";
import {
  Send,
  Server,
  CheckCircle,
  AlertTriangle,
  Fingerprint,
  Sparkles,
  Flame,
  Beaker,
  Zap,
  Atom,
  BookOpen,
} from "lucide-react";
import Link from "next/link";

const QUICK_QUESTIONS = [
  {
    icon: Flame,
    label: "How does microgravity alter soot formation?",
    color: "var(--accent-flame)",
    bg: "rgba(59,130,246,0.08)",
    border: "rgba(59,130,246,0.15)",
  },
  {
    icon: Beaker,
    label: "What are the temperature profiles of BASS-II flames?",
    color: "var(--accent-ember)",
    bg: "rgba(251,146,60,0.08)",
    border: "rgba(251,146,60,0.15)",
  },
  {
    icon: Atom,
    label: "Cool flame behavior in droplet combustion?",
    color: "var(--accent-aurora)",
    bg: "rgba(6,182,212,0.08)",
    border: "rgba(6,182,212,0.15)",
  },
  {
    icon: Zap,
    label: "Explain radiative extinction limits in microgravity",
    color: "var(--accent-nebula)",
    bg: "rgba(129,140,248,0.08)",
    border: "rgba(129,140,248,0.15)",
  },
];

export default function ChatPage() {
  const { activeSession, sendMessage, isSending } = useChat();
  const [query, setQuery] = useState("");
  const turns = activeSession?.turns || [];

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSending) return;
    const currentQuery = query;
    setQuery("");
    await sendMessage(currentQuery);
  };

  const handleQuickQuestion = (text: string) => {
    setQuery(text);
  };

  return (
    <div className="flex flex-col w-full p-2 sm:p-4 md:p-5">
      <div
        className="flex flex-col w-full rounded-2xl"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-subtle)",
          backdropFilter: "blur(20px)",
          boxShadow: "var(--shadow-elevated)",
        }}
      >
        {/* Messages Area */}
        <div className="flex flex-col p-4 sm:p-6 lg:p-8 space-y-6 min-h-[50vh]">
          {turns.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center space-y-6 animate-fade-in-up py-10">
              {/* Hero Icon */}
              <div
                className="relative flex h-20 w-20 items-center justify-center rounded-3xl"
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid rgba(59,130,246,0.2)",
                  boxShadow: "0 0 40px rgba(59,130,246,0.1)",
                }}
              >
                <Sparkles className="h-10 w-10" style={{ color: "var(--accent-flame)" }} />
                <div
                  className="absolute -inset-1 rounded-3xl animate-pulse-glow"
                  style={{
                    background: "radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)",
                  }}
                />
              </div>

              {/* Welcome Text */}
              <div className="max-w-lg px-4 text-center">
                <h2
                  className="text-xl font-bold sm:text-2xl"
                  style={{ color: "var(--text-primary)" }}
                >
                  Ask a scientific research question
                </h2>
                <p
                  className="mt-3 text-sm leading-relaxed"
                  style={{ color: "var(--text-muted)" }}
                >
                  Answers are synthesized and verified using NASA combustion
                  literature & experimental data from the ISS.
                </p>
              </div>

              {/* Quick Questions Grid */}
              <div className="mt-2 grid w-full max-w-2xl grid-cols-1 gap-3 px-4 sm:grid-cols-2">
                {QUICK_QUESTIONS.map((q) => {
                  const Icon = q.icon;
                  return (
                    <button
                      key={q.label}
                      type="button"
                      onClick={() => handleQuickQuestion(q.label)}
                      className="group flex items-start gap-3 rounded-xl p-4 text-left text-sm"
                      style={{
                        background: q.bg,
                        border: `1px solid ${q.border}`,
                        color: "var(--text-secondary)",
                        transition: "all var(--transition-default)",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = q.color;
                        e.currentTarget.style.transform = "translateY(-1px)";
                        e.currentTarget.style.boxShadow = `0 4px 20px ${q.bg}`;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = q.border;
                        e.currentTarget.style.transform = "translateY(0)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    >
                      <Icon
                        className="mt-0.5 h-4 w-4 shrink-0"
                        style={{ color: q.color }}
                      />
                      <span>{q.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            turns.map((turn, i) => (
              <div
                key={turn.id || i}
                className="space-y-4 animate-fade-in-up"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                {/* User Message */}
                <div className="flex justify-end">
                  <div
                    className="max-w-[85%] rounded-2xl rounded-tr-md px-5 py-3.5 text-sm sm:max-w-[70%]"
                    style={{
                      background: "linear-gradient(135deg, rgba(59,130,246,0.15), rgba(96,165,250,0.1))",
                      border: "1px solid rgba(59,130,246,0.25)",
                      color: "var(--text-primary)",
                      boxShadow: "0 2px 16px rgba(59,130,246,0.08)",
                    }}
                  >
                    {turn.req.query}
                  </div>
                </div>

                {/* AI Response */}
                <div className="flex justify-start">
                  <div
                    className="max-w-[95%] rounded-2xl rounded-tl-md px-5 py-4 text-sm sm:max-w-[85%]"
                    style={{
                      background: "var(--border-subtle)",
                      border: "1px solid var(--border-default)",
                      color: "var(--text-secondary)",
                      boxShadow: "var(--shadow-card)",
                    }}
                  >
                    {turn.loading ? (
                      <div
                        className="flex items-center gap-3"
                        style={{ color: "var(--accent-flame)" }}
                      >
                        <div className="flex gap-1">
                          <div
                            className="h-2 w-2 rounded-full animate-bounce"
                            style={{ background: "var(--accent-flame)" }}
                          />
                          <div
                            className="h-2 w-2 rounded-full animate-bounce"
                            style={{
                              background: "var(--accent-flame)",
                              animationDelay: "0.15s",
                            }}
                          />
                          <div
                            className="h-2 w-2 rounded-full animate-bounce"
                            style={{
                              background: "var(--accent-flame)",
                              animationDelay: "0.3s",
                            }}
                          />
                        </div>
                        <span className="text-xs font-medium">
                          Synthesizing evidence...
                        </span>
                      </div>
                    ) : turn.res ? (
                      <div className="space-y-4">
                        {/* Answer */}
                        <div
                          className="leading-relaxed whitespace-pre-wrap"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {turn.res.answer}
                        </div>

                        {/* Evidence Chips */}
                        {turn.res.sources && turn.res.sources.length > 0 && (
                          <div
                            className="mt-4 pt-4 space-y-2"
                            style={{ borderTop: "1px solid var(--border-subtle)" }}
                          >
                            <h4
                              className="text-[10px] font-bold uppercase tracking-[0.15em]"
                              style={{ color: "var(--text-muted)" }}
                            >
                              <BookOpen
                                className="mr-1.5 inline h-3 w-3"
                                style={{ color: "var(--accent-flame)" }}
                              />
                              Grounding Evidence
                            </h4>
                            <div className="flex flex-wrap gap-2">
                              {turn.res.sources.map((src, idx) => (
                                <Link
                                  key={idx}
                                  href={`/evidence?id=${src.evidence_id}`}
                                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs"
                                  style={{
                                    background: "rgba(59,130,246,0.06)",
                                    border: "1px solid rgba(59,130,246,0.15)",
                                    color: "var(--accent-flame)",
                                    transition: "all var(--transition-fast)",
                                  }}
                                  onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = "rgba(59,130,246,0.35)";
                                    e.currentTarget.style.background = "rgba(59,130,246,0.1)";
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = "rgba(59,130,246,0.15)";
                                    e.currentTarget.style.background = "rgba(59,130,246,0.06)";
                                  }}
                                >
                                  <Fingerprint className="h-3.5 w-3.5 shrink-0" />
                                  <span className="font-semibold">[{idx + 1}]</span>
                                  <span className="max-w-[150px] truncate">
                                    {src.title}
                                  </span>
                                  <span style={{ color: "var(--text-dim)" }}>
                                    ({src.location})
                                  </span>
                                </Link>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Metadata Footer */}
                        <div
                          className="mt-4 flex flex-wrap items-center gap-3 pt-3 text-[10px] sm:gap-4"
                          style={{
                            borderTop: "1px solid var(--border-subtle)",
                            fontFamily: "var(--font-mono)",
                            color: "var(--text-dim)",
                          }}
                        >
                          <span className="flex items-center gap-1.5">
                            <Server className="h-3.5 w-3.5" />
                            {turn.res.model.provider}:{turn.res.model.name}
                          </span>
                          {turn.res.cache_hit && (
                            <span
                              className="flex items-center gap-1"
                              style={{ color: "var(--accent-aurora)" }}
                            >
                              <CheckCircle className="h-3.5 w-3.5" /> Cached
                            </span>
                          )}
                          {turn.res.memory_used && (
                            <span
                              className="flex items-center gap-1"
                              style={{ color: "var(--accent-plasma)" }}
                            >
                              <AlertTriangle className="h-3.5 w-3.5" /> Grounded
                            </span>
                          )}
                          <span className="hidden sm:inline">
                            Corpus: {turn.res.knowledge_version}
                          </span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input Bar */}
        <div
          className="shrink-0 p-3 sm:p-5"
          style={{
            background: "var(--bg-secondary)",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <form
            onSubmit={handleSend}
            className="relative mx-auto flex w-full max-w-4xl items-center"
          >
            <input
              id="chat-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a scientific research question..."
              disabled={isSending}
              className="w-full rounded-2xl py-4 pl-5 pr-14 text-sm disabled:opacity-60"
              style={{
                background: "var(--border-subtle)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
                fontFamily: "var(--font-sans)",
                transition: "border-color var(--transition-fast), box-shadow var(--transition-fast)",
                outline: "none",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "rgba(59,130,246,0.4)";
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(59,130,246,0.08)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "var(--border-default)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
            <button
              id="chat-send-btn"
              type="submit"
              disabled={!query.trim() || isSending}
              className="absolute bottom-2 right-2 top-2 flex aspect-square items-center justify-center rounded-xl active:scale-95 disabled:opacity-30"
              style={{
                background: "linear-gradient(135deg, var(--accent-flame), var(--accent-ember))",
                color: "#000",
                transition: "all var(--transition-fast)",
                boxShadow: "0 0 12px rgba(59,130,246,0.25)",
              }}
            >
              <Send className="ml-0.5 h-4 w-4" />
            </button>
          </form>
          <div
            className="mt-2.5 text-center text-[10px] font-medium sm:text-[11px]"
            style={{ color: "var(--text-dim)" }}
          >
            Scientific answers are grounded in NASA microgravity combustion publications.
          </div>
        </div>
      </div>
    </div>
  );
}
