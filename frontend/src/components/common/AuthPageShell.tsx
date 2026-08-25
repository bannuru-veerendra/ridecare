import type { ReactNode } from "react";

import RideCareLogo from "@/components/common/RideCareLogo";

interface AuthPageShellProps {
    logoTo: "/login" | "/register" | "/check-email";
    title: string;
    subtitle: string;
    children: ReactNode;
}

/** Shared full-bleed auth chrome for login and register. */
export default function AuthPageShell({
    logoTo,
    title,
    subtitle,
    children,
}: AuthPageShellProps) {
    return (
        <div className="relative flex min-h-dvh">
            <div className="absolute inset-0 -z-10">
                <img
                    src="/rider-hero.jpg"
                    alt=""
                    className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-background/85" />
                <div
                    aria-hidden
                    className="absolute bottom-12 left-1/2 h-px w-48 -translate-x-1/2 bg-gradient-to-r from-transparent via-brand/50 to-transparent"
                />
            </div>

            <div className="flex w-full flex-col items-center justify-center px-4 py-5 sm:py-8">
                <div className="animate-speed-in mb-4">
                    <RideCareLogo to={logoTo} inverted />
                </div>

                <div className="animate-fade-up surface-panel w-full max-w-md px-5 py-5 sm:px-7 sm:py-6">
                    <h1 className="font-heading text-2xl font-bold uppercase tracking-wide sm:text-3xl">
                        {title}
                    </h1>
                    <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>
                    {children}
                </div>
            </div>
        </div>
    );
}
