"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useMemo, useState } from "react";

type ToastVariant = "info" | "success" | "warning" | "danger";

type ToastInput = {
  title: string;
  message?: string;
  variant?: ToastVariant;
};

type ToastItem = ToastInput & {
  id: string;
};

type ToastContextValue = {
  pushToast: (toast: ToastInput) => void;
  clearToasts: () => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

function toneClasses(variant: ToastVariant): string {
  if (variant === "success") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (variant === "warning") return "border-amber-200 bg-amber-50 text-amber-900";
  if (variant === "danger") return "border-rose-200 bg-rose-50 text-rose-900";
  return "border-slate-200 bg-white text-slate-900";
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const value = useMemo<ToastContextValue>(() => {
    return {
      pushToast(toast: ToastInput) {
        const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        setToasts((current) => [...current, { id, ...toast, variant: toast.variant || "info" }]);
        window.setTimeout(() => {
          setToasts((current) => current.filter((item) => item.id !== id));
        }, 4200);
      },
      clearToasts() {
        setToasts([]);
      }
    };
  }, []);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-[min(92vw,24rem)] flex-col gap-3">
        {toasts.map((toast) => (
          <div key={toast.id} className={`pointer-events-auto rounded-2xl border p-4 shadow-lg ${toneClasses(toast.variant || "info")}`}>
            <p className="text-sm font-semibold">{toast.title}</p>
            {toast.message ? <p className="mt-1 text-sm text-current/80">{toast.message}</p> : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return context;
}
