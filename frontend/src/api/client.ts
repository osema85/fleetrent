/**
 * Tiny fetch wrapper.
 *
 * Security model:
 * - The short-lived access token is kept ONLY in memory (never localStorage), so an XSS
 *   bug cannot read a long-lived credential from storage.
 * - The refresh token is an httpOnly, Secure, SameSite=Strict cookie scoped to /api/auth;
 *   JavaScript can never read it.
 * - Every request carries the X-Requested-With header the API requires for cookie endpoints.
 */
import type { User } from './types';

const CSRF_HEADERS = { 'X-Requested-With': 'fleetrent' };

let accessToken: string | null = null;
let refreshInFlight: Promise<User | null> | null = null;
let onSessionLost: (() => void) | null = null;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function setSessionLostHandler(fn: () => void) {
  onSessionLost = fn;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: string[]; msg?: string }) => {
        const field = d.loc?.filter((p) => p !== 'body').join('.');
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join('\n');
  }
  return 'Request failed';
}

/** Exchange the refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<User | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch('/api/auth/refresh', {
          method: 'POST',
          credentials: 'same-origin',
          headers: CSRF_HEADERS,
        });
        if (!res.ok) {
          accessToken = null;
          return null;
        }
        const data = await res.json();
        accessToken = data.access_token;
        return data.user as User;
      } catch {
        return null;
      } finally {
        setTimeout(() => (refreshInFlight = null), 0);
      }
    })();
  }
  return refreshInFlight;
}

type Query = Record<string, string | number | boolean | null | undefined>;

interface Options {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Query;
  retry?: boolean;
}

export async function api<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const { method = 'GET', body, query, retry = true } = opts;
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v));
  });
  const url = `/api${path}${params.toString() ? `?${params}` : ''}`;

  const headers: Record<string, string> = { Accept: 'application/json', ...CSRF_HEADERS };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(url, {
    method,
    headers,
    credentials: 'same-origin',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && retry && !path.startsWith('/auth/')) {
    const user = await refreshSession();
    if (user) return api<T>(path, { ...opts, retry: false });
    onSessionLost?.();
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    if (res.status === 429) message = 'Too many requests. Please wait a moment and try again.';
    try {
      const data = await res.json();
      if (data?.detail) message = formatDetail(data.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
