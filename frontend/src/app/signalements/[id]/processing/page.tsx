"use client";

import { useParams } from "next/navigation";

import AuthGate from "@/components/AuthGate";
import SignalementDetailView from "@/components/SignalementDetailView";

export default function SignalementProcessingPage() {
  const params = useParams<{ id: string }>();

  return (
    <AuthGate>
      <SignalementDetailView signalementId={params.id} autoRefresh />
    </AuthGate>
  );
}
