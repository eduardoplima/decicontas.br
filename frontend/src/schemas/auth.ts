import { z } from "zod";

// Mirrors LoginRequest in backend/app/auth/schemas.py.
export const loginRequestSchema = z.object({
  username: z
    .string()
    .min(1, { message: "Informe o usuário." })
    .max(150, { message: "Usuário muito longo." }),
  password: z
    .string()
    .min(1, { message: "Informe a senha." })
    .max(255, { message: "Senha muito longa." }),
});
export type LoginRequest = z.infer<typeof loginRequestSchema>;

// Mirrors TokenPair in backend/app/auth/schemas.py.
export const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string().default("bearer"),
});
export type TokenPair = z.infer<typeof tokenPairSchema>;

// Mirrors RefreshRequest in backend/app/auth/schemas.py.
export const refreshRequestSchema = z.object({
  refresh_token: z.string().min(1),
});
export type RefreshRequest = z.infer<typeof refreshRequestSchema>;

// Mirrors UserOut in backend/app/auth/schemas.py.
export const userOutSchema = z.object({
  id: z.number().int(),
  username: z.string(),
  email: z.string(),
  role: z.string(),
  is_active: z.boolean(),
});
export type UserOut = z.infer<typeof userOutSchema>;
