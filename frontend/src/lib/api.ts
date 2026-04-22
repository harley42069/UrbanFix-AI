import type {
  ApiMeta,
  AuthSession,
  AuthUser,
  CostItem,
  ListSignalementsParams,
  LegacyScenarioItem,
  MediaUrls,
  PaginationMeta,
  PipelineStatus,
  ProcessStatusResponse,
  ProblemCategory,
  RawProcessStatusResponse,
  Scenario,
  ScenarioAction,
  ScenarioType,
  SignalementCreateInput,
  SignalementSummary,
  SupportedLanguage,
  InteractionMode,
  UploadAndProcessResult,
  UploadFormValues,
  ApiResponseEnvelope
} from "@/lib/types";
import {
  clearAuthSession,
  getAccessToken,
  getStoredAuthSession,
  saveAuthSession,
  type StoredAuthSession
} from "@/lib/auth";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") || "";
const FIXED_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

function getApiBaseUrlOrThrow(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL est manquant. Configurez le frontend puis relancez-le.");
  }
  return raw.replace(/\/+$/, "");
}

function getDiagnosticMessage(error: unknown, url: string): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return `Le serveur ne repond pas (${url}). Verifiez que le backend est lance.`;
  }

  const baseMsg = error instanceof Error ? error.message : "Unknown error";
  const isNetworkError = error instanceof TypeError && baseMsg.includes("Failed to fetch");

  if (isNetworkError) {
    if (!API_BASE_URL) {
      return "NEXT_PUBLIC_API_BASE_URL est manquant. Configurez le frontend puis relancez-le.";
    }

    const localhostApi = API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1");
    const pageHost = typeof window !== "undefined" ? window.location.hostname : "";
    const pageIsLocal = pageHost === "localhost" || pageHost === "127.0.0.1";
    const lanHint = localhostApi && pageHost && !pageIsLocal
      ? " Vous utilisez probablement le frontend depuis un autre appareil. Remplacez NEXT_PUBLIC_API_BASE_URL par l'IP locale du PC (ex: http://192.168.x.x:8000) et demarrez le backend avec --host 0.0.0.0."
      : "";

    return `Impossible de contacter le backend (${url}). Verifiez que le backend est lance.${lanHint}`;
  }

  return baseMsg;
}

function getRequestErrorMessage(response: Response, url: string): string {
  return `Echec requete API (${response.status}) sur ${url}`;
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs = 25000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function getAccessTokenForRequest(): string | null {
  return getAccessToken() || FIXED_TOKEN || null;
}

function buildHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {};
  const token = getAccessTokenForRequest();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return { ...headers, ...extra };
}

