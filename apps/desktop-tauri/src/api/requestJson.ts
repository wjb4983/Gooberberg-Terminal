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

function shouldUseDevProxy(url: string): boolean {
  if (!import.meta.env.DEV || typeof window === 'undefined') {
    return false;
  }

  try {
    return new URL(url).origin !== window.location.origin;
  } catch {
    return false;
  }
}

function toDevProxyUrl(url: string): string {
  return `/__gb_api_proxy?url=${encodeURIComponent(url)}`;
}

function summarizeFailureBody(body: string): string {
  const trimmed = body.trim();
  if (!trimmed) {
    return '';
  }

  const maxLen = 280;
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (parsed && typeof parsed === 'object') {
      const detail = (parsed as Record<string, unknown>).detail;
      if (typeof detail === 'string' && detail.trim().length > 0) {
        return `: ${detail.trim().slice(0, maxLen)}`;
      }
      return `: ${JSON.stringify(parsed).slice(0, maxLen)}`;
    }
  } catch {
    // Fall back to raw response text for non-JSON payloads.
  }

  return `: ${trimmed.slice(0, maxLen)}`;
}

function summarizeCorrelatedFailure(body: string): string {
  const trimmed = body.trim();
  if (!trimmed) return '';
  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>;
    const requestId = typeof parsed.request_id === 'string' ? parsed.request_id : undefined;
    const errorCode = typeof parsed.error_code === 'string' ? parsed.error_code : undefined;
    const detail = typeof parsed.detail === 'string' ? parsed.detail : undefined;
    const correlation = [requestId ? `request_id=${requestId}` : '', errorCode ? `error_code=${errorCode}` : '']
      .filter(Boolean)
      .join(', ');
    const prefix = correlation ? ` [${correlation}]` : '';
    const detailSuffix = detail?.trim() ? `: ${detail.trim().slice(0, 280)}` : '';
    return `${prefix}${detailSuffix}`;
  } catch {
    return summarizeFailureBody(body);
  }
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
  const browserUrl = shouldUseDevProxy(url) ? toDevProxyUrl(url) : url;

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
      throw new Error(
        `Request failed (${response.status}) for ${method.toUpperCase()} ${url}${summarizeCorrelatedFailure(response.body)}`,
      );
    }

    return JSON.parse(response.body) as T;
  }

  try {
    const response = await fetch(browserUrl, {
      ...init,
      headers,
    });

    if (!response.ok) {
      const responseBody = await response.text();
      throw new Error(
        `Request failed (${response.status}) for ${method.toUpperCase()} ${url}${summarizeCorrelatedFailure(responseBody)}`,
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(formatNetworkFailureMessage(url, authAttached, error));
    }
    throw error;
  }
}
