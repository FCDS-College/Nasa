"use client";

import { useEffect, useState } from "react";
import { fetchExperiments } from "@/lib/api/client";
import { ExperimentRecord } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { FlaskConical, Beaker, RefreshCw, AlertTriangle } from "lucide-react";
import Link from "next/link";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<"all" | "microgravity" | "terrestrial">("all");

  const loadExperiments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchExperiments();
      setExperiments(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load experiment records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExperiments();
  }, []);

  const filtered = experiments.filter((e) => {
    if (selectedTab === "microgravity") return e.gravity_regime.toLowerCase().includes("micro");
    if (selectedTab === "terrestrial") return !e.gravity_regime.toLowerCase().includes("micro");
    return true;
  });

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <FlaskConical className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            Experiment Explorer
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Compare microgravity (BASS-II, FLEX, SAFFIRE, SPICE) and terrestrial flight test matrices with full evidence lineages.
          </p>
        </div>

        <button
          onClick={loadExperiments}
          className="flex h-9 w-9 items-center justify-center rounded-xl p-2 cursor-pointer transition-all"
          style={{
            background: 'var(--border-subtle)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
          }}
          title="Refresh experiments"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 animate-fade-in-up" style={{ animationDelay: '80ms' }}>
        {[
          { id: "all", label: "All Experiments" },
          { id: "microgravity", label: "Microgravity (0G)" },
          { id: "terrestrial", label: "Terrestrial (1G)" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSelectedTab(tab.id as any)}
            className="rounded-lg px-4 py-2 text-xs font-medium cursor-pointer transition-all"
            style={{
              background: selectedTab === tab.id ? 'rgba(59,130,246,0.1)' : 'transparent',
              border: selectedTab === tab.id ? '1px solid rgba(59,130,246,0.25)' : '1px solid transparent',
              color: selectedTab === tab.id ? 'var(--accent-flame)' : 'var(--text-dim)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <FlaskConical className="h-8 w-8 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          <p className="mt-3 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
            Querying experimental condition records from Flame API...
          </p>
        </div>
      ) : error ? (
        <div className="rounded-2xl p-6 text-center space-y-3"
             style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--accent-danger)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto" />
          <h3 className="font-bold text-base">Error Loading Experiments</h3>
          <p className="text-xs">{error}</p>
          <button
            onClick={loadExperiments}
            className="rounded-lg px-4 py-1.5 text-xs font-semibold cursor-pointer"
            style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--accent-danger)', border: '1px solid rgba(239,68,68,0.3)' }}
          >
            Retry
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl p-12 text-center space-y-4 animate-fade-in-up"
             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl mx-auto"
               style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid var(--border-subtle)' }}>
            <Beaker className="h-7 w-7" style={{ color: 'var(--accent-flame)', opacity: 0.8 }} />
          </div>
          <div>
            <h3 className="font-bold text-white text-base">No Matching Experiments</h3>
            <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
              No flight test records matching the active filter were returned by the API.
            </p>
          </div>
          <Link
            href="/search?q=flame&type=experiment"
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold"
            style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-flame)', border: '1px solid rgba(59,130,246,0.25)' }}
          >
            Search Experiment Corpus →
          </Link>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          {filtered.map((exp, i) => (
            <div
              key={exp.experiment_id}
              className="rounded-2xl p-5 space-y-4 animate-fade-in-up"
              style={{
                animationDelay: `${150 + i * 80}ms`,
                background: 'var(--bg-card)',
                border: '1px solid var(--border-default)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-base font-bold text-white">
                    {exp.name}
                  </h3>
                  <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <span>{exp.platform}</span>
                    <span>•</span>
                    <span className="capitalize">{exp.gravity_regime}</span>
                  </div>
                </div>
                <Badge variant={exp.gravity_regime.includes("micro") ? "success" : "default"}>
                  {exp.gravity_regime.toUpperCase()}
                </Badge>
              </div>

              <div className="rounded-xl p-3" style={{ background: 'var(--border-subtle)' }}>
                <span className="text-[10px] font-bold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-dim)' }}>
                  Material / Fuel
                </span>
                <p className="text-xs text-white">
                  {exp.objective}
                </p>
              </div>

              {exp.conditions.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider block" style={{ color: 'var(--text-dim)' }}>
                    Test Conditions ({exp.conditions.length})
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {exp.conditions.slice(0, 6).map((c, idx) => (
                      <div key={idx} className="rounded-lg p-2" style={{ background: 'var(--border-subtle)' }}>
                        <span className="text-[10px] block truncate" style={{ color: 'var(--text-muted)' }}>
                          {c.variable}
                        </span>
                        <span className="text-xs font-mono font-bold text-white">
                          {c.value} {c.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
