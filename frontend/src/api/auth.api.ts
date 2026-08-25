import apiClient from "@/lib/axios";
import type { User } from "@/types";
import type { LoginSchema, RegisterSchema } from "@/features/auth/schemas";

/**
 * Auth API calls.
 * All endpoints map to the backend /auth routes.
 * Tokens are set as httpOnly cookies by the server — not returned in JSON for SPA login/refresh.
 */

export type RegisterPayload = Omit<RegisterSchema, "confirm_password">;
export type LoginPayload = LoginSchema;

export interface SessionResponse {
    token_type: string;
}

export interface MessageResponse {
    message: string;
}

export const authApi = {
    register: async (payload: RegisterPayload): Promise<User> => {
        const response = await apiClient.post<User>(
            "/auth/register",
            payload
        );
        return response.data;
    },

    login: async (payload: LoginPayload): Promise<SessionResponse> => {
        const response = await apiClient.post<SessionResponse>(
            "/auth/login",
            payload
        );
        return response.data;
    },

    logout: async (): Promise<void> => {
        await apiClient.post("/auth/logout", {});
    },

    verifyEmail: async (token: string): Promise<MessageResponse> => {
        const response = await apiClient.post<MessageResponse>(
            "/auth/verify-email",
            { token }
        );
        return response.data;
    },

    resendVerification: async (email: string): Promise<MessageResponse> => {
        const response = await apiClient.post<MessageResponse>(
            "/auth/resend-verification",
            { email }
        );
        return response.data;
    },
};
