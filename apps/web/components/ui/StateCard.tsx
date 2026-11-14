interface StateCardProps {
  title: string;
  message: string;
  status?: "success" | "warning" | "error" | "neutral";
}

const statusRgb: Record<string, string> = {
  success: "34,197,94",
  warning: "245,158,11",
  error: "239,68,68",
  neutral: "124,180,255",
};

export function StateCard({ title, message, status = "neutral" }: StateCardProps) {
  const rgb = statusRgb[status] || statusRgb.neutral;
  return (
    <section
      className="relative overflow-hidden rounded-xl p-5 pl-6"
      style={{
        background: `linear-gradient(100deg, rgba(${rgb},0.08), rgba(${rgb},0.02) 60%)`,
        border: `1px solid rgba(${rgb},0.2)`,
      }}
    >
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px]"
            style={{ background: `rgb(${rgb})`, boxShadow: `0 0 14px rgba(${rgb},0.8)` }} />
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
        {title}
      </h3>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        {message}
      </p>
    </section>
  );
}
