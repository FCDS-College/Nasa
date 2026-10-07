interface StateCardProps {
  title: string;
  message: string;
  status?: "success" | "warning" | "error" | "neutral";
}

const statusStyles: Record<string, { bg: string; border: string; icon: string }> = {
  success: {
    bg: "rgba(16,185,129,0.04)",
    border: "rgba(16,185,129,0.15)",
    icon: "var(--accent-success)",
  },
  warning: {
    bg: "rgba(245,158,11,0.04)",
    border: "rgba(245,158,11,0.15)",
    icon: "var(--accent-warning)",
  },
  error: {
    bg: "rgba(239,68,68,0.04)",
    border: "rgba(239,68,68,0.15)",
    icon: "var(--accent-danger)",
  },
  neutral: {
    bg: "var(--border-subtle)",
    border: "var(--border-default)",
    icon: "var(--text-muted)",
  },
};

export function StateCard({ title, message, status = "neutral" }: StateCardProps) {
  const style = statusStyles[status] || statusStyles.neutral;
  return (
    <section
      className="rounded-xl p-5"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
      }}
    >
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
        {title}
      </h3>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        {message}
      </p>
    </section>
  );
}
