// ── Foedus API client ────────────────────────────────────────
// JWT auth with automatic refresh-once-on-401.

import type { TokenResponse } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/api/v1";

const ACCESS_KEY = "foedus_access";
const REFRESH_KEY = "foedus_refresh";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function setTokens(t: TokenResponse) {
  localStorage.setItem(ACCESS_KEY, t.access_token);
  localStorage.setItem(REFRESH_KEY, t.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    setTokens(await res.json());
    return true;
  } catch {
    return false;
  }
}

interface ApiOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, formData, auth = true } = opts;

  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (auth) {
      const token = getToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    if (body !== undefined) headers["Content-Type"] = "application/json";
    return fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  };

  let res = await doFetch();

  // One silent refresh attempt on expiry
  if (res.status === 401 && auth) {
    if (await tryRefresh()) {
      res = await doFetch();
    } else {
      clearTokens();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError(401, "Session expired");
    }
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function isLoggedIn(): boolean {
  return getToken() !== null;
}
