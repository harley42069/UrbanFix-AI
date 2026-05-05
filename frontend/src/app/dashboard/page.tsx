"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import AuthGate from "@/components/AuthGate";
import StatusBadge from "@/components/StatusBadge";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import { getCurrentUser, listSignalements } from "@/lib/api";
import type { AuthUser, SignalementSummary } from "@/lib/types";

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function countByStatus(items: SignalementSummary[], status: string): number {
  return items.filter((item) => item.status === status).length;
}

export default function DashboardPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [signalements, setSignalements] = useState<SignalementSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [profile, list] = await Promise.all([
          getCurrentUser(),
          listSignalements({ limit: 8, skip: 0 })
        ]);
        setUser(profile);
        setSignalements(list.items);
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "Unable to load the dashboard");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const stats = useMemo(() => {
    return {
      total: signalements.length,
      pending: countByStatus(signalements, "pending"),
      processing: countByStatus(signalements, "processing"),
      completed: countByStatus(signalements, "completed"),
      failed: countByStatus(signalements, "failed") + countByStatus(signalements, "rejected")
    };
  }, [signalements]);

  return (
    <AuthGate>
      <section className="space-y-6" style={{ background: "linear-gradient(180deg, #fdf6ec 0%, #f5ede0 100%)" }}>
        <Card className="space-y-4 rounded-3xl border-[#e8d5c0] bg-white">
          <SectionHeader
            title="Dashboard"
            subtitle={user ? `Hello ${user.full_name}, here is the latest recorded activity.` : "Consolidated view of reports and the AI pipeline."}
            actions={
              <>
                <Link href="/signalements/new" className="rounded-full bg-[#c4623a] px-4 py-2 text-sm font-semibold text-white hover:bg-[#a94a2a]">
                  New report
                </Link>
                <Link href="/signalements" className="rounded-full border border-[#e8d5c0] bg-white px-4 py-2 text-sm font-semibold text-[#1a5490] hover:bg-[#f0f7ff]">
                  Full list
                </Link>
              </>
            }
          />

          {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-3xl border border-[#e8d5c0] bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8b6f5e]">Total</p>
              <p className="mt-2 text-3xl font-black text-[#1a1a1a]">{loading ? "-" : stats.total}</p>
            </div>
            <div className="rounded-3xl border border-[#e8d5c0] bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8b6f5e]">Pending</p>
              <p className="mt-2 text-3xl font-black text-[#1a1a1a]">{loading ? "-" : stats.pending}</p>
            </div>
            <div className="rounded-3xl border border-[#e8d5c0] bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8b6f5e]">In progress</p>
              <p className="mt-2 text-3xl font-black text-[#1a1a1a]">{loading ? "-" : stats.processing}</p>
            </div>
            <div className="rounded-3xl border border-[#e8d5c0] bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8b6f5e]">Completed</p>
              <p className="mt-2 text-3xl font-black text-[#1a1a1a]">{loading ? "-" : stats.completed}</p>
            </div>
            <div className="rounded-3xl border border-[#e8d5c0] bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-[#8b6f5e]">Needs attention</p>
              <p className="mt-2 text-3xl font-black text-[#1a1a1a]">{loading ? "-" : stats.failed}</p>
            </div>
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <Card className="space-y-4 rounded-3xl border-[#e8d5c0] bg-white">
            <SectionHeader title="Recent reports" subtitle="The latest cases" />
            {signalements.length ? (
              <div className="space-y-3">
                {signalements.map((item) => (
                  <Link key={item.id} href={`/signalements/${item.id}`} className="block rounded-3xl border border-[#e8d5c0] bg-white p-4 transition hover:border-[#1a5490] hover:shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-[#1a1a1a]">{item.title || `Report #${item.id}`}</h3>
                        <p className="mt-1 text-sm text-[#8b6f5e]">{item.city || "Unknown city"} {item.region ? `· ${item.region}` : ""}</p>
                      </div>
                      <StatusBadge status={item.status} />
                    </div>
                    <div className="mt-3 grid gap-2 text-xs text-[#8b6f5e] sm:grid-cols-3">
                      <span>Stage: {item.current_stage || "queued"}</span>
                      <span>Progress: {item.progress || 0}%</span>
                      <span>Updated: {formatDate(item.updated_at)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : loading ? (
              <div className="space-y-3">
                <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
                <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
              </div>
            ) : (
              <p className="text-sm text-[#8b6f5e]">No reports available.</p>
            )}
          </Card>

          <Card className="space-y-4 rounded-3xl border-[#e8d5c0] bg-white">
            <SectionHeader title="Quick actions" subtitle="Service entry points" />
            <div className="grid gap-3">
              <Link href="/signalements/new" className="rounded-full bg-[#c4623a] px-4 py-4 text-sm font-semibold text-white hover:bg-[#a94a2a]">
                Create a report
              </Link>
              <Link href="/signalements" className="rounded-full border border-[#e8d5c0] bg-white px-4 py-4 text-sm font-semibold text-[#1a5490] hover:bg-[#f0f7ff]">
                Browse database
              </Link>
              <Link href="/login" className="rounded-full border border-[#e8d5c0] bg-white px-4 py-4 text-sm font-semibold text-[#1a5490] hover:bg-[#f0f7ff]">
                Switch account
              </Link>
            </div>

            <div className="rounded-3xl border border-[#e8d5c0] bg-[#fbf6ef] p-4 text-sm text-[#8b6f5e]">
              <p className="font-semibold text-[#1a1a1a]">Operational tip</p>
              <p className="mt-2">Use the reports list to check status, then open the details to track pipeline progress and download outputs.</p>
            </div>
          </Card>
        </div>
      </section>
    </AuthGate>
  );
}
