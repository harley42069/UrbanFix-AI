import type { Scenario } from "@/lib/types";
import Badge from "@/components/ui/Badge";

type ScenarioGalleryProps = {
  scenarios: Scenario[];
};

function toTitle(value: string): string {
  if (value === "basic") return "Basic";
  if (value === "smart") return "Smart";
  return "Premium";
}

export default function ScenarioGallery({ scenarios }: ScenarioGalleryProps) {
  if (!scenarios.length) {
    return <p className="text-sm text-slate-500">Aucun scenario disponible.</p>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {scenarios.map((scenario) => {
        return (
          <article key={scenario.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            {scenario.image_url ? (
              <img src={scenario.image_url} alt={scenario.title} className="h-48 w-full object-cover" />
            ) : (
              <div className="flex h-48 items-center justify-center bg-slate-100 text-sm text-slate-500">No scenario image</div>
            )}

            <div className="space-y-3 p-4">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-base font-semibold text-slate-900">{scenario.title}</h3>
                <Badge tone="brand">{toTitle(scenario.scenario_type)}</Badge>
              </div>

              <p className="text-sm text-slate-600">{scenario.description}</p>

              <details className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Prompt used
                </summary>
                <p className="mt-2 break-words text-xs text-slate-700">{scenario.prompt_used || "No prompt"}</p>
              </details>

              <p className="text-sm font-semibold text-slate-900">
                {new Intl.NumberFormat("fr-FR").format(Math.round(scenario.cost_total))} TND
              </p>
            </div>
          </article>
        );
      })}
    </div>
  );
}
