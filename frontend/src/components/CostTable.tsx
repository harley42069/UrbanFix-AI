import type { Scenario } from "@/lib/types";

type CostTableProps = {
  scenarios: Scenario[];
};

function formatTnd(value: number): string {
  if (!Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "TND",
    maximumFractionDigits: 0
  }).format(value);
}

export default function CostTable({ scenarios }: CostTableProps) {
  if (!scenarios.length) {
    return <p className="text-sm text-slate-500">Aucun cout disponible.</p>;
  }

  return (
    <div className="space-y-4">
      {scenarios.map((scenario) => (
        <div key={scenario.id} className="overflow-hidden rounded-xl border border-slate-200">
          <div className="flex items-center justify-between bg-slate-50 px-4 py-3">
            <p className="font-semibold text-slate-900">{scenario.title}</p>
            <p className="text-sm font-semibold text-slate-700">{formatTnd(scenario.cost_total)}</p>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white text-left text-slate-600">
                <tr>
                  <th className="px-4 py-2">Poste</th>
                  <th className="px-4 py-2">Quantite</th>
                  <th className="px-4 py-2">Unite</th>
                  <th className="px-4 py-2">Prix Unit.</th>
                  <th className="px-4 py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {scenario.cost_breakdown.length ? (
                  scenario.cost_breakdown.map((item) => (
                    <tr key={`${scenario.id}-${item.category}`} className="border-t border-slate-100">
                      <td className="px-4 py-2 text-slate-800">{item.description}</td>
                      <td className="px-4 py-2 text-slate-700">{item.quantity}</td>
                      <td className="px-4 py-2 text-slate-700">{item.unit}</td>
                      <td className="px-4 py-2 text-slate-700">{formatTnd(item.unit_price)}</td>
                      <td className="px-4 py-2 font-medium text-slate-900">{formatTnd(item.total)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-sm text-slate-500">
                      Aucun detail de cout.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
