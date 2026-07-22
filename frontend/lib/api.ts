import { getToken, getWorkspaceId } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function authHeaders(input?: HeadersInit): Headers {
  const headers = new Headers(input);
  const token = getToken();
  const workspace = getWorkspaceId();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (workspace) headers.set("X-Workspace-ID", workspace);
  return headers;
}

function requestUrl(path: string): string {
  if (path.startsWith("/api/")) return `${new URL(API_BASE).origin}${path}`;
  return `${API_BASE}${path}`;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = authHeaders(options.headers);
  if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new APIError(
      response.status,
      payload?.error?.message ?? payload?.message ?? `Request failed (${response.status})`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const headers = authHeaders(options.headers);
  const response = await fetch(requestUrl(path), {
    ...options,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new APIError(
      response.status,
      payload?.error?.message ?? payload?.message ?? `Request failed (${response.status})`,
    );
  }
  return response.blob();
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
