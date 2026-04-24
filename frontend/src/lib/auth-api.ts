import { apiClient } from "@/lib/api-client";
import {
  LoginRequest,
  TokenPair,
  tokenPairSchema,
  UserOut,
  userOutSchema,
} from "@/schemas/auth";

export async function login(body: LoginRequest): Promise<TokenPair> {
  const response = await apiClient.post("/api/v1/auth/login", body);
  return tokenPairSchema.parse(response.data);
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post("/api/v1/auth/logout", { refresh_token: refreshToken });
}

export async function fetchCurrentUser(): Promise<UserOut> {
  const response = await apiClient.get("/api/v1/auth/me");
  return userOutSchema.parse(response.data);
}
