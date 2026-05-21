/**
 * Thin fetch wrapper — all requests go to /api, handles 401 redirects,
 * and serialises/deserialises JSON automatically.
 */

const BASE = "/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string
  ) {
    super(`API ${status}: ${detail}`);
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, string | number | boolean>
): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);

  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v));
    }
  }

  const init: RequestInit = {
    method,
    credentials: "same-origin",
    headers: {},
  };

  if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  const resp = await fetch(url.toString(), init);

  if (resp.status === 401) {
    // Redirect to login if not already there
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Not authenticated");
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const err = await resp.json();
      detail = err.detail ?? JSON.stringify(err);
    } catch {
      // ignore parse error
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) {
    return undefined as unknown as T;
  }

  return resp.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, params?: Record<string, string | number | boolean>) =>
    request<T>("GET", path, undefined, params),

  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),

  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),

  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),

  delete: <T = void>(path: string, params?: Record<string, string | number | boolean>) =>
    request<T>("DELETE", path, undefined, params),
};
