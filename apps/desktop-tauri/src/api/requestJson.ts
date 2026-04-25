import { invoke } from '@tauri-apps/api/core';
import { resolveAuthorizationHeader } from './authHeaders';

interface NativeApiHttpResponse {
  status: number;
  body: string;
}

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

export async function requestJson<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('Authorization')) {
    const authHeader = await resolveAuthorizationHeader(path);
    if (authHeader) {
      headers.set('Authorization', authHeader);
    }
  }

  const url = `${baseUrl.replace(/\/$/, '')}${path}`;
  const method = init?.method ?? 'GET';

  if (isTauriRuntime()) {
    const response = await invoke<NativeApiHttpResponse>('api_http_request', {
      request: {
        method,
        url,
        headers: Array.from(headers.entries()),
        body: typeof init?.body === 'string' ? init.body : undefined,
      },
    });

    if (response.status < 200 || response.status >= 300) {
      throw new Error(`Request failed (${response.status}) for ${path}`);
    }

    return JSON.parse(response.body) as T;
  }

  try {
    const response = await fetch(url, {
      ...init,
      headers,
    });

    if (!response.ok) {
      throw new Error(`Request failed (${response.status}) for ${path}`);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof TypeError) {
      const origin = typeof window !== 'undefined' ? window.location.origin : 'unknown origin';
      throw new Error(`Network request failed for ${url} from ${origin}. Check API base URL, CORS, TLS/certificate, and whether the API is reachable from this machine.`);
    }
    throw error;
  }
}
