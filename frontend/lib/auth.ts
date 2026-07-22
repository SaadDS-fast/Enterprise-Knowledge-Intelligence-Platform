const TOKEN_KEY = "ekip_token";
const WORKSPACE_KEY = "ekip_workspace";

export function saveSession(token: string, workspaceId: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(WORKSPACE_KEY, workspaceId);
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(WORKSPACE_KEY);
}

export function getToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}

export function getWorkspaceId(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(WORKSPACE_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}
