/**
 * Thin typed client for the Fitzy API.
 *
 * The base URL comes from VITE_API_URL (see .env.example). In dev it is `/api`,
 * which Vite proxies to the FastAPI backend on :8000 with the prefix stripped.
 */

export interface HealthResponse {
  status: string;
}

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function apiBaseUrl(): string {
  const configured: string | undefined = import.meta.env.VITE_API_URL;
  const base = configured && configured.trim() !== '' ? configured.trim() : '/api';
  return base.replace(/\/+$/, '');
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const url = `${apiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: 'application/json' },
      signal: signal ?? null,
    });
  } catch (cause) {
    throw new ApiError(`Network error calling ${path}: ${String(cause)}`, null);
  }
  if (!response.ok) {
    throw new ApiError(`${path} returned HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  health: (signal?: AbortSignal): Promise<HealthResponse> =>
    getJson<HealthResponse>('/health', signal),
};
