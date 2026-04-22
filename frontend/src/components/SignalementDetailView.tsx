"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import AudioPlayer from "@/components/AudioPlayer";
import ProgressPipeline from "@/components/ProgressPipeline";
import ScenarioCard from "@/components/ScenarioCard";
import StatusBadge from "@/components/StatusBadge";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import { getProcessStatus } from "@/lib/api";
import type { ProcessStatusResponse, Scenario } from "@/lib/types";

type SignalementDetailViewProps = {
  signalementId: string;
  autoRefresh?: boolean;
};

function formatTnd(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "TND",
    maximumFractionDigits: 0
  }).format(value);
}

export default function SignalementDetailView({ signalementId, autoRefresh = true }: SignalementDetailViewProps) {
  const [data, setData] = useState<ProcessStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await getProcessStatus(signalementId);
      setData(response);
      setError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Erreur de chargement du signalement");
    } finally {
      setLoading(false);
    }
  }, [signalementId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!autoRefresh || data?.status === "completed" || data?.status === "failed") {
      return;
    }

    const timer = window.setInterval(load, 3500);
    return () => window.clearInterval(timer);
  }, [autoRefresh, data?.status, load]);

  const scenarios: Scenario[] = useMemo(() => data?.scenarios || data?.results?.scenarios || [], [data?.results?.scenarios, data?.scenarios]);
  const detections = data?.results?.detections || data?.detections || null;
  const media = data?.media || data?.results?.media || data?.outputs;
  const detectionCount = Array.isArray((detections as { detections?: unknown[] } | null)?.detections)
    ? (detections as { detections?: unknown[] }).detections?.length || 0
    : Array.isArray(detections)
      ? detections.length
      : 0;

  if (loading) {
    return <div className="h-72 animate-pulse rounded-3xl bg-white shadow-sm" />;
  }

  if (error) {
    return <Card className="border-rose-200 bg-rose-50 text-rose-800">{error}</Card>;
  }

  if (!data) {
    return <Card>Aucune donnee disponible.</Card>;
  }

  return (
    <section className="space-y-6">
      <Card className="space-y-6">
        <SectionHeader
          title={`Signalement #${signalementId}`}
          subtitle="Interface municipale pour suivre la detection, les scenarios et les livrables IA"
          actions={
            <>
              <StatusBadge status={data.status} />
              <Badge tone="brand">{data.language.toUpperCase()}</Badge>
            </>
          }
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Statut</p>
            <p className="mt-2 text-lg font-semibold text-slate-900">{data.status}</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Etape</p>
            <p className="mt-2 text-lg font-semibold text-slate-900">{data.current_stage || data.stage || "queued"}</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Scenario</p>
            <p className="mt-2 text-lg font-semibold text-slate-900">{scenarios.length}</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Detections</p>
            <p className="mt-2 text-lg font-semibold text-slate-900">{detectionCount}</p>
          </div>
        </div>
      </Card>

      <ProgressPipeline
        status={data.status}
        progress={data.progress}
        currentStage={data.current_stage || data.stage}
        lastError={data.last_error || null}
      />

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="space-y-6">
          <Card className="space-y-4">
            <SectionHeader title="Scenarios de rehabilitation" />
            <div className="grid gap-4 lg:grid-cols-2">
              {scenarios.length ? scenarios.map((scenario) => <ScenarioCard key={scenario.id} scenario={scenario} />) : <p className="text-sm text-slate-500">Aucun scenario disponible pour le moment.</p>}
            </div>
          </Card>

          <Card className="space-y-4">
            <SectionHeader title="Elements techniques" subtitle="Sorties detectees et informations de pipeline" />
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">Sorties detection</p>
                <div className="mt-3 space-y-2 text-sm text-slate-600">
                  <p>Total: {typeof (detections as { total_problems?: number } | null)?.total_problems === "number" ? (detections as { total_problems?: number }).total_problems : detectionCount}</p>
                  <p>Langue: {data.language}</p>
                  <p>Temps de traitement: {data.processing_time_seconds ? `${Math.round(data.processing_time_seconds)} s` : "n/a"}</p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">Resume cout</p>
                <div className="mt-3 space-y-2 text-sm text-slate-600">
                  <p>Scenarios: {scenarios.length}</p>
                  <p>Cout moyen: {formatTnd(scenarios.reduce((sum, scenario) => sum + scenario.cost_total, 0) / (scenarios.length || 1))}</p>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="space-y-4">
            <SectionHeader title="Medias generes" subtitle="Visuels, audio et documents exportes" />
            {media?.scenario_image ? (
              <a href={media.scenario_image} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <img src={media.scenario_image} alt="Image scenario" className="h-48 w-full object-cover" />
                <div className="px-4 py-3 text-sm font-medium text-slate-700">Ouvrir l'image scenario</div>
              </a>
            ) : null}
            <AudioPlayer src={media?.audio_url || null} title="Narration audio" />
            {media?.video_url ? (
              <a href={media.video_url} target="_blank" rel="noreferrer" className="inline-flex w-full items-center justify-center rounded-2xl bg-[#1f6fb2] px-4 py-3 text-sm font-semibold text-white hover:bg-[#185b90]">
                Ouvrir la video
              </a>
            ) : null}
            {media?.pdf_url ? (
              <a href={media.pdf_url} target="_blank" rel="noreferrer" className="inline-flex w-full items-center justify-center rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50">
                Telecharger le rapport PDF
              </a>
            ) : null}
          </Card>

          <Card className="space-y-4">
            <SectionHeader title="Actions" subtitle="Acces rapide au suivi et aux listes" />
            <div className="grid gap-3">
              <button type="button" onClick={load} className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50">
                Rafraichir
              </button>
              <Link href="/signalements" className="rounded-2xl bg-[#1f6fb2] px-4 py-3 text-center text-sm font-semibold text-white hover:bg-[#185b90]">
                Voir tous les signalements
              </Link>
              <Link href="/signalements/new" className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-center text-sm font-semibold text-slate-800 hover:bg-slate-50">
                Nouveau signalement
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}
