"use client";

import type { ReactNode } from "react";

import { ToastProvider } from "@/components/ui/Toast";

export default function AppProviders({ children }: { children: ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
