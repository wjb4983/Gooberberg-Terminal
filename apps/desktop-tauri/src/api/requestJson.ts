import { invoke } from '@tauri-apps/api/core';
import { resolveAuthorizationHeader } from './authHeaders';

interface NativeApiHttpResponse {
  status: number;
  body: string;
}

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

function formatNetworkFailureMessage(url: string, authAttached: boolean, error: TypeError): string {
  const origin = typeof window !== 'undefined' ? window.location.origin : 'unknown origin';
  const detail = error.message?.trim() ? ` Browser detail: ${error.message.trim()}.` : '';
  const authHint = authAttached
    ? ' Authorization header was attached; re-check token formatting, CORS preflight, and token validity.'
    : ' No Authorization header was attached.'
  return `Network request failed for ${url} from ${origin}.${authHint} Check API base URL, CORS, TLS/certificate, and whether the API is reachable from this machine.${detail}`;
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
  const authAttached = headers.has('Authorization');

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
      throw new Error(formatNetworkFailureMessage(url, authAttached, error));
    }
    throw error;
  }
}
