import { redirect } from "next/navigation";

export default function LegacySignalementDetailPage({ params }: { params: { id: string } }) {
  redirect(`/signalements/${params.id}`);
}
