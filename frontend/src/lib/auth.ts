/**
 * Token storage.
 *
 * Access token lives in memory only and is lost on hard reload. It is
 * re-hydrated from the refresh token when the app mounts.
 *
 * Refresh token is in localStorage as tech debt: the backend currently
 * returns it in the JSON body of POST /api/v1/auth/login (see
 * backend/app/auth/router.py) instead of setting an HTTP-only cookie.
 * Until the cookie flow lands we have no choice but to keep it in
 * JS-readable storage, which widens the XSS blast radius. Remove this
 * branch and read the cookie once the backend is updated.
 */

const REFRESH_TOKEN_KEY = "decicontas.refresh_token";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token === null) {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } else {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

export function setTokens(access: string, refresh: string): void {
  setAccessToken(access);
  setRefreshToken(refresh);
}

export function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}

export function hasSession(): boolean {
  return getAccessToken() !== null || getRefreshToken() !== null;
}
