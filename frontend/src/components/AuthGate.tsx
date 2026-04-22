"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { hasStoredAuthSession } from "@/lib/auth";

type AuthGateProps = {
  children: ReactNode;
  redirectTo?: string;
};

export default function AuthGate({ children, redirectTo = "/login" }: AuthGateProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!hasStoredAuthSession()) {
      router.replace(`${redirectTo}?next=${encodeURIComponent(window.location.pathname)}`);
      return;
    }

    setReady(true);
  }, [redirectTo, router]);

  if (!ready) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="h-6 w-40 animate-pulse rounded-full bg-slate-200" />
        <div className="mt-4 h-28 animate-pulse rounded-2xl bg-slate-100" />
      </div>
    );
  }

  return <>{children}</>;
}
