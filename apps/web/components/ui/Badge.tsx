interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "flame";
}

const variantStyles: Record<string, { rgb: string; color: string }> = {
  default: { rgb: "164,173,196", color: "var(--text-secondary)" },
  success: { rgb: "34,197,94", color: "var(--accent-success)" },
  warning: { rgb: "245,158,11", color: "var(--accent-warning)" },
  danger: { rgb: "239,68,68", color: "var(--accent-danger)" },
  flame: { rgb: "79,140,255", color: "var(--accent-ember)" },
};

export function Badge({ children, variant = "default" }: BadgeProps) {
  const style = variantStyles[variant] || variantStyles.default;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide"
      style={{
        background: `rgba(${style.rgb},0.1)`,
        color: style.color,
        border: `1px solid rgba(${style.rgb},0.25)`,
        boxShadow: `0 0 14px -6px rgba(${style.rgb},0.7)`,
      }}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full" style={{ background: style.color }} />
      {children}
    </span>
  );
}
