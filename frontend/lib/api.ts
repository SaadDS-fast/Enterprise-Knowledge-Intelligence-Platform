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

async function readBounded(response: Response, maxBytes: number): Promise<Uint8Array> {
  const declaredLength = Number(response.headers.get("content-length") ?? "0");
  if (declaredLength > maxBytes) {
    await response.body?.cancel();
    throw new APIError(413, "The download exceeds the safety limit.");
  }
  if (!response.body) return new Uint8Array();
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        throw new APIError(413, "The download exceeds the safety limit.");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const output = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return output;
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

export async function apiBinary(
  path: string,
  expectedContentType: string,
  maxBytes: number,
  signal?: AbortSignal,
): Promise<Blob> {
  const response = await fetch(requestUrl(path), {
    headers: authHeaders(),
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw new APIError(response.status, "The requested download is unavailable.");
  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim();
  if (contentType !== expectedContentType) throw new APIError(502, "The download format is invalid.");
  const bytes = await readBounded(response, maxBytes);
  return new Blob([bytes.buffer as ArrayBuffer], { type: expectedContentType });
}

export async function apiBoundedJson<T>(
  path: string,
  maxBytes: number,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(requestUrl(path), {
    headers: authHeaders(),
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw new APIError(response.status, "The requested data is unavailable.");
  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim();
  if (contentType !== "application/json") {
    await response.body?.cancel();
    throw new APIError(502, "The download format is invalid.");
  }
  const text = new TextDecoder("utf-8", { fatal: true }).decode(await readBounded(response, maxBytes));
  return JSON.parse(text) as T;
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