async function requestApiEnvelope<T>(
  url: string,
  init: RequestInit,
  timeoutMs = 25000
): Promise<{ data: T; meta: ApiMeta | null }> {
  try {
    const response = await fetchWithTimeout(url, init, timeoutMs);
    const rawText = await response.text();
    let payload: ApiResponseEnvelope<T> | null = null;

    if (rawText) {
      try {
        payload = JSON.parse(rawText) as ApiResponseEnvelope<T>;
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      const backendMessage = payload?.error?.message;

      if (response.status === 401) {
        throw new Error("Authentification requise. Connectez-vous ou configurez un token.");
      }
      if (response.status === 403) {
        throw new Error("Acces refuse pour cette operation.");
      }
      if (response.status >= 500) {
        throw new Error("Le backend a retourne une erreur interne.");
      }

      throw new Error(backendMessage || getRequestErrorMessage(response, url));
    }

    if (!payload || !payload.success) {
      throw new Error("Reponse API invalide ou incomplete.");
    }

    if (payload.data === null || payload.data === undefined) {
      throw new Error("Reponse API invalide ou incomplete.");
    }

    return {
      data: payload.data,
      meta: payload.meta || null
    };
  } catch (error) {
    console.error("[api] requestApiEnvelope error", { url, error });

    if (error instanceof Error) {
      throw error;
    }

    throw new Error(getDiagnosticMessage(error, url));
  }
}

async function requestApiData<T>(url: string, init: RequestInit, timeoutMs = 25000): Promise<T> {
  const result = await requestApiEnvelope<T>(url, init, timeoutMs);
  return result.data;
}

function resolveInteractionMode(hasImage: boolean, hasPrompt: boolean): InteractionMode {
  if (!hasImage && hasPrompt) return "prompt_only";
  if (hasImage && hasPrompt) return "photo_and_prompt";
  return "photo_only";
}

function resolveUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

function asLanguage(value: unknown): SupportedLanguage {
  return value === "en" ? "en" : "fr";
}

function asScenarioType(value: unknown): ScenarioType {
  const raw = String(value || "smart").toLowerCase();
  if (raw === "basic" || raw === "minimal" || raw === "conservative") return "basic";
  if (raw === "premium" || raw === "innovative") return "premium";
  return "smart";
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeCostBreakdown(input: unknown): CostItem[] {
  if (Array.isArray(input)) {
    return input
      .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
      .map((item) => ({
        category: String(item.category || "travaux"),
        description: String(item.description || item.category || "Travaux"),
        quantity: asNumber(item.quantity, asNumber(item.count, 1)),
        unit: String(item.unit || "unit"),
        unit_price: asNumber(item.unit_price, asNumber(item.unit_cost, 0)),
        total: asNumber(item.total, asNumber(item.cost, 0))
      }));
  }

  if (input && typeof input === "object") {
    return Object.entries(input as Record<string, unknown>)
      .filter(([, value]) => !!value && typeof value === "object")
      .map(([category, value]) => {
        const row = value as Record<string, unknown>;
        return {
          category,
          description: String(row.description || category.replaceAll("_", " ")),
          quantity: asNumber(row.quantity, asNumber(row.count, 1)),
          unit: String(row.unit || "unit"),
          unit_price: asNumber(row.unit_price, asNumber(row.unit_cost, 0)),
          total: asNumber(row.total, asNumber(row.cost, 0))
        };
      });
  }

  return [];
}

function normalizeActions(input: unknown): ScenarioAction[] {
  if (!Array.isArray(input)) return [];
  return input
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => ({
      label: String(item.label || item.title || "Action"),
      details: item.details ? String(item.details) : null
    }));
}

function buildNarrationFallback(type: ScenarioType, costTotal: number, lang: SupportedLanguage): string {
  if (lang === "en") {
    return `This ${type} scenario will improve the area and will cost about ${new Intl.NumberFormat("en-US").format(Math.round(costTotal))} TND.`;
  }
  return `Ce scenario ${type} ameliorera la zone et le cout des travaux sera d'environ ${new Intl.NumberFormat("fr-FR").format(Math.round(costTotal))} TND.`;
}

function normalizeScenario(entry: LegacyScenarioItem, index: number, lang: SupportedLanguage): Scenario {
  const scenarioType = asScenarioType(entry.scenario_type || entry.type);
  const costBreakdown = normalizeCostBreakdown(entry.cost_breakdown);
  const costTotal = asNumber(entry.cost_total, costBreakdown.reduce((sum, item) => sum + item.total, 0));

  return {
    id: String(entry.id || `scn-${index + 1}`),
    scenario_type: scenarioType,
    title: String(entry.title || `${scenarioType.toUpperCase()} scenario`),
    description: String(entry.description || ""),
    prompt_used: String(entry.prompt_used || entry.prompt || ""),
    image_url: resolveUrl((entry.image_url as string | undefined) || (entry.image_path as string | undefined)),
    narration_text: String(entry.narration_text || buildNarrationFallback(scenarioType, costTotal, lang)),
    actions: normalizeActions(entry.actions),
    cost_breakdown: costBreakdown,
    cost_total: costTotal,
    language: asLanguage(entry.language || lang)
  };
}

function normalizeScenarios(
  rawScenarios: RawProcessStatusResponse["scenarios"] | RawProcessStatusResponse["results"],
  lang: SupportedLanguage
): Scenario[] {
  const fromResults = rawScenarios && typeof rawScenarios === "object" && "scenarios" in rawScenarios
    ? (rawScenarios.scenarios as RawProcessStatusResponse["scenarios"])
    : undefined;

  const source = fromResults ?? (rawScenarios as RawProcessStatusResponse["scenarios"]);

  if (Array.isArray(source)) {
    return source.map((item, index) => normalizeScenario(item as LegacyScenarioItem, index, lang));
  }

  if (source && typeof source === "object" && Array.isArray((source as { items?: unknown[] }).items)) {
    return (source as { items: LegacyScenarioItem[] }).items.map((item, index) => normalizeScenario(item, index, lang));
  }

  return [];
}

function normalizeMedia(raw: RawProcessStatusResponse): MediaUrls {
  const resultMedia = raw.results?.media;
  const outputs = raw.outputs;

  return {
    annotated_image: resolveUrl((resultMedia?.annotated_image || outputs?.annotated_image || null) as string | null),
    scenario_image: resolveUrl((resultMedia?.scenario_image || outputs?.scenario_image || null) as string | null),
    audio_url: resolveUrl((resultMedia?.audio_url || resultMedia?.audio || raw.audio_url || outputs?.audio || null) as string | null),
    video_url: resolveUrl((resultMedia?.video_url || resultMedia?.video || raw.video_url || outputs?.video || null) as string | null),
    pdf_url: resolveUrl((resultMedia?.pdf_url || resultMedia?.pdf || raw.pdf_url || outputs?.pdf || null) as string | null)
  };
}

function normalizeStatus(data: RawProcessStatusResponse): ProcessStatusResponse {
  const language = asLanguage(data.language ?? data.results?.language ?? "fr");
  const scenarios = normalizeScenarios(data.results ?? data.scenarios ?? null, language);
  const media = normalizeMedia(data);

  return {
    signalement_id: data.signalement_id,
    status: (data.status || "pending") as PipelineStatus,
    progress: typeof data.progress === "number" ? data.progress : 0,
    current_stage: data.current_stage || data.stage || "queued",
    stage: data.stage,
    language,
    last_error: data.last_error || null,
    completed_at: data.completed_at || null,
    processing_time_seconds: data.processing_time_seconds ?? null,
    detections: data.results?.detections || data.detections || null,
    scenarios,
    estimations: data.estimations || null,
    outputs: media,
    media,
    audio_url: media.audio_url,
    video_url: media.video_url,
    pdf_url: media.pdf_url,
    ws_channel: data.ws_channel,
    results: {
      language,
      detections: data.results?.detections || data.detections || null,
      scenarios,
      media
    }
  };
}

export type LoginCredentials = {
  username: string;
  password: string;
};

export async function login(credentials: LoginCredentials): Promise<AuthSession> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = `${baseUrl}/api/v1/auth/login`;
  const body = new URLSearchParams();
  body.set("username", credentials.username);
  body.set("password", credentials.password);

  return requestApiData<AuthSession>(url, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/x-www-form-urlencoded" }),
    body
  });
}

