"use client";

import { useParams } from "next/navigation";

import AuthGate from "@/components/AuthGate";
import SignalementDetailView from "@/components/SignalementDetailView";

export default function SignalementDetailPage() {
  const params = useParams<{ id: string }>();

  return (
    <AuthGate>
      <section style={{ background: "linear-gradient(180deg, #fdf6ec 0%, #f5ede0 100%)" }}>
        <SignalementDetailView signalementId={params.id} autoRefresh />
      </section>
    </AuthGate>
  );
}
