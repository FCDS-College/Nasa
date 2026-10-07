interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "flame";
}

const variantStyles: Record<string, { bg: string; color: string; border: string }> = {
  default: {
    bg: "var(--border-subtle)",
    color: "var(--text-secondary)",
    border: "rgba(255,255,255,0.1)",
  },
  success: {
    bg: "rgba(16,185,129,0.1)",
    color: "var(--accent-success)",
    border: "rgba(16,185,129,0.2)",
  },
  warning: {
    bg: "rgba(245,158,11,0.1)",
    color: "var(--accent-warning)",
    border: "rgba(245,158,11,0.2)",
  },
  danger: {
    bg: "rgba(239,68,68,0.1)",
    color: "var(--accent-danger)",
    border: "rgba(239,68,68,0.2)",
  },
  flame: {
    bg: "rgba(59,130,246,0.1)",
    color: "var(--accent-flame)",
    border: "rgba(59,130,246,0.2)",
  },
};

export function Badge({ children, variant = "default" }: BadgeProps) {
  const style = variantStyles[variant] || variantStyles.default;
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide"
      style={{
        background: style.bg,
        color: style.color,
        border: `1px solid ${style.border}`,
        backdropFilter: 'blur(8px)',
      }}
    >
      {children}
    </span>
  );
}
