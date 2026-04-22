import type { AuthSession, AuthUser } from "@/lib/types";

const SESSION_KEY = "urbanfix.auth.session";

export type StoredAuthSession = AuthSession & {
  user?: AuthUser | null;
};

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getStoredAuthSession(): StoredAuthSession | null {
  if (!canUseStorage()) {
    return null;
  }

  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredAuthSession;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function saveAuthSession(session: StoredAuthSession): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearAuthSession(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(SESSION_KEY);
}

export function getAccessToken(): string | null {
  return getStoredAuthSession()?.access_token || null;
}

export function getRefreshToken(): string | null {
  return getStoredAuthSession()?.refresh_token || null;
}

export function hasStoredAuthSession(): boolean {
  return Boolean(getAccessToken() || process.env.NEXT_PUBLIC_API_TOKEN);
}