export async function getCurrentUser(): Promise<AuthUser> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = `${baseUrl}/api/v1/auth/me`;
  return requestApiData<AuthUser>(url, {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });
}

export async function logout(): Promise<void> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = `${baseUrl}/api/v1/auth/logout`;
  try {
    await requestApiData<Record<string, unknown>>(url, {
      method: "POST",
      headers: buildHeaders()
    });
  } finally {
    clearAuthSession();
  }
}

export async function listSignalements(params: ListSignalementsParams = {}): Promise<{ items: SignalementSummary[]; pagination: PaginationMeta | null }> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = new URL(`${baseUrl}/api/v1/signalements/`);

  if (typeof params.skip === "number") url.searchParams.set("skip", String(params.skip));
  if (typeof params.limit === "number") url.searchParams.set("limit", String(params.limit));
  if (params.status) url.searchParams.set("status", params.status);
  if (params.city) url.searchParams.set("city", params.city);
  if (params.region) url.searchParams.set("region", params.region);

  const { data, meta } = await requestApiEnvelope<SignalementSummary[]>(url.toString(), {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });

  return {
    items: data,
    pagination: meta?.pagination || null
  };
}

export async function getSignalement(id: string | number): Promise<SignalementSummary> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = `${baseUrl}/api/v1/signalements/${id}`;
  return requestApiData<SignalementSummary>(url, {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });
}

export type TriggerSignalementPayload = {
  user_prompt?: string;
  generate_media?: boolean;
  generate_audio?: boolean;
  generate_video?: boolean;
  generate_pdf?: boolean;
  interaction_mode?: InteractionMode;
  category?: ProblemCategory;
};

export async function triggerSignalement(
  id: string | number,
  payload: TriggerSignalementPayload = {}
): Promise<Record<string, unknown>> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = `${baseUrl}/api/v1/process/${id}`;
  return requestApiData<Record<string, unknown>>(url, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload)
  });
}

