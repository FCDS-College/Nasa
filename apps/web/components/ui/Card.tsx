import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
}

/** A console panel: gradient glass, viewfinder corner brackets that extend on hover, and a glowing top hairline. */
export function Card({ children, className = "", glow = false }: CardProps) {
  return (
    <section
      className={`hud-card rounded-2xl ${className}`}
      style={{
        boxShadow: glow ? 'var(--shadow-glow-md), var(--shadow-card)' : undefined,
        padding: '22px',
      }}
    >
      <span aria-hidden="true" className="hud-sheen" />
      {children}
    </section>
  );
}
