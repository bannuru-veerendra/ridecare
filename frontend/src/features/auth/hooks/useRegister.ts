import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { authApi } from "@/api/auth.api";
import { getApiErrorMessage } from "@/lib/api-error";
import type { RegisterFormValues } from "../types";

/**
 * Handles user registration.
 * Backend validates email/password rules; client only collects input.
 */
export const useRegister = () => {
    const navigate = useNavigate();

    return useMutation({
        mutationFn: (values: RegisterFormValues) =>
            authApi.register({
                email: values.email,
                full_name: values.full_name,
                password: values.password,
            }),
        onSuccess: (_user, values) => {
            navigate(
                `/check-email?email=${encodeURIComponent(values.email)}`,
                { replace: true }
            );
        },
        onError: (error) => {
            toast.error(
                getApiErrorMessage(
                    error,
                    "Registration failed. Please try again."
                ),
                { id: "register-error" }
            );
        },
    });
};
