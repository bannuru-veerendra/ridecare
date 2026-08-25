import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { authApi } from "@/api/auth.api";
import { getApiErrorMessage } from "@/lib/api-error";

/** Resend the verification email for an unverified account. */
export const useResendVerification = () => {
    return useMutation({
        mutationFn: (email: string) => authApi.resendVerification(email),
        onSuccess: (data) => {
            toast.success(data.message, { id: "resend-verification" });
        },
        onError: (error) => {
            toast.error(
                getApiErrorMessage(
                    error,
                    "Could not resend verification email."
                ),
                { id: "resend-verification-error" }
            );
        },
    });
};
