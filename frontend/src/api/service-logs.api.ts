import apiClient from "@/lib/axios";
import type { CursorPage } from "@/types";
import type { ServiceLogSchema } from "@/features/service-logs/schemas";

/**
 * Service log API calls.
 * All endpoints map to the backend /service_logs routes.
 * vehicle_id is passed as a query parameter.
 */

export interface ServiceLog {
    id: string;
    vehicle_id: string;
    date: string;
    odometer: number;
    service_center: string | null;
    total_cost: number;
    services_done: string[];
    next_service_date: string | null;
    next_service_odometer: number | null;
    notes: string | null;
}

export type CreateServiceLogPayload = ServiceLogSchema;
export type UpdateServiceLogPayload = Partial<{
    date: string;
    odometer: number;
    service_center: string | null;
    total_cost: number;
    services_done: string[];
    next_service_date: string | null;
    next_service_odometer: number | null;
    notes: string | null;
}>;

export const serviceLogsApi = {
    getAll: async (
        vehicleId: string,
        params?: { cursor?: string; size?: number }
    ): Promise<CursorPage<ServiceLog>> => {
        const { data } = await apiClient.get("/service_logs/", {
            params: { vehicle_id: vehicleId, ...params },
        });
        return data;
    },

    create: async (
        vehicleId: string,
        payload: CreateServiceLogPayload
    ): Promise<ServiceLog> => {
        const { data } = await apiClient.post("/service_logs/", payload, {
            params: { vehicle_id: vehicleId },
        });
        return data;
    },

    update: async (
        vehicleId: string,
        logId: string,
        payload: UpdateServiceLogPayload
    ): Promise<ServiceLog> => {
        const { data } = await apiClient.patch(`/service_logs/${logId}`, payload, {
            params: { vehicle_id: vehicleId },
        });
        return data;
    },

    delete: async (vehicleId: string, logId: string): Promise<void> => {
        await apiClient.delete(`/service_logs/${logId}`, {
            params: { vehicle_id: vehicleId },
        });
    },

    exportCsv: async (vehicleId: string): Promise<Blob> => {
        const { data } = await apiClient.get("/service_logs/export", {
            params: { vehicle_id: vehicleId },
            responseType: "blob",
        });
        return data;
    },

    suggestNextDue: async (payload: {
        date: string;
        odometer: number;
        services_done: string[];
    }): Promise<{
        next_service_date: string | null;
        next_service_odometer: number | null;
        matched_tasks: string[];
    }> => {
        const { data } = await apiClient.post(
            "/service_logs/suggest-next-due",
            payload
        );
        return data;
    },
};

