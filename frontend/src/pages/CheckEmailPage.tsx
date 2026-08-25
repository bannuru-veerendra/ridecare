import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AuthPageShell from "@/components/common/AuthPageShell";
import { useResendVerification } from "@/features/auth/hooks/useResendVerification";
import {
    resendVerificationSchema,
    type ResendVerificationSchema,
} from "@/features/auth/schemas";

/**
 * After register (or failed login when unverified): check inbox + resend.
 */
export default function CheckEmailPage() {
    const [searchParams] = useSearchParams();
    const presetEmail = searchParams.get("email") ?? "";
    const { mutate: resend, isPending } = useResendVerification();
    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<ResendVerificationSchema>({
        resolver: zodResolver(resendVerificationSchema),
        defaultValues: { email: presetEmail },
        reValidateMode: "onBlur",
    });

    return (
        <AuthPageShell
            logoTo="/login"
            title="Check your email"
            subtitle="We sent a verification link to confirm your account"
        >
            <p className="mt-4 text-sm text-muted-foreground">
                Open the link in that email to unlock login. It expires in 24
                hours. If it never arrived, resend below.
            </p>

            <form
                onSubmit={handleSubmit((data) => resend(data.email))}
                className="mt-4 space-y-3"
                noValidate
            >
                <div className="space-y-1.5">
                    <Label htmlFor="email">Email</Label>
                    <Input
                        id="email"
                        type="email"
                        placeholder="your@email.com"
                        autoComplete="email"
                        autoCapitalize="none"
                        autoCorrect="off"
                        spellCheck={false}
                        className="border-white/15 bg-white/5 lowercase"
                        {...register("email")}
                    />
                    {errors.email && (
                        <p className="text-sm text-destructive">
                            {errors.email.message}
                        </p>
                    )}
                </div>

                <Button
                    type="submit"
                    className="w-full bg-brand text-brand-foreground hover:bg-brand/90"
                    disabled={isPending}
                >
                    {isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        "Resend verification email"
                    )}
                </Button>
            </form>

            <p className="mt-4 text-sm text-muted-foreground">
                Already verified?{" "}
                <Link
                    to="/login"
                    className="font-semibold text-brand hover:text-brand/80"
                >
                    Sign in
                </Link>
            </p>
        </AuthPageShell>
    );
}
