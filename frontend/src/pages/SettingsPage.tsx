import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    Bell,
    FileWarning,
    KeyRound,
    Loader2,
    Mail,
    ShieldAlert,
    ShieldCheck,
    Trash2,
    UserRound,
    Wrench,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/common/PasswordInput";
import { Skeleton } from "@/components/ui/skeleton";
import { getApiErrorMessage } from "@/lib/api-error";
import { cn } from "@/lib/utils";

import {
    useCurrentUser,
    useDeleteAccount,
    useUpdatePassword,
    useUpdateProfile,
    useUpdateReminderPrefs,
} from "@/features/users/hooks/useUsers";
import {
    passwordUpdateSchema,
    profileUpdateSchema,
    type PasswordUpdateSchema,
    type ProfileUpdateSchema,
} from "@/features/users/schemas";

function initialsFromName(fullName: string): string {
    const parts = fullName.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return "?";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function ReminderToggle({
    id,
    label,
    description,
    checked,
    disabled,
    onCheckedChange,
}: {
    id: string;
    label: string;
    description: string;
    checked: boolean;
    disabled?: boolean;
    onCheckedChange: (next: boolean) => void;
}) {
    return (
        <div className="flex items-start justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="min-w-0">
                <Label htmlFor={id} className="cursor-pointer text-sm font-medium">
                    {label}
                </Label>
                <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
            </div>
            <button
                id={id}
                type="button"
                role="switch"
                aria-checked={checked}
                disabled={disabled}
                onClick={() => onCheckedChange(!checked)}
                className={cn(
                    "relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                    checked ? "bg-brand" : "bg-white/15"
                )}
            >
                <span
                    aria-hidden
                    className={cn(
                        "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform",
                        checked && "translate-x-5"
                    )}
                />
            </button>
        </div>
    );
}

/**
 * Account settings — profile, password, email reminders, delete account.
 */
export default function SettingsPage() {
    const { data: user, isLoading, isError } = useCurrentUser();
    const updateProfile = useUpdateProfile();
    const updatePassword = useUpdatePassword();
    const updateReminders = useUpdateReminderPrefs();
    const deleteAccount = useDeleteAccount();
    const [deletePassword, setDeletePassword] = useState("");

    const profileForm = useForm<ProfileUpdateSchema>({
        resolver: zodResolver(profileUpdateSchema),
        reValidateMode: "onBlur",
        defaultValues: {
            full_name: "",
            email: "",
        },
    });
    const { reset: resetProfile } = profileForm;

    const passwordForm = useForm<PasswordUpdateSchema>({
        resolver: zodResolver(passwordUpdateSchema),
        reValidateMode: "onBlur",
        defaultValues: {
            current_password: "",
            new_password: "",
            confirm_password: "",
        },
    });

    useEffect(() => {
        if (!user) return;
        resetProfile({
            full_name: user.full_name,
            email: user.email,
        });
    }, [user, resetProfile]);

    const onProfileSubmit = (values: ProfileUpdateSchema) => {
        updateProfile.mutate(
            {
                full_name: values.full_name,
                email: values.email,
            },
            {
                onSuccess: () => toast.success("Profile updated"),
                onError: (error) =>
                    toast.error(
                        getApiErrorMessage(error, "Failed to update profile")
                    ),
            }
        );
    };

    const onPasswordSubmit = (values: PasswordUpdateSchema) => {
        updatePassword.mutate(values, {
            onSuccess: () =>
                toast.success("Password changed. Please log in again."),
        });
    };

    const onDeleteAccount = () => {
        if (!deletePassword.trim()) {
            toast.error("Enter your password to delete the account");
            return;
        }
        deleteAccount.mutate({ password: deletePassword });
    };

    if (isLoading) {
        return (
            <div className="animate-fade-up space-y-8">
                <div>
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="mt-3 h-12 w-48" />
                    <Skeleton className="mt-3 h-4 w-72" />
                </div>
                <Skeleton className="h-28 w-full rounded-2xl" />
                <div className="space-y-6">
                    <Skeleton className="h-72 w-full rounded-2xl" />
                    <Skeleton className="h-96 w-full rounded-2xl" />
                </div>
            </div>
        );
    }

    if (isError || !user) {
        return (
            <div className="animate-fade-up surface-panel px-6 py-8 sm:px-8">
                <h1 className="font-heading text-3xl font-bold uppercase tracking-wide">
                    Settings
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                    Could not load your profile. Please try again.
                </p>
            </div>
        );
    }

    const initials = initialsFromName(user.full_name);
    const remindersPending = updateReminders.isPending;

    return (
        <div className="animate-fade-up space-y-8">
            <div>
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-brand">
                    Your account
                </p>
                <h1 className="font-heading mt-1 text-5xl font-extrabold uppercase italic tracking-wide sm:text-6xl">
                    Settings
                </h1>
                <p className="mt-2 max-w-xl text-sm text-muted-foreground">
                    Profile, password, reminder emails, and account deletion
                </p>
            </div>

            <section className="animate-speed-in relative overflow-hidden rounded-2xl border border-brand/25 bg-gradient-to-br from-brand/15 via-card/90 to-card/95 px-5 py-5 sm:px-7 sm:py-6">
                <div
                    aria-hidden
                    className="pointer-events-none absolute -right-16 -top-20 h-48 w-48 rounded-full bg-brand/20 blur-3xl"
                />
                <div
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-1 bg-brand"
                />
                <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand text-lg font-bold text-brand-foreground shadow-[0_0_0_4px_oklch(0.14_0.012_40)]">
                            {initials}
                        </div>
                        <div className="min-w-0">
                            <p className="font-heading truncate text-2xl font-bold uppercase tracking-wide sm:text-3xl">
                                {user.full_name}
                            </p>
                            <p className="mt-0.5 truncate text-sm text-muted-foreground">
                                {user.email}
                            </p>
                        </div>
                    </div>
                    <Badge
                        variant="outline"
                        className={
                            user.email_verified
                                ? "w-fit border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                                : "w-fit border-amber-500/40 bg-amber-500/10 text-amber-200"
                        }
                    >
                        {user.email_verified ? (
                            <>
                                <ShieldCheck className="mr-1 h-3.5 w-3.5" />
                                Email verified
                            </>
                        ) : (
                            <>
                                <Mail className="mr-1 h-3.5 w-3.5" />
                                Email not verified
                            </>
                        )}
                    </Badge>
                </div>
            </section>

            <div className="flex w-full flex-col gap-6">
                <section className="animate-speed-in relative overflow-hidden surface-panel px-6 py-6 sm:px-8 [animation-delay:80ms]">
                    <div
                        aria-hidden
                        className="absolute inset-y-0 left-0 w-1 bg-brand/80"
                    />
                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-brand/15 text-brand">
                            <UserRound className="h-4 w-4" />
                        </div>
                        <div>
                            <h2 className="font-heading text-xl font-bold uppercase tracking-wide">
                                Profile
                            </h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Shown in your account menu across the app
                            </p>
                        </div>
                    </div>

                    <form
                        onSubmit={profileForm.handleSubmit(onProfileSubmit)}
                        className="mt-6 max-w-2xl space-y-5"
                        noValidate
                    >
                        <div className="space-y-1.5">
                            <Label htmlFor="full_name">Full Name</Label>
                            <Input
                                id="full_name"
                                type="text"
                                autoComplete="name"
                                className="border-white/15 bg-white/5"
                                {...profileForm.register("full_name")}
                            />
                            {profileForm.formState.errors.full_name && (
                                <p className="text-sm text-destructive">
                                    {
                                        profileForm.formState.errors.full_name
                                            .message
                                    }
                                </p>
                            )}
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                autoComplete="email"
                                autoCapitalize="none"
                                autoCorrect="off"
                                spellCheck={false}
                                className="border-white/15 bg-white/5 lowercase"
                                {...profileForm.register("email")}
                            />
                            <p className="text-xs text-muted-foreground">
                                Changing email requires a new verification link
                            </p>
                            {profileForm.formState.errors.email && (
                                <p className="text-sm text-destructive">
                                    {profileForm.formState.errors.email.message}
                                </p>
                            )}
                        </div>

                        <Button
                            type="submit"
                            className="bg-brand text-brand-foreground hover:bg-brand/90"
                            disabled={updateProfile.isPending}
                        >
                            {updateProfile.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                "Save profile"
                            )}
                        </Button>
                    </form>
                </section>

                <section className="animate-speed-in relative overflow-hidden surface-panel px-6 py-6 sm:px-8 [animation-delay:160ms]">
                    <div
                        aria-hidden
                        className="absolute inset-y-0 left-0 w-1 bg-brand/80"
                    />
                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-brand/15 text-brand">
                            <KeyRound className="h-4 w-4" />
                        </div>
                        <div>
                            <h2 className="font-heading text-xl font-bold uppercase tracking-wide">
                                Password
                            </h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Signs you out on every device after a change
                            </p>
                        </div>
                    </div>

                    <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-xs leading-relaxed text-muted-foreground">
                        Use a strong password you do not reuse elsewhere. RideCare
                        never stores the plain text.
                    </div>

                    <form
                        onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}
                        className="mt-6 max-w-2xl space-y-5"
                        noValidate
                    >
                        <div className="space-y-1.5">
                            <Label htmlFor="current_password">
                                Current password
                            </Label>
                            <PasswordInput
                                id="current_password"
                                autoComplete="current-password"
                                className="border-white/15 bg-white/5"
                                {...passwordForm.register("current_password")}
                            />
                            {passwordForm.formState.errors.current_password && (
                                <p className="text-sm text-destructive">
                                    {
                                        passwordForm.formState.errors
                                            .current_password.message
                                    }
                                </p>
                            )}
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="new_password">New password</Label>
                            <PasswordInput
                                id="new_password"
                                autoComplete="new-password"
                                className="border-white/15 bg-white/5"
                                {...passwordForm.register("new_password")}
                            />
                            <p className="text-xs text-muted-foreground">
                                At least 8 characters, with one uppercase letter,
                                one number, and one special character.
                            </p>
                            {passwordForm.formState.errors.new_password && (
                                <p className="text-sm text-destructive">
                                    {
                                        passwordForm.formState.errors
                                            .new_password.message
                                    }
                                </p>
                            )}
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="confirm_password">
                                Confirm new password
                            </Label>
                            <PasswordInput
                                id="confirm_password"
                                autoComplete="new-password"
                                className="border-white/15 bg-white/5"
                                {...passwordForm.register("confirm_password")}
                            />
                            {passwordForm.formState.errors.confirm_password && (
                                <p className="text-sm text-destructive">
                                    {
                                        passwordForm.formState.errors
                                            .confirm_password.message
                                    }
                                </p>
                            )}
                        </div>

                        <Button
                            type="submit"
                            className="bg-brand text-brand-foreground hover:bg-brand/90"
                            disabled={updatePassword.isPending}
                        >
                            {updatePassword.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                "Change password"
                            )}
                        </Button>
                    </form>
                </section>

            <section className="animate-speed-in relative overflow-hidden surface-panel px-6 py-6 sm:px-8 [animation-delay:220ms]">
                <div
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-1 bg-brand/80"
                />
                <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-brand/15 text-brand">
                        <Bell className="h-4 w-4" />
                    </div>
                    <div>
                        <h2 className="font-heading text-xl font-bold uppercase tracking-wide">
                            Email reminders
                        </h2>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Daily digest around midnight IST when something needs
                            attention
                        </p>
                    </div>
                </div>

                <div className="mt-6 max-w-2xl space-y-3">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <Wrench className="h-3.5 w-3.5" />
                        Service
                    </div>
                    <ReminderToggle
                        id="email_service_reminders"
                        label="Service due emails"
                        description="Soon or overdue next-service date / km"
                        checked={user.email_service_reminders}
                        disabled={remindersPending}
                        onCheckedChange={(next) =>
                            updateReminders.mutate({
                                email_service_reminders: next,
                            })
                        }
                    />

                    <div className="flex items-center gap-2 pt-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <FileWarning className="h-3.5 w-3.5" />
                        Documents
                    </div>
                    <ReminderToggle
                        id="email_document_reminders"
                        label="Document expiry emails"
                        description="Insurance, licence, or RC expiring soon or expired"
                        checked={user.email_document_reminders}
                        disabled={remindersPending}
                        onCheckedChange={(next) =>
                            updateReminders.mutate({
                                email_document_reminders: next,
                            })
                        }
                    />
                </div>
            </section>

            <section className="animate-speed-in relative overflow-hidden rounded-2xl border border-destructive/30 bg-destructive/5 px-6 py-6 sm:px-8 [animation-delay:280ms]">
                <div
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-1 bg-destructive"
                />
                <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-destructive/15 text-destructive">
                        <ShieldAlert className="h-4 w-4" />
                    </div>
                    <div>
                        <h2 className="font-heading text-xl font-bold uppercase tracking-wide text-destructive">
                            Delete account
                        </h2>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Permanently removes your garage, fuel/service logs, and
                            documents. This cannot be undone.
                        </p>
                    </div>
                </div>

                <div className="mt-6 space-y-4 sm:max-w-md">
                    <div className="space-y-1.5">
                        <Label htmlFor="delete_password">
                            Confirm with your password
                        </Label>
                        <PasswordInput
                            id="delete_password"
                            autoComplete="current-password"
                            className="border-white/15 bg-white/5"
                            value={deletePassword}
                            onChange={(e) => setDeletePassword(e.target.value)}
                        />
                    </div>
                    <Button
                        type="button"
                        variant="destructive"
                        disabled={deleteAccount.isPending}
                        onClick={onDeleteAccount}
                    >
                        {deleteAccount.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <>
                                <Trash2 className="mr-1.5 h-4 w-4" />
                                Delete my account
                            </>
                        )}
                    </Button>
                </div>
            </section>
            </div>
        </div>
    );
}
