import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <section
      className={`rounded-xl border border-zinc-800 bg-zinc-950 p-5 ${className}`}
    >
      {children}
    </section>
  );
}
