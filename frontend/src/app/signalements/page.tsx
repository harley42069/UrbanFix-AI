"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import AuthGate from "@/components/AuthGate";
import StatusBadge from "@/components/StatusBadge";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import { listSignalements } from "@/lib/api";
import type { PipelineStatus, SignalementSummary } from "@/lib/types";

const STATUSES: Array<{ label: string; value: PipelineStatus | "all" }> = [
  { label: "Tous", value: "all" },
  { label: "En attente", value: "pending" },
  { label: "En cours", value: "processing" },
  { label: "Termines", value: "completed" },
  { label: "Echoues", value: "failed" },
  { label: "Rejetes", value: "rejected" }
];

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function SignalementsPage() {
  const [signalements, setSignalements] = useState<SignalementSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<PipelineStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await listSignalements({
          limit: 10,
          skip: (page - 1) * 10,
          status: status === "all" ? undefined : status
        });
        setSignalements(response.items);
        setPages(response.pagination?.pages || 1);
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "Erreur de chargement de la liste");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [page, status]);

  const filteredSignalements = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return signalements;
    return signalements.filter((item) => {
      const haystack = [item.title, item.description, item.city, item.region, item.current_stage].join(" ").toLowerCase();
      return haystack.includes(query);
    });
  }, [search, signalements]);

  return (
    <AuthGate>
      <section className="space-y-6" style={{ background: "linear-gradient(180deg, #fdf6ec 0%, #f5ede0 100%)" }}>
        <Card className="space-y-4 rounded-3xl border-[#e8d5c0] bg-white">
          <SectionHeader
            title="Signalements"
            subtitle="Filtrer, retrouver et ouvrir les dossiers en un seul endroit"
            actions={
              <Link href="/signalements/new" className="rounded-full bg-[#c4623a] px-4 py-2 text-sm font-semibold text-white hover:bg-[#a94a2a]">
                Nouveau dossier
              </Link>
            }
          />

          {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

          <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Rechercher par titre, ville, region ou etape"
              className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-sm text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
            />
            <div className="flex flex-wrap gap-2">
              {STATUSES.map((item) => {
                const active = item.value === status;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => {
                      setStatus(item.value);
                      setPage(1);
                    }}
                    className={[
                      "rounded-full border px-4 py-2 text-sm font-semibold transition",
                      active ? "border-[#1a5490] bg-[#f0f7ff] text-[#1a5490]" : "border-[#e8d5c0] bg-white text-[#8b6f5e] hover:bg-[#fbf6ef]"
                    ].join(" ")}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>
        </Card>

        <Card className="space-y-4 rounded-3xl border-[#e8d5c0] bg-white">
          {loading ? (
            <div className="space-y-3">
              <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
              <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
            </div>
          ) : filteredSignalements.length ? (
            <div className="space-y-3">
              {filteredSignalements.map((item) => (
                <Link key={item.id} href={`/signalements/${item.id}`} className="block rounded-3xl border border-[#e8d5c0] bg-white p-4 transition hover:border-[#1a5490] hover:shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="text-base font-semibold text-[#1a1a1a]">{item.title || `Signalement #${item.id}`}</h3>
                      <p className="mt-1 text-sm text-[#8b6f5e]">{item.description || "Aucune description"}</p>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>

                  <div className="mt-4 grid gap-2 text-xs text-[#8b6f5e] sm:grid-cols-4">
                    <span>Ville: {item.city || "-"}</span>
                    <span>Region: {item.region || "-"}</span>
                    <span>Etape: {item.current_stage || "queued"}</span>
                    <span>Maj: {formatDate(item.updated_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Aucun resultat ne correspond aux filtres courants.</p>
          )}

          <div className="flex items-center justify-between border-t border-[#e8d5c0] pt-4">
            <p className="text-sm text-[#8b6f5e]">
              Page {page} sur {pages}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                className="rounded-full border border-[#e8d5c0] bg-white px-4 py-2 text-sm font-semibold text-[#1a5490] hover:bg-[#f0f7ff] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Precedent
              </button>
              <button
                type="button"
                disabled={page >= pages}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-full bg-[#c4623a] px-4 py-2 text-sm font-semibold text-white hover:bg-[#a94a2a] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Suivant
              </button>
            </div>
          </div>
        </Card>
      </section>
    </AuthGate>
  );
}
