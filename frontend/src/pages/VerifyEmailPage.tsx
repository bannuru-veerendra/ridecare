import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";

import AuthPageShell from "@/components/common/AuthPageShell";
import { authApi } from "@/api/auth.api";
import { getApiErrorMessage } from "@/lib/api-error";

/**
 * Public route opened from the verification email link.
 * Success toast lives on LoginPage (?verified=true) to avoid double toasts.
 */
export default function VerifyEmailPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token") ?? "";
    const started = useRef(false);
    const [errorMessage, setErrorMessage] = useState(
        token ? null : "Missing verification token."
    );

    useEffect(() => {
        if (!token || started.current) {
            return;
        }
        started.current = true;

        authApi
            .verifyEmail(token)
            .then(() => {
                navigate("/login?verified=true", { replace: true });
            })
            .catch((error) => {
                setErrorMessage(
                    getApiErrorMessage(
                        error,
                        "Verification link is invalid or expired."
                    )
                );
            });
    }, [token, navigate]);

    const isError = errorMessage !== null;

    return (
        <AuthPageShell
            logoTo="/login"
            title="Verifying email"
            subtitle={
                isError
                    ? "We could not verify that link"
                    : "Hang tight while we confirm your address"
            }
        >
            <div className="mt-6 space-y-4">
                {!isError && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Confirming your email…
                    </div>
                )}
                {isError && (
                    <>
                        <p className="text-sm text-destructive">{errorMessage}</p>
                        <Link
                            to="/login"
                            className="inline-flex h-8 w-full items-center justify-center rounded-lg bg-brand px-2.5 text-sm font-medium text-brand-foreground hover:bg-brand/90"
                        >
                            Back to login
                        </Link>
                        <p className="text-sm text-muted-foreground">
                            Need a new link?{" "}
                            <Link
                                to="/check-email"
                                className="font-semibold text-brand hover:text-brand/80"
                            >
                                Resend verification
                            </Link>
                        </p>
                    </>
                )}
            </div>
        </AuthPageShell>
    );
}
