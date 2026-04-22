import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export default function Card({ children, className = "" }: CardProps) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur ${className}`}>
      {children}
    </section>
  );
}
