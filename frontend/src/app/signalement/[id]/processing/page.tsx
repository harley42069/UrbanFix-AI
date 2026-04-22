import { redirect } from "next/navigation";

export default function LegacyProcessingPage({ params }: { params: { id: string } }) {
  redirect(`/signalements/${params.id}`);
}