export type SubmitSignalementOptions = SignalementCreateInput & {
  imageFile?: File | null;
};

export async function createSignalement(options: SubmitSignalementOptions): Promise<UploadAndProcessResult> {
  const prompt = options.user_prompt?.trim() || "";
  const hasImage = Boolean(options.imageFile);
  const interactionMode = options.interaction_mode || resolveInteractionMode(hasImage, Boolean(prompt));
  const category = options.category;
  const title = options.title.trim();

  if (interactionMode === "prompt_only") {
    const baseUrl = getApiBaseUrlOrThrow();
    const url = `${baseUrl}/api/v1/signalements/prompt`;
    const data = await requestApiData<{ signalement_id: number }>(url, {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        title,
        description: options.description,
        interaction_mode: interactionMode,
        category,
        user_prompt: prompt,
        latitude: options.latitude,
        longitude: options.longitude,
        generate_audio: Boolean(options.generate_audio),
        generate_video: Boolean(options.generate_video),
        generate_pdf: Boolean(options.generate_pdf)
      })
    });

    return { signalementId: data.signalement_id };
  }

  if (!options.imageFile) {
    throw new Error("Ajoutez une image pour creer ce signalement.");
  }

  const baseUrl = getApiBaseUrlOrThrow();
  const createUrl = `${baseUrl}/api/v1/signalements/`;
  const formData = new FormData();
  formData.append("title", title);
  formData.append("description", options.description || "");
  formData.append("latitude", String(typeof options.latitude === "number" ? options.latitude : 36.8065));
  formData.append("longitude", String(typeof options.longitude === "number" ? options.longitude : 10.1815));
  formData.append("city", options.city);
  formData.append("region", options.region);
  if (options.address) {
    formData.append("address", options.address);
  }
  formData.append("image", options.imageFile);
  formData.append(
    "metadata",
    JSON.stringify({
      interaction_mode: interactionMode,
      category,
      generate_audio: Boolean(options.generate_audio),
      generate_video: Boolean(options.generate_video),
      generate_pdf: Boolean(options.generate_pdf)
    })
  );

  const created = await requestApiData<{ id: number }>(createUrl, {
    method: "POST",
    headers: buildHeaders(),
    body: formData
  });

  await triggerSignalement(created.id, {
    user_prompt: prompt || undefined,
    interaction_mode: interactionMode,
    category,
    generate_media: Boolean(options.generate_media || options.generate_audio || options.generate_video || options.generate_pdf),
    generate_audio: Boolean(options.generate_audio),
    generate_video: Boolean(options.generate_video),
    generate_pdf: Boolean(options.generate_pdf)
  });

  return { signalementId: created.id };
}

export async function uploadAndStartPipeline(
  values: UploadFormValues,
  imageFile: File | null
): Promise<UploadAndProcessResult> {
  const prompt = values.user_prompt?.trim() || "";
  const hasImage = Boolean(imageFile);
  const interactionMode = resolveInteractionMode(hasImage, Boolean(prompt));

  return createSignalement({
    title: values.title?.trim() || `Signalement ${values.category}`,
    description: undefined,
    user_prompt: prompt || undefined,
    interaction_mode: interactionMode,
    category: values.category,
    latitude: typeof values.latitude === "number" ? values.latitude : undefined,
    longitude: typeof values.longitude === "number" ? values.longitude : undefined,
    city: values.city || "Unknown",
    region: values.region || "Unknown",
    address: values.address,
    generate_media: values.generate_media,
    generate_audio: values.generate_audio,
    generate_video: values.generate_video,
    generate_pdf: values.generate_pdf,
    imageFile
  });
}

export async function getProcessStatus(id: string | number): Promise<ProcessStatusResponse> {
  const baseUrl = getApiBaseUrlOrThrow();
  const url = `${baseUrl}/api/v1/process/${id}/status`;
  const data = await requestApiData<RawProcessStatusResponse>(url, {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });
  return normalizeStatus(data);
}

export function rememberAuthSession(session: AuthSession, user?: AuthUser | null): void {
  const stored: StoredAuthSession = { ...session, user: user || null };
  saveAuthSession(stored);
}

export function getRememberedAuthSession(): StoredAuthSession | null {
  return getStoredAuthSession();
}
