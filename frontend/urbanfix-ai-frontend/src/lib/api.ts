import type { ProcessStatus, Signalement, SignalementDetail } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, '') || 'http://localhost:8000';

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  meta?: unknown;
  error?: { message?: string };
};

type RawSignalement = Record<string, any>;

function isObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object';
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('urbanfix_token');
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init.headers || {}),
    },
  });
  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | T | null;

  if (!response.ok) {
    const message = isObject(payload) && 'error' in payload
      ? (payload.error as { message?: string } | undefined)?.message
      : null;
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  if (isObject(payload) && 'data' in payload) {
    return payload.data as T;
  }

  return payload as T;
}

function resolveUrl(path: unknown): string | null {
  if (!path || typeof path !== 'string') return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

function normalizeSignalement(raw: RawSignalement): Signalement {
  return {
    id: Number(raw.id),
    title: String(raw.title || ''),
    description: raw.description ?? null,
    city: String(raw.city || ''),
    region: String(raw.region || ''),
    latitude: Number(raw.latitude || 0),
    longitude: Number(raw.longitude || 0),
    imageUrl: resolveUrl(raw.image_url || raw.imageUrl || raw.image_path),
    status: raw.status || 'pending',
    createdAt: String(raw.created_at || raw.createdAt || new Date().toISOString()),
  };
}

export async function fetchSignalements(status = 'all'): Promise<Signalement[]> {
  const params = status && status !== 'all' ? `?status=${encodeURIComponent(status)}` : '';
  const rows = await request<RawSignalement[]>(`/api/v1/signalements/${params}`);
  return rows.map(normalizeSignalement);
}

export async function getSignalementDetails(id: string | number): Promise<SignalementDetail> {
  const raw = await request<RawSignalement>(`/api/v1/signalements/${id}`);
  const base = normalizeSignalement(raw);
  const scenarios = Array.isArray(raw.scenarios)
    ? raw.scenarios.map((scenario: RawSignalement) => ({
        imageUrl: resolveUrl(scenario.image_url || scenario.image_path || scenario.imageUrl),
        title: scenario.title,
        cost: Number(scenario.cost_total || scenario.cost || 0),
      }))
    : [];

  return {
    ...base,
    scenarios,
    audioUrl: resolveUrl(raw.audio_url || raw.audioUrl),
    pdfUrl: resolveUrl(raw.pdf_url || raw.pdfUrl),
  };
}

export async function getProcessStatus(id: string | number): Promise<ProcessStatus> {
  const raw = await request<RawSignalement>(`/api/v1/process/${id}/status`);
  return {
    id: Number(raw.id || raw.signalement_id || id),
    signalementId: Number(raw.signalement_id || id),
    status: raw.status || 'pending',
    currentStage: raw.current_stage || raw.stage || null,
    isComplete: raw.status === 'completed',
    audioUrl: resolveUrl(raw.outputs?.audio || raw.audio_url) || undefined,
    pdfUrl: resolveUrl(raw.outputs?.pdf || raw.pdf_url) || undefined,
  };
}

export async function createSignalement(input: {
  image: File;
  title: string;
  description: string;
  city: string;
  region: string;
  latitude: number | null;
  longitude: number | null;
}): Promise<number> {
  const form = new FormData();
  form.append('image', input.image);
  form.append('title', input.title);
  form.append('description', input.description);
  form.append('city', input.city);
  form.append('region', input.region);
  form.append('latitude', String(input.latitude ?? 36.8065));
  form.append('longitude', String(input.longitude ?? 10.1815));

  const created = await request<RawSignalement>('/api/v1/signalements/', {
    method: 'POST',
    body: form,
  });
  return Number(created.id);
}

export async function processSignalement(
  id: string | number,
  options: { generate_audio?: boolean; generate_pdf?: boolean } = {}
): Promise<void> {
  await request(`/api/v1/process/${id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      generate_audio: Boolean(options.generate_audio),
      generate_pdf: Boolean(options.generate_pdf),
      generate_media: Boolean(options.generate_audio || options.generate_pdf),
    }),
  });
}
