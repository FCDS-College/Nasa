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
  accentColor = "var(--accent-ember)",
}: MetricCardProps) {
  return (
    <section className="panel panel-hover relative overflow-hidden rounded-xl p-5">
      <span aria-hidden="true" className="absolute inset-x-0 top-0 h-[2px]"
            style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)` }} />
      <p className="text-[10.5px] font-semibold uppercase tracking-[0.18em]"
         style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        {label}
      </p>
      <p className="mt-2 text-3xl font-bold tracking-tight"
         style={{ color: accentColor, fontFamily: 'var(--font-mono)', textShadow: '0 0 24px rgba(79,140,255,0.35)' }}>
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
