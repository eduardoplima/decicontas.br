import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api-client";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "@/lib/auth";

import { API_URL } from "../mocks/handlers";
import { server } from "../mocks/server";

const originalLocation = window.location;

describe("api-client 401-refresh-retry", () => {
  beforeEach(() => {
    clearTokens();
    // Stub window.location so the redirect-on-refresh-failure path doesn't
    // blow up jsdom.
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...originalLocation,
        pathname: "/reviews",
        assign: vi.fn(),
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("refreshes the access token once on 401 and retries the request", async () => {
    setAccessToken("stale-access");
    setRefreshToken("valid-refresh");

    let attempts = 0;
    server.use(
      http.get(`${API_URL}/api/v1/reviews`, ({ request }) => {
        attempts += 1;
        const auth = request.headers.get("Authorization");
        if (auth === "Bearer fresh-access") {
          return HttpResponse.json({ items: [] });
        }
        return HttpResponse.json({ detail: "expired" }, { status: 401 });
      }),
      http.post(`${API_URL}/api/v1/auth/refresh`, async ({ request }) => {
        const body = (await request.json()) as { refresh_token: string };
        expect(body.refresh_token).toBe("valid-refresh");
        return HttpResponse.json({
          access_token: "fresh-access",
          refresh_token: "rotated-refresh",
          token_type: "bearer",
        });
      }),
    );

    const response = await apiClient.get("/api/v1/reviews");

    expect(response.data).toEqual({ items: [] });
    expect(attempts).toBe(2);
    expect(getAccessToken()).toBe("fresh-access");
    expect(getRefreshToken()).toBe("rotated-refresh");
  });

  it("clears tokens and redirects on refresh failure", async () => {
    setAccessToken("stale-access");
    setRefreshToken("revoked-refresh");

    server.use(
      http.get(`${API_URL}/api/v1/reviews`, () =>
        HttpResponse.json({ detail: "expired" }, { status: 401 }),
      ),
      http.post(`${API_URL}/api/v1/auth/refresh`, () =>
        HttpResponse.json({ detail: "invalid" }, { status: 401 }),
      ),
    );

    await expect(apiClient.get("/api/v1/reviews")).rejects.toBeDefined();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith("/login");
  });

  it("does not retry when no refresh token is available", async () => {
    setAccessToken("stale-access");

    let attempts = 0;
    server.use(
      http.get(`${API_URL}/api/v1/reviews`, () => {
        attempts += 1;
        return HttpResponse.json({ detail: "expired" }, { status: 401 });
      }),
    );

    await expect(apiClient.get("/api/v1/reviews")).rejects.toBeDefined();

    expect(attempts).toBe(1);
    expect(getAccessToken()).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith("/login");
  });
});
