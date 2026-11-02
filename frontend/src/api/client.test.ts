import { describe, expect, it, vi } from 'vitest';

import { ApiError, api, apiBaseUrl } from './client';

describe('apiBaseUrl', () => {
  it('defaults to /api', () => {
    vi.stubEnv('VITE_API_URL', '');
    expect(apiBaseUrl()).toBe('/api');
  });

  it('uses VITE_API_URL without a trailing slash', () => {
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/');
    expect(apiBaseUrl()).toBe('https://api.example.test');
  });
});

describe('api.health', () => {
  it('returns the parsed body', async () => {
    vi.stubEnv('VITE_API_URL', '/api');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 })),
    );

    await expect(api.health()).resolves.toEqual({ status: 'ok' });
  });

  it('wraps network failures in ApiError with no status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const error: unknown = await api.health().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBeNull();
  });
});
