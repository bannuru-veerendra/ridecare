import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { X, Plus, Wrench } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import FormErrorBanner from "@/components/common/FormErrorBanner";
import FormSubmitButton from "@/components/common/FormSubmitButton";
import { serviceLogsApi } from "@/api/service-logs.api";
import {
    serviceLogSchema,
    type ServiceLogSchema,
    COMMON_SERVICES,
} from "../schemas";
import type { ServiceLog } from "../types";
import { appTodayISO } from "@/lib/date";

interface ServiceLogFormProps {
    /** Pass a service log to pre-fill the form for editing */
    defaultValues?: ServiceLog;
    onSubmit: (values: ServiceLogSchema) => void;
    isPending: boolean;
    error: Error | null;
}

/** Empty number inputs become undefined instead of NaN */
function optionalNumberValue(value: unknown): number | undefined {
    if (value === "" || value == null) return undefined;
    const num = Number(value);
    return Number.isNaN(num) ? undefined : num;
}

/**
 * Reusable service log form used for both create and edit.
 * Common services are shown as clickable badges; custom ones can be typed in.
 */
export default function ServiceLogForm({
    defaultValues,
    onSubmit,
    isPending,
    error,
}: ServiceLogFormProps) {
    const [selectedServices, setSelectedServices] = useState<string[]>([]);
    const [customService, setCustomService] = useState("");

    const {
        register,
        handleSubmit,
        setValue,
        reset,
        getValues,
        formState: { errors },
    } = useForm<ServiceLogSchema>({
        resolver: zodResolver(serviceLogSchema),
        reValidateMode: "onBlur",
        defaultValues: {
            date: appTodayISO(),
            services_done: [],
        },
    });

    const [suggestPending, setSuggestPending] = useState(false);

    // Prefill when editing; create mode remounts via key on the parent
    useEffect(() => {
        if (!defaultValues) return;

        setSelectedServices(defaultValues.services_done);
        setCustomService("");
        reset({
            date: defaultValues.date,
            odometer: defaultValues.odometer,
            service_center: defaultValues.service_center ?? "",
            total_cost: defaultValues.total_cost,
            services_done: defaultValues.services_done,
            next_service_date: defaultValues.next_service_date ?? "",
            next_service_odometer:
                defaultValues.next_service_odometer ?? undefined,
            notes: defaultValues.notes ?? "",
        });
    }, [defaultValues, reset]);

    useEffect(() => {
        setValue("services_done", selectedServices, { shouldValidate: true });
    }, [selectedServices, setValue]);

    const toggleService = (service: string) => {
        setSelectedServices((prev) =>
            prev.includes(service)
                ? prev.filter((s) => s !== service)
                : [...prev, service]
        );
    };

    const addCustomService = () => {
        const trimmed = customService.trim();
        if (trimmed && !selectedServices.includes(trimmed)) {
            setSelectedServices((prev) => [...prev, trimmed]);
            setCustomService("");
        }
    };

    const fillFromGuide = async () => {
        const { date, odometer } = getValues();
        if (!selectedServices.length) {
            toast.error("Select at least one service first");
            return;
        }
        if (!odometer || Number.isNaN(Number(odometer))) {
            toast.error("Enter the visit odometer first");
            return;
        }
        setSuggestPending(true);
        try {
            const suggestion = await serviceLogsApi.suggestNextDue({
                date: date || appTodayISO(),
                odometer: Number(odometer),
                services_done: selectedServices,
            });
            if (
                !suggestion.next_service_date &&
                suggestion.next_service_odometer == null
            ) {
                toast.message("No catalog interval matched these services");
                return;
            }
            if (suggestion.next_service_date) {
                setValue("next_service_date", suggestion.next_service_date, {
                    shouldValidate: true,
                });
            }
            if (suggestion.next_service_odometer != null) {
                setValue(
                    "next_service_odometer",
                    suggestion.next_service_odometer,
                    { shouldValidate: true }
                );
            }
            toast.success(
                suggestion.matched_tasks.length
                    ? `Filled from: ${suggestion.matched_tasks.join(", ")}`
                    : "Next due filled from guide"
            );
        } catch {
            toast.error("Could not suggest next due from the guide");
        } finally {
            setSuggestPending(false);
        }
    };

    const removeService = (service: string) => {
        setSelectedServices((prev) => prev.filter((s) => s !== service));
    };

    const inputClass = "border-white/15 bg-white/5";

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
            <FormErrorBanner error={error} />

            <div className="relative overflow-hidden rounded-2xl border border-brand/30 bg-brand/10 px-5 py-5">
                <div
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-1 bg-brand"
                />
                <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.16em] text-brand/80">
                    <Wrench className="h-3.5 w-3.5" />
                    Services selected
                </p>
                {selectedServices.length > 0 ? (
                    <>
                        <p className="font-heading mt-1 text-4xl font-extrabold tracking-wide text-brand">
                            {selectedServices.length}
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {selectedServices.slice(0, 3).join(", ") +
                                (selectedServices.length > 3
                                    ? ` +${selectedServices.length - 3} more`
                                    : "")}
                        </p>
                    </>
                ) : (
                    <p className="mt-2 text-sm text-muted-foreground">
                        Tap the chips below to add what was done
                    </p>
                )}
            </div>

            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                        <Label htmlFor="date">Date</Label>
                        <Input
                            id="date"
                            type="date"
                            max={appTodayISO()}
                            className={inputClass}
                            {...register("date")}
                        />
                        {errors.date && (
                            <p className="text-xs text-destructive">
                                {errors.date.message}
                            </p>
                        )}
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="odometer">Odometer (km)</Label>
                        <Input
                            id="odometer"
                            type="number"
                            placeholder="12500"
                            className={inputClass}
                            {...register("odometer", { valueAsNumber: true })}
                        />
                        {errors.odometer && (
                            <p className="text-xs text-destructive">
                                {errors.odometer.message}
                            </p>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                        <Label htmlFor="service_center">
                            Service center{" "}
                            <span className="text-xs text-muted-foreground">
                                (optional)
                            </span>
                        </Label>
                        <Input
                            id="service_center"
                            placeholder="Bharat Automobiles"
                            className={inputClass}
                            {...register("service_center")}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="total_cost">Cost (₹)</Label>
                        <Input
                            id="total_cost"
                            type="number"
                            placeholder="1500"
                            className={inputClass}
                            {...register("total_cost", { valueAsNumber: true })}
                        />
                        {errors.total_cost && (
                            <p className="text-xs text-destructive">
                                {errors.total_cost.message}
                            </p>
                        )}
                    </div>
                </div>

                <div className="space-y-2">
                    <Label>Services done</Label>

                    <div className="flex flex-wrap gap-2">
                        {COMMON_SERVICES.map((service) => (
                            <Badge
                                key={service}
                                variant={
                                    selectedServices.includes(service)
                                        ? "default"
                                        : "outline"
                                }
                                className={
                                    selectedServices.includes(service)
                                        ? "cursor-pointer select-none border-0 bg-brand text-brand-foreground"
                                        : "cursor-pointer select-none border-white/20"
                                }
                                onClick={() => toggleService(service)}
                            >
                                {service}
                            </Badge>
                        ))}
                    </div>

                    {selectedServices.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-1">
                            {selectedServices.map((service) => (
                                <Badge
                                    key={service}
                                    variant="secondary"
                                    className="gap-1 border-white/10 pr-1"
                                >
                                    {service}
                                    <button
                                        type="button"
                                        onClick={() => removeService(service)}
                                        className="ml-1 hover:text-destructive"
                                    >
                                        <X className="h-3 w-3" />
                                    </button>
                                </Badge>
                            ))}
                        </div>
                    )}

                    <div className="flex gap-2">
                        <Input
                            placeholder="Add custom service..."
                            value={customService}
                            className={inputClass}
                            onChange={(e) => setCustomService(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    addCustomService();
                                }
                            }}
                        />
                        <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="border-white/15"
                            onClick={addCustomService}
                        >
                            <Plus className="h-4 w-4" />
                        </Button>
                    </div>

                    {errors.services_done && (
                        <p className="text-xs text-destructive">
                            {errors.services_done.message}
                        </p>
                    )}
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                        <Label className="mb-0">Next due</Label>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="border-white/15"
                            disabled={suggestPending || isPending}
                            onClick={() => void fillFromGuide()}
                        >
                            {suggestPending ? "Suggesting…" : "Fill from guide"}
                        </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                        <Label htmlFor="next_service_date">
                            Next service date{" "}
                            <span className="text-xs text-muted-foreground">
                                (optional)
                            </span>
                        </Label>
                        <Input
                            id="next_service_date"
                            type="date"
                            className={inputClass}
                            {...register("next_service_date")}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="next_service_odometer">
                            Next at (km){" "}
                            <span className="text-xs text-muted-foreground">
                                (optional)
                            </span>
                        </Label>
                        <Input
                            id="next_service_odometer"
                            type="number"
                            placeholder="15000"
                            className={inputClass}
                            {...register("next_service_odometer", {
                                setValueAs: optionalNumberValue,
                            })}
                        />
                    </div>
                    </div>
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor="notes">
                        Notes{" "}
                        <span className="text-xs text-muted-foreground">
                            (optional)
                        </span>
                    </Label>
                    <Input
                        id="notes"
                        placeholder="Any additional notes..."
                        className={inputClass}
                        {...register("notes")}
                    />
                </div>
            </div>

            <FormSubmitButton
                isPending={isPending}
                isEdit={!!defaultValues}
                createLabel="Log service"
                className="w-full bg-brand text-brand-foreground hover:bg-brand/90"
            />
        </form>
    );
}
