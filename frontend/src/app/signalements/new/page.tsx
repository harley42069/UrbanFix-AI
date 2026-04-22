"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import AuthGate from "@/components/AuthGate";
import ImageUploader from "@/components/ImageUploader";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import { useToast } from "@/components/ui/Toast";
import { createSignalement } from "@/lib/api";
import type { InteractionMode, ProblemCategory } from "@/lib/types";
import { signalementFormSchema } from "@/lib/validators";

type FormState = {
  title: string;
  description: string;
  user_prompt: string;
  interaction_mode: InteractionMode;
  category: ProblemCategory;
  city: string;
  region: string;
  address: string;
  latitude: string;
  longitude: string;
  generate_audio: boolean;
  generate_video: boolean;
  generate_pdf: boolean;
};

const CATEGORY_OPTIONS: Array<{ value: ProblemCategory; label: string }> = [
  { value: "roads", label: "Routes" },
  { value: "sidewalk", label: "Trottoirs" },
  { value: "lighting", label: "Eclairage" },
  { value: "waste", label: "Dechets" },
  { value: "drainage", label: "Drainage" },
  { value: "other", label: "Autre" }
];

function initialState(): FormState {
  return {
    title: "",
    description: "",
    user_prompt: "",
    interaction_mode: "photo_and_prompt",
    category: "roads",
    city: "Tunis",
    region: "Tunis",
    address: "",
    latitude: "36.8065",
    longitude: "10.1815",
    generate_audio: true,
    generate_video: false,
    generate_pdf: true
  };
}

export default function NewSignalementPage() {
  const router = useRouter();
  const { pushToast } = useToast();
  const [form, setForm] = useState<FormState>(initialState);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const hasImage = Boolean(imageFile);

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErrors([]);

    const lat = form.latitude.trim() ? Number(form.latitude) : undefined;
    const lon = form.longitude.trim() ? Number(form.longitude) : undefined;

    const parsed = signalementFormSchema.safeParse({
      title: form.title,
      description: form.description || undefined,
      user_prompt: form.user_prompt || undefined,
      interaction_mode: form.interaction_mode,
      category: form.category,
      city: form.city,
      region: form.region,
      address: form.address || undefined,
      latitude: typeof lat === "number" && Number.isFinite(lat) ? lat : undefined,
      longitude: typeof lon === "number" && Number.isFinite(lon) ? lon : undefined,
      has_image: hasImage,
      generate_audio: form.generate_audio,
      generate_video: form.generate_video,
      generate_pdf: form.generate_pdf
    });

    if (!parsed.success) {
      const nextErrors = parsed.error.issues.map((issue) => issue.message);
      setErrors(nextErrors);
      return;
    }

    try {
      setLoading(true);
      const result = await createSignalement({
        title: form.title,
        description: form.description || undefined,
        user_prompt: form.user_prompt || undefined,
        interaction_mode: form.interaction_mode,
        category: form.category,
        latitude: typeof lat === "number" && Number.isFinite(lat) ? lat : undefined,
        longitude: typeof lon === "number" && Number.isFinite(lon) ? lon : undefined,
        city: form.city,
        region: form.region,
        address: form.address || undefined,
        generate_media: form.generate_audio || form.generate_video || form.generate_pdf,
        generate_audio: form.generate_audio,
        generate_video: form.generate_video,
        generate_pdf: form.generate_pdf,
        imageFile
      });

      pushToast({
        title: "Signalement cree",
        message: `Dossier #${result.signalementId} transmis au pipeline`,
        variant: "success"
      });
      router.push(`/signalements/${result.signalementId}`);
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Creation impossible";
      setErrors([message]);
      pushToast({ title: "Creation refusee", message, variant: "danger" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGate>
      <section className="space-y-6" style={{ background: "linear-gradient(180deg, #fdf6ec 0%, #f5ede0 100%)" }}>
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card className="space-y-5 rounded-3xl border-[#e8d5c0] bg-white">
            <SectionHeader title="Prompt et media" subtitle="Texte libre, photo et livrables additionnels" />

            <label className="space-y-2 block">
              <span className="text-sm font-medium text-[#1a1a1a]">Prompt / description operationnelle</span>
              <textarea
                value={form.user_prompt}
                onChange={(event) => updateField("user_prompt", event.target.value)}
                rows={5}
                className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-sm text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
                placeholder="Decrivez l'etat de la route, les travaux souhaites, les contraintes..."
              />
            </label>

            <ImageUploader file={imageFile} onChange={setImageFile} />

            <div className="grid gap-2 md:grid-cols-2">
              <label className="flex items-center justify-between rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3">
                <span className="text-sm text-[#8b6f5e]">Audio</span>
                <input type="checkbox" checked={form.generate_audio} onChange={(event) => updateField("generate_audio", event.target.checked)} />
              </label>
              <label className="flex items-center justify-between rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3">
                <span className="text-sm text-[#8b6f5e]">PDF</span>
                <input type="checkbox" checked={form.generate_pdf} onChange={(event) => updateField("generate_pdf", event.target.checked)} />
              </label>
            </div>
          </Card>

          <Card className="space-y-5 rounded-3xl border-[#e8d5c0] bg-white">
            <SectionHeader title="Informations du dossier" subtitle="Champs de base pour la collecte et le traitement" />

            <div className="grid gap-4 md:grid-cols-4">
              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-medium text-[#1a1a1a]">Titre</span>
                <input
                  value={form.title}
                  onChange={(event) => updateField("title", event.target.value)}
                  className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-sm text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
                  placeholder="Ex. Nid-de-poule rue Ibn Khaldoun"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-[#1a1a1a]">Ville</span>
                <input
                  value={form.city}
                  onChange={(event) => updateField("city", event.target.value)}
                  className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-sm text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-[#1a1a1a]">Region</span>
                <input
                  value={form.region}
                  onChange={(event) => updateField("region", event.target.value)}
                  className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-sm text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
                />
              </label>
            </div>

            <div className="space-y-3">
              <p className="text-sm font-semibold text-[#1a1a1a]">Categorie</p>
              <div className="flex flex-wrap gap-2">
                {CATEGORY_OPTIONS.map((option) => {
                  const active = form.category === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => updateField("category", option.value)}
                      className={[
                        "rounded-full border px-4 py-2 text-sm font-semibold transition",
                          active ? "border-[#c4623a] bg-[#fff7f1] text-[#c4623a]" : "border-[#e8d5c0] bg-white text-[#8b6f5e] hover:bg-[#fbf6ef]"
                      ].join(" ")}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <input type="hidden" name="latitude" value={form.latitude} readOnly />
            <input type="hidden" name="longitude" value={form.longitude} readOnly />
          </Card>

          {errors.length ? (
            <ul className="space-y-2 rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {errors.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full bg-[#c4623a] px-4 py-4 text-sm font-semibold text-white transition hover:bg-[#a94a2a] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Creation en cours..." : "Enregistrer et lancer le traitement"}
          </button>
        </form>
      </section>
    </AuthGate>
  );
}
