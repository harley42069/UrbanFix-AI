import Badge from "@/components/ui/Badge";
import type { PipelineStatus } from "@/lib/types";

type StatusBadgeProps = {
  status: PipelineStatus | string | undefined;
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const value = (status || "pending").toString().toLowerCase();

  if (value === "completed") return <Badge tone="success">Termine</Badge>;
  if (value === "processing") return <Badge tone="warning">En cours</Badge>;
  if (value === "failed" || value === "rejected") return <Badge tone="danger">Bloque</Badge>;
  return <Badge tone="neutral">En attente</Badge>;
}
