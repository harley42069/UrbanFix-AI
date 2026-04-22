type ProgressBarProps = {
  value: number;
  label?: string;
};

export default function ProgressBar({ value, label }: ProgressBarProps) {
  const safeValue = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between text-sm text-slate-600">
        <span>{label || "Progress"}</span>
        <span className="font-semibold text-slate-900">{safeValue}%</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-brand-500 transition-all duration-500"
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}
