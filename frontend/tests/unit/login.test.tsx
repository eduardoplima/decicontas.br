import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/(auth)/login/page";
import { Toaster } from "@/components/ui/sonner";
import { clearTokens, getAccessToken, getRefreshToken } from "@/lib/auth";

import { API_URL } from "../mocks/handlers";
import { server } from "../mocks/server";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

function renderLogin() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <LoginPage />
      <Toaster />
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    clearTokens();
    pushMock.mockReset();
    replaceMock.mockReset();
  });

  it("shows validation errors when fields are empty", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText("Informe o usuário.")).toBeInTheDocument();
    expect(screen.getByText("Informe a senha.")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("submits valid credentials and redirects to /reviews", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText("Usuário"), "alice");
    await user.type(screen.getByLabelText("Senha"), "correct-horse");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/reviews"));
    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
  });

  it("shows an error when credentials are rejected", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText("Usuário"), "alice");
    await user.type(screen.getByLabelText("Senha"), "wrong");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(
      await screen.findByText("Usuário ou senha inválidos."),
    ).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
    expect(getAccessToken()).toBeNull();
  });

  it("surfaces network errors with a friendly message", async () => {
    server.use(
      http.post(`${API_URL}/api/v1/auth/login`, () => HttpResponse.error()),
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText("Usuário"), "alice");
    await user.type(screen.getByLabelText("Senha"), "correct-horse");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(
      await screen.findByText("Não foi possível conectar ao servidor."),
    ).toBeInTheDocument();
  });
});
