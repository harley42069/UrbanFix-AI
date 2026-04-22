type StepperProps = {
  steps: Array<{ id: string; label: string }>;
  currentIndex: number;
};

export default function Stepper({ steps, currentIndex }: StepperProps) {
  return (
    <ol className="grid gap-3 sm:grid-cols-4" aria-label="Progression formulaire">
      {steps.map((step, index) => {
        const isDone = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <li
            key={step.id}
            className={[
              "rounded-xl border p-3 text-sm transition",
              isCurrent ? "border-cyan-400 bg-cyan-50" : "border-slate-200 bg-white",
              isDone ? "ring-1 ring-emerald-300" : ""
            ].join(" ")}
          >
            <p className="font-semibold text-slate-900">Step {index + 1}</p>
            <p className="text-slate-600">{step.label}</p>
          </li>
        );
      })}
    </ol>
  );
}
