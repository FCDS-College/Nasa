import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
}

export function Card({ children, className = "", hover = false, glow = false }: CardProps) {
  return (
    <section
      className={`rounded-2xl ${hover ? "transition-all duration-200 hover:border-blue-500/30 hover:shadow-lg cursor-pointer" : ""} ${className}`}
      style={{
        background: 'var(--bg-card)',
        backdropFilter: 'blur(24px) saturate(1.4)',
        border: '1px solid var(--border-default)',
        boxShadow: glow ? 'var(--shadow-glow-sm)' : 'var(--shadow-card)',
        padding: '20px',
        transition: 'all var(--transition-default)',
      }}
    >
      {children}
    </section>
  );
}
