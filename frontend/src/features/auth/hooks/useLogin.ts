import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { authApi } from "@/api/auth.api";
import { getApiErrorMessage } from "@/lib/api-error";
import useAuthStore from "@/store/auth.store";
import type { LoginFormValues } from "../types";

/**
 * Handles user login.
 * Server sets httpOnly cookies; we only mark the UI session as authenticated.
 */
export const useLogin = () => {
    const navigate = useNavigate();
    const setAuthenticated = useAuthStore((state) => state.setAuthenticated);

    return useMutation({
        mutationFn: (values: LoginFormValues) => authApi.login(values),
        onSuccess: () => {
            setAuthenticated();
            navigate("/dashboard");
        },
        onError: (error, values) => {
            if (
                isAxiosError(error) &&
                error.response?.status === 403 &&
                typeof error.response.data?.detail === "string" &&
                error.response.data.detail.toLowerCase().includes("not verified")
            ) {
                toast.error(error.response.data.detail, {
                    id: "login-unverified",
                });
                navigate(
                    `/check-email?email=${encodeURIComponent(values.email)}`,
                    { replace: true }
                );
                return;
            }
            toast.error(
                getApiErrorMessage(error, "Login failed. Please try again."),
                { id: "login-error" }
            );
        },
    });
};
