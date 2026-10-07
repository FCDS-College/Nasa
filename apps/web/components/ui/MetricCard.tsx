interface MetricCardProps {
  label: string;
  value: string | number;
  description?: string;
  accentColor?: string;
}

export function MetricCard({
  label,
  value,
  description,
  accentColor = "var(--accent-flame)",
}: MetricCardProps) {
  return (
    <section
      className="rounded-xl p-5"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-default)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em]"
         style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <p className="mt-2 text-3xl font-bold" style={{ color: accentColor }}>
        {value}
      </p>
      {description && (
        <p className="mt-1.5 text-xs" style={{ color: 'var(--text-dim)' }}>
          {description}
        </p>
      )}
    </section>
  );
}
