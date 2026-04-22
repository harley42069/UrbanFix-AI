export type PipelineStatus = "pending" | "processing" | "completed" | "failed" | "rejected";

export type ScenarioType = "basic" | "smart" | "premium";

export type SupportedLanguage = "fr" | "en";

export type InteractionMode = "photo_only" | "photo_and_prompt" | "prompt_only";

export type ProblemCategory =
  | "roads"
  | "sidewalk"
  | "lighting"
  | "waste"
  | "drainage"
  | "other";

export type DetectionItem = {
  class_name?: string;
  confidence?: number;
  bbox?: number[];
  [key: string]: unknown;
};

export type PaginationMeta = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
};

export type ApiMeta = {
  request_id: string;
  timestamp: string;
  pagination?: PaginationMeta | null;
};

export type ApiResponseEnvelope<T> = {
  success: boolean;
  data: T | null;
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  } | null;
  meta?: ApiMeta | null;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type AuthUser = {
  id: number;
  email: string;
  username: string;
  full_name: string;
  phone?: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
};

export type DetectionsPayload = {
  total_problems?: number;
  summary?: Record<string, number>;
  detections?: DetectionItem[];
  annotated_image_url?: string;
  language?: SupportedLanguage;
  [key: string]: unknown;
};

export type CostItem = {
  category: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  total: number;
};

export type ScenarioAction = {
  label: string;
  details?: string | null;
};

export type Scenario = {
  id: string;
  scenario_type: ScenarioType;
  title: string;
  description: string;
  prompt_used: string;
  image_url?: string | null;
  narration_text: string;
  actions: ScenarioAction[];
  cost_breakdown: CostItem[];
  cost_total: number;
  language?: SupportedLanguage;
  [key: string]: unknown;
};

export type LegacyScenarioItem = {
  id?: number | string;
  type?: string;
  scenario_type?: string;
  title?: string;
  prompt?: string;
  prompt_used?: string;
  description?: string;
  image_path?: string;
  image_url?: string;
  narration_text?: string;
  actions?: Array<{ label?: string; details?: string | null }>;
  cost_breakdown?: CostItem[];
  cost_total?: number;
  language?: string;
  [key: string]: unknown;
};

export type LegacyScenariosPayload = {
  items?: LegacyScenarioItem[];
  selected?: LegacyScenarioItem;
  [key: string]: unknown;
};

export type EstimationsPayload = {
  total_min?: number;
  total_max?: number;
  total_avg?: number;
  total_cost_tnd?: number;
  breakdown?: Record<string, unknown> | CostItem[];
  duration_days?: number;
  language?: SupportedLanguage;
  [key: string]: unknown;
};

export type MediaUrls = {
  audio_url?: string | null;
  video_url?: string | null;
  pdf_url?: string | null;
  annotated_image?: string | null;
  scenario_image?: string | null;
};

export type RawProcessStatusResponse = {
  signalement_id: number;
  status?: PipelineStatus;
  progress?: number;
  current_stage?: string;
  stage?: string;
  last_error?: { stage?: string; message?: string; [key: string]: unknown } | null;
  completed_at?: string | null;
  processing_time_seconds?: number | null;
  language?: string;
  detections?: DetectionsPayload | null;
  scenarios?: LegacyScenariosPayload | LegacyScenarioItem[] | null;
  estimations?: EstimationsPayload | null;
  outputs?: {
    annotated_image?: string | null;
    scenario_image?: string | null;
    audio?: string | null;
    video?: string | null;
    pdf?: string | null;
  };
  audio_url?: string | null;
  video_url?: string | null;
  pdf_url?: string | null;
  ws_channel?: string;
  results?: {
    language?: string;
    detections?: DetectionsPayload | null;
    scenarios?: LegacyScenarioItem[] | LegacyScenariosPayload | null;
    media?: {
      annotated_image?: string | null;
      scenario_image?: string | null;
      audio?: string | null;
      video?: string | null;
      pdf?: string | null;
      audio_url?: string | null;
      video_url?: string | null;
      pdf_url?: string | null;
    };
  };
};

export type ProcessStatusResponse = {
  signalement_id: number;
  status: PipelineStatus;
  progress: number;
  current_stage?: string;
  stage?: string;
  language: SupportedLanguage;
  last_error?: { stage?: string; message?: string; [key: string]: unknown } | null;
  completed_at?: string | null;
  processing_time_seconds?: number | null;
  detections?: DetectionsPayload | null;
  scenarios: Scenario[];
  estimations?: EstimationsPayload | null;
  outputs: MediaUrls;
  media: MediaUrls;
  audio_url?: string | null;
  video_url?: string | null;
  pdf_url?: string | null;
  results: {
    language: SupportedLanguage;
    detections?: DetectionsPayload | null;
    scenarios: Scenario[];
    media: MediaUrls;
  };
  ws_channel?: string;
};

export type SignalementSummary = {
  id: number;
  title?: string;
  description?: string;
  status?: PipelineStatus;
  progress?: number;
  current_stage?: string | null;
  city?: string;
  region?: string;
  address?: string | null;
  image_url?: string | null;
  created_at?: string;
  updated_at?: string;
  completed_at?: string | null;
  user_id?: number;
  [key: string]: unknown;
};

export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  } | null;
};

export type UploadFormValues = {
  title?: string;
  description?: string;
  user_prompt?: string;
  interaction_mode: InteractionMode;
  category: ProblemCategory;
  latitude?: number;
  longitude?: number;
  city?: string;
  region?: string;
  address?: string;
  generate_media?: boolean;
  generate_audio?: boolean;
  generate_video?: boolean;
  generate_pdf?: boolean;
};

export type UploadAndProcessResult = {
  signalementId: number;
};

export type SignalementCreateInput = {
  title: string;
  description?: string;
  user_prompt?: string;
  interaction_mode: InteractionMode;
  category: ProblemCategory;
  latitude?: number;
  longitude?: number;
  city: string;
  region: string;
  address?: string;
  generate_media?: boolean;
  generate_audio?: boolean;
  generate_video?: boolean;
  generate_pdf?: boolean;
};

export type ListSignalementsParams = {
  skip?: number;
  limit?: number;
  status?: PipelineStatus;
  city?: string;
  region?: string;
};
