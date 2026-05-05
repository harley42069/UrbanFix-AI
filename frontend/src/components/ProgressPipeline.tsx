import type { PipelineStatus } from "@/lib/types";

import Badge from "@/components/ui/Badge";

type ProgressPipelineProps = {
  status: PipelineStatus | string;
  progress: number;
  currentStage?: string | null;
  lastError?: { stage?: string; message?: string } | null;
};

export default function ProgressPipeline({ status, progress, currentStage, lastError }: ProgressPipelineProps) {
  const safeProgress = Math.max(0, Math.min(100, Number.isFinite(progress) ? progress : 0));

  return (
    <div className="space-y-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">AI pipeline</p>
        </div>
        <Badge tone={status === "completed" ? "success" : status === "failed" ? "danger" : status === "processing" ? "warning" : "neutral"}>
          {String(status).toUpperCase()}
        </Badge>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
          <span>{safeProgress}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-[#1f6fb2] transition-all duration-500" style={{ width: `${safeProgress}%` }} />
        </div>
      </div>
    </div>
  );
}
