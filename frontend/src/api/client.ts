/**
 * Typed HTTP Client with RFC 7807 problem detail parsing, timeout, and abort support.
 */

import type { ProblemDetail } from '../types.ts';

export class ApiClientError extends Error {
  public status: number;
  public problem?: ProblemDetail;
  public rawBody?: string;

  constructor(status: number, message: string, problem?: ProblemDetail, rawBody?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.problem = problem;
    this.rawBody = rawBody;
  }
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | null | undefined>;
  timeoutMs?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, timeoutMs = 15000, signal: externalSignal, ...customConfig } = options;

  // Build query string
  const url = new URL(endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        url.searchParams.append(key, String(val));
      }
    });
  }

  // Setup timeout and abort controller
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const combinedSignal = externalSignal
    ? anySignal([externalSignal, controller.signal])
    : controller.signal;

  try {
    const response = await fetch(url.toString(), {
      ...customConfig,
      signal: combinedSignal,
      headers: {
        Accept: 'application/json, application/problem+json',
        ...customConfig.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let problem: ProblemDetail | undefined;
      let rawText = '';
      try {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('json')) {
          problem = await response.json();
        } else {
          rawText = await response.text();
        }
      } catch {
        // failed to parse body
      }

      const errorMessage =
        problem?.detail ||
        problem?.title ||
        rawText ||
        `HTTP ${response.status}: ${response.statusText}`;

      throw new ApiClientError(response.status, errorMessage, problem, rawText);
    }

    // 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new ApiClientError(408, 'Request timed out or was aborted');
    }
    if (error instanceof ApiClientError) {
      throw error;
    }
    throw new ApiClientError(500, error.message || 'Network error occurred');
  }
}

/**
 * Polyfill helper for combining multiple abort signals
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort();
      return signal;
    }
    signal.addEventListener('abort', () => controller.abort(), { once: true });
  }
  return controller.signal;
}
