import type { Scenario } from "@/lib/types";

import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";

type ScenarioCardProps = {
  scenario: Scenario;
};

function formatTnd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "TND",
    maximumFractionDigits: 0
  }).format(value);
}

function toneForType(type: string): "neutral" | "brand" {
  return type === "premium" ? "brand" : "neutral";
}

export default function ScenarioCard({ scenario }: ScenarioCardProps) {
  return (
    <Card className="overflow-hidden p-0">
      {scenario.image_url ? (
        <img
          src={scenario.image_url}
          alt={scenario.title}
          className="h-56 w-full cursor-pointer object-cover"
          onClick={() => window.open(scenario.image_url || "", "_blank")}
        />
      ) : (
        <div className="flex h-56 items-center justify-center bg-slate-100 text-sm text-slate-500">Scenario image unavailable</div>
      )}

      <div className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-semibold text-slate-900">{scenario.title}</h3>
          <Badge tone={toneForType(scenario.scenario_type)}>{formatTnd(scenario.cost_total)}</Badge>
        </div>
      </div>
    </Card>
  );
}
