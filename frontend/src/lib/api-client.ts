import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!BASE_URL && typeof window !== "undefined") {
  console.warn("NEXT_PUBLIC_API_URL is not set — API calls will fail.");
}

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

type RetriableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// Single in-flight refresh so concurrent 401s share one round trip.
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error("no refresh token");

  // Bare axios: must NOT go through our interceptors or we'd loop on 401.
  const response = await axios.post<{
    access_token: string;
    refresh_token: string;
    token_type: string;
  }>(
    `${BASE_URL}/api/v1/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { "Content-Type": "application/json" } },
  );

  setTokens(response.data.access_token, response.data.refresh_token);
  return response.data.access_token;
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/login")) return;
  window.location.assign("/login");
}

apiClient.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as RetriableRequestConfig | undefined;
    const status = error.response?.status;

    if (status !== 401 || !original || original._retry) {
      return Promise.reject(error);
    }
    // Auth endpoints don't count: a 401 on /login is bad credentials, not an
    // expired token, and a 401 on /refresh means the refresh token itself is
    // dead — in that case give up and send the user to /login.
    if (original.url?.endsWith("/api/v1/auth/login")) {
      return Promise.reject(error);
    }
    if (original.url?.endsWith("/api/v1/auth/refresh")) {
      clearTokens();
      redirectToLogin();
      return Promise.reject(error);
    }
    // Nothing to refresh with.
    if (!getRefreshToken()) {
      clearTokens();
      redirectToLogin();
      return Promise.reject(error);
    }

    original._retry = true;

    try {
      refreshPromise = refreshPromise ?? refreshAccessToken();
      const newAccess = await refreshPromise;
      original.headers.set("Authorization", `Bearer ${newAccess}`);
      return apiClient(original);
    } catch (refreshError) {
      clearTokens();
      redirectToLogin();
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  },
);
