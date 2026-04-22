import { z } from "zod";

export const uploadSchema = z.object({
  title: z.string().max(200).optional(),
  user_prompt: z.string().max(2000).optional(),
  category: z.enum(["roads", "sidewalk", "lighting", "waste", "drainage", "other"]),
  has_image: z.boolean().optional().default(false),
  latitude: z.number().min(-90).max(90).optional(),
  longitude: z.number().min(-180).max(180).optional(),
  generate_audio: z.boolean().optional().default(false),
  generate_video: z.boolean().optional().default(false),
  generate_pdf: z.boolean().optional().default(false),
  generate_media: z.boolean().optional().default(false)
}).superRefine((values, ctx) => {
  const prompt = values.user_prompt?.trim() || "";

  if (!values.has_image && !prompt) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Ajoutez un prompt ou une image pour continuer",
      path: ["user_prompt"]
    });
  }
});

export const signalementFormSchema = z.object({
  title: z.string().min(5, "Le titre doit contenir au moins 5 caracteres").max(200),
  description: z.string().max(500).optional(),
  user_prompt: z.string().max(2000).optional(),
  interaction_mode: z.enum(["photo_only", "photo_and_prompt", "prompt_only"]),
  category: z.enum(["roads", "sidewalk", "lighting", "waste", "drainage", "other"]),
  city: z.string().min(2, "La ville est requise").max(100),
  region: z.string().min(2, "La region est requise").max(100),
  address: z.string().max(500).optional(),
  latitude: z.number().min(-90).max(90).optional(),
  longitude: z.number().min(-180).max(180).optional(),
  has_image: z.boolean().default(false),
  generate_audio: z.boolean().default(false),
  generate_video: z.boolean().default(false),
  generate_pdf: z.boolean().default(false)
}).superRefine((values, ctx) => {
  const prompt = values.user_prompt?.trim() || "";
  const needsImage = values.interaction_mode === "photo_only" || values.interaction_mode === "photo_and_prompt";
  const needsPrompt = values.interaction_mode === "photo_and_prompt" || values.interaction_mode === "prompt_only";

  if (needsImage && !values.has_image) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Ajoutez une image pour ce mode d'interaction",
      path: ["has_image"]
    });
  }

  if (needsPrompt && !prompt) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Ajoutez un prompt pour ce mode d'interaction",
      path: ["user_prompt"]
    });
  }
});

export type UploadSchema = z.infer<typeof uploadSchema>;
export type SignalementFormSchema = z.infer<typeof signalementFormSchema>;
