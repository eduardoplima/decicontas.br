import { http, HttpResponse } from "msw";

export const API_URL = "http://api.test";

// Default handlers. Individual tests override via server.use(...).
export const handlers = [
  http.post(`${API_URL}/api/v1/auth/login`, async ({ request }) => {
    const body = (await request.json()) as {
      username: string;
      password: string;
    };
    if (body.username === "alice" && body.password === "correct-horse") {
      return HttpResponse.json({
        access_token: "access-1",
        refresh_token: "refresh-1",
        token_type: "bearer",
      });
    }
    return HttpResponse.json(
      { detail: "invalid credentials" },
      { status: 401 },
    );
  }),
];
