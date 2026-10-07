"use client";

import { useEffect, useState } from "react";
import { fetchExperiments } from "@/lib/api/client";
import { ExperimentRecord } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { FlaskConical, GitMerge, FileText, Globe2, Activity, Microscope } from "lucide-react";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);

  useEffect(() => {
    fetchExperiments().then(setExperiments);
  }, []);

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
            style={{ color: 'var(--text-primary)' }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg"
               style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <FlaskConical className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
          </div>
          Experiment Explorer
        </h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Compare microgravity and terrestrial flame experiments side-by-side with full evidence graphs.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 animate-fade-in-up" style={{ animationDelay: '80ms' }}>
        {["All Experiments", "Microgravity", "Terrestrial"].map((tab, i) => (
          <button
            key={tab}
            className="rounded-lg px-4 py-2 text-sm font-medium"
            style={{
              background: i === 0 ? 'rgba(59,130,246,0.1)' : 'transparent',
              border: i === 0 ? '1px solid rgba(59,130,246,0.2)' : '1px solid transparent',
              color: i === 0 ? 'var(--accent-flame)' : 'var(--text-dim)',
              transition: 'all var(--transition-fast)',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Experiments Grid */}
      <div className="grid gap-5 xl:grid-cols-2">
        {experiments.map((exp, i) => (
          <div
            key={exp.experiment_id}
            className="rounded-2xl p-5 space-y-4 animate-fade-in-up"
            style={{
              animationDelay: `${150 + i * 80}ms`,
              background: 'var(--bg-card)',
              border: '1px solid var(--border-default)',
              boxShadow: 'var(--shadow-card)',
              transition: 'all var(--transition-default)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(59,130,246,0.2)';
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = 'var(--shadow-glow-sm)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-default)';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'var(--shadow-card)';
            }}
          >
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  {exp.name}
                </h2>
                <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{exp.objective}</div>
              </div>
              <Badge variant={exp.gravity_regime === "microgravity" ? "flame" : "default"}>
                {exp.gravity_regime === "microgravity"
                  ? <Globe2 className="h-3 w-3 mr-1" />
                  : <Activity className="h-3 w-3 mr-1" />}
                {exp.gravity_regime.toUpperCase()}
              </Badge>
            </div>

            <div className="text-sm py-2 pl-3"
                 style={{
                   borderLeft: '2px solid rgba(59,130,246,0.3)',
                   color: 'var(--text-muted)',
                 }}>
              Platform:{" "}
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                {exp.platform}
              </span>
            </div>

            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] mb-3"
                  style={{ color: 'var(--accent-flame)', opacity: 0.8 }}>
                <Microscope className="h-3 w-3 inline mr-1" />
                Controlled Conditions
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {exp.conditions.map((cond, idx) => (
                  <div key={idx} className="rounded-lg p-2.5"
                       style={{
                         background: 'var(--border-subtle)',
                         border: '1px solid var(--border-subtle)',
                       }}>
                    <div className="text-[10px] uppercase"
                         style={{ color: 'var(--text-dim)' }}>{cond.variable}</div>
                    <div className="text-sm mt-0.5"
                         style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {cond.value} {cond.unit}
                    </div>
                    <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-dim)' }}>{cond.method}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-4 pt-4"
                 style={{ borderTop: '1px solid var(--border-subtle)' }}>
              <button className="text-xs font-medium flex items-center gap-1.5"
                      style={{ color: 'var(--accent-flame)', transition: 'opacity var(--transition-fast)' }}>
                <GitMerge className="h-4 w-4" /> Compare with terrestrial
              </button>
              <button className="text-xs flex items-center gap-1.5"
                      style={{ color: 'var(--text-muted)', transition: 'color var(--transition-fast)' }}>
                <FileText className="h-4 w-4" /> 14 Linked Docs
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
