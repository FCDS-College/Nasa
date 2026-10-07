"use client";

import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api/client";
import { SystemHealth } from "@/lib/api/types";
import { Activity, Server, Database, Brain, Cpu, HardDrive, CheckCircle2, AlertTriangle, Layers, Gauge } from "lucide-react";

export default function StatusPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth);
    const timer = setInterval(() => fetchHealth().then(setHealth), 10000);
    return () => clearInterval(timer);
  }, []);

  if (!health) {
    return (
      <div className="p-8 flex items-center gap-3" style={{ color: 'var(--text-muted)' }}>
        <Gauge className="h-5 w-5 animate-spin" style={{ color: 'var(--accent-flame)' }} />
        Loading system status...
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
  };

  const summaryCards = [
    { label: "Global Status", value: health.status.toUpperCase(),
      color: health.status === 'ok' ? 'var(--accent-success)' : 'var(--accent-warning)' },
    { label: "API Version", value: health.version, color: 'var(--text-primary)' },
    { label: "Build ID", value: health.metrics.build_id || "—", color: 'var(--text-secondary)', mono: true },
    { label: "Release ID", value: health.metrics.release_id || "—", color: 'var(--text-secondary)', mono: true },
  ];

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
            style={{ color: 'var(--text-primary)' }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg"
               style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <Activity className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
          </div>
          System & Model Status
        </h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Real-time observability of provider availability, queues, and platform health.
        </p>
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
        Core Services
      </h2>

      {/* Services Grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Object.entries(health.services).map(([name, service], i) => {
          const Icon = icons[name] || Activity;
          const isUp = service.status === "up";
          return (
            <div
              key={name}
              className="rounded-2xl p-5 flex flex-col justify-between space-y-4 animate-fade-in-up"
              style={{
                animationDelay: `${200 + i * 60}ms`,
                background: 'var(--bg-card)',
                border: '1px solid var(--border-default)',
                boxShadow: 'var(--shadow-card)',
                transition: 'all var(--transition-default)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = isUp ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-default)';
              }}
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl"
                       style={{
                         background: isUp ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                         border: `1px solid ${isUp ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}`,
                       }}>
                    <Icon className="h-5 w-5"
                          style={{ color: isUp ? 'var(--accent-success)' : 'var(--accent-danger)' }} />
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
                <div className="flex items-center gap-1 text-xs font-semibold"
                     style={{ color: isUp ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                  {isUp ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                  {service.status.toUpperCase()}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs pt-3"
                   style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <div>
                  <span className="block mb-1" style={{ color: 'var(--text-dim)' }}>Latency</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {service.latency_ms ?? "—"} ms
                  </span>
                </div>
                <div>
                  <span className="block mb-1" style={{ color: 'var(--text-dim)' }}>Queue Depth</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {service.queue_depth ?? "—"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
