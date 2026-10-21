"use client";

import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api/client";
import { SystemHealth } from "@/lib/api/types";
import { Activity, Server, Database, Brain, Cpu, HardDrive, Layers, Gauge, RefreshCw } from "lucide-react";

export default function StatusPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const timer = setInterval(() => {
      fetchHealth().then(setHealth);
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  if (!health && loading) {
    return (
      <div className="p-8 flex items-center gap-3" style={{ color: 'var(--text-muted)' }}>
        <Gauge className="h-5 w-5 animate-spin" style={{ color: 'var(--accent-flame)' }} />
        <span>Loading system diagnostics...</span>
      </div>
    );
  }

  const icons: Record<string, React.ElementType> = {
    api: Server,
    database: Database,
    vector_index: Layers,
    object_storage: HardDrive,
    cache: Cpu,
    cv_model: Brain,
    llm: Brain,
    aura: Activity,
  };

  const summaryCards = [
    {
      label: "Global Status",
      value: (health?.status || "UNKNOWN").toUpperCase(),
      color: health?.status === 'ok' ? 'var(--accent-success)' : health?.status === 'degraded' ? 'var(--accent-warning)' : 'var(--accent-danger)',
    },
    { label: "API Version", value: health?.version || "unknown", color: 'var(--text-primary)' },
    { label: "Build ID", value: health?.metrics.build_id || "—", color: 'var(--text-secondary)', mono: true },
    { label: "Release ID", value: health?.metrics.release_id || "—", color: 'var(--text-secondary)', mono: true },
  ];

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <Activity className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            System & Subsystem Diagnostics
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Live observability of Flame API health, vector database, object storage, and upstream services.
          </p>
        </div>

        <button
          onClick={checkHealth}
          className="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold cursor-pointer transition-all"
          style={{
            background: 'var(--border-subtle)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-secondary)',
          }}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Health
        </button>
      </div>

      {/* Summary Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in-up" style={{ animationDelay: '80ms' }}>
        {summaryCards.map((card, i) => (
          <div key={i} className="rounded-2xl p-4"
               style={{
                 background: 'var(--bg-card)',
                 border: '1px solid var(--border-default)',
                 boxShadow: 'var(--shadow-card)',
               }}>
            <div className="text-[10px] font-bold uppercase tracking-[0.15em] mb-2"
                 style={{ color: 'var(--text-dim)' }}>
              {card.label}
            </div>
            <div className="text-xl font-bold"
                 style={{
                   color: card.color,
                   fontFamily: card.mono ? 'var(--font-mono)' : 'var(--font-sans)',
                   fontSize: card.mono ? '14px' : undefined,
                 }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Services Header */}
      <h2 className="text-lg font-bold mt-8 pb-3 flex items-center gap-2"
          style={{
            color: 'var(--text-primary)',
            borderBottom: '1px solid var(--border-subtle)',
          }}>
        <Server className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
        Subsystem Dependencies
      </h2>

      {/* Services Grid */}
      {health && health.services ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Object.entries(health.services).map(([name, service], i) => {
            const Icon = icons[name] || Activity;
            const isUp = service.status === "up";
            const isDisabled = service.status === "disabled";
            return (
              <div
                key={name}
                className="rounded-2xl p-5 flex flex-col justify-between space-y-4 animate-fade-in-up"
                style={{
                  animationDelay: `${200 + i * 60}ms`,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl"
                         style={{
                           background: isUp ? 'rgba(16,185,129,0.08)' : isDisabled ? 'var(--border-subtle)' : 'rgba(239,68,68,0.08)',
                           border: `1px solid ${isUp ? 'rgba(16,185,129,0.15)' : isDisabled ? 'var(--border-subtle)' : 'rgba(239,68,68,0.15)'}`,
                         }}>
                      <Icon className="h-5 w-5"
                            style={{ color: isUp ? 'var(--accent-success)' : isDisabled ? 'var(--text-dim)' : 'var(--accent-danger)' }} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold uppercase tracking-wider"
                          style={{ color: 'var(--text-primary)' }}>
                        {name.replace("_", " ")}
                      </h3>
                      {service.version && (
                        <div className="text-[10px] mt-0.5"
                             style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                          {service.version}
                        </div>
                      )}
                    </div>
                  </div>

                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                        style={{
                          background: isUp ? 'rgba(16,185,129,0.1)' : isDisabled ? 'var(--border-subtle)' : 'rgba(239,68,68,0.1)',
                          color: isUp ? 'var(--accent-success)' : isDisabled ? 'var(--text-dim)' : 'var(--accent-danger)',
                        }}>
                    {service.status}
                  </span>
                </div>

                <div className="space-y-1.5 pt-2 text-xs" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                  {service.latency_ms != null && (
                    <div className="flex justify-between text-[11px]">
                      <span style={{ color: 'var(--text-muted)' }}>Latency</span>
                      <span className="font-mono text-white">{service.latency_ms.toFixed(1)} ms</span>
                    </div>
                  )}
                  {service.message && (
                    <p className="text-[11px] leading-tight mt-1" style={{ color: 'var(--text-dim)' }}>
                      {service.message}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
