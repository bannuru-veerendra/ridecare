import { lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";

import ErrorBoundary from "@/components/common/ErrorBoundary";
import ProtectedRoute from "@/components/common/ProtectedRoute";
import AppLayout from "@/components/common/AppLayout";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import CheckEmailPage from "@/pages/CheckEmailPage";
import VerifyEmailPage from "@/pages/VerifyEmailPage";
import NotFoundPage from "@/pages/NotFoundPage";

const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const VehiclesPage = lazy(() => import("@/pages/VehiclesPage"));
const VehicleDetailPage = lazy(() => import("@/pages/VehicleDetailPage"));
const ComparePage = lazy(() => import("@/pages/ComparePage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));
const MaintenanceGuidelinesPage = lazy(
    () => import("@/pages/MaintenanceGuidelinesPage")
);

/**
 * Root application component.
 * Defines all client-side routes.
 * Auth pages stay eager; the rest of the app is code-split so the first
 * login/register interaction is not blocked by dashboard or chart code.
 */
export default function App() {
    return (
        <ErrorBoundary>
            <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />

                {/* Public routes */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/check-email" element={<CheckEmailPage />} />
                <Route path="/verify-email" element={<VerifyEmailPage />} />

                {/* Protected routes — all share AppLayout */}
                <Route element={<ProtectedRoute />}>
                    <Route element={<AppLayout />}>
                        <Route path="/dashboard" element={<ErrorBoundary><DashboardPage /></ErrorBoundary>} />
                        <Route path="/vehicles" element={<ErrorBoundary><VehiclesPage /></ErrorBoundary>} />
                        <Route path="/vehicles/:id" element={<ErrorBoundary><VehicleDetailPage /></ErrorBoundary>} />
                        <Route path="/compare" element={<ErrorBoundary><ComparePage /></ErrorBoundary>} />
                        <Route path="/settings" element={<ErrorBoundary><SettingsPage /></ErrorBoundary>} />
                        <Route path="/maintenance" element={<ErrorBoundary><MaintenanceGuidelinesPage /></ErrorBoundary>} />
                    </Route>
                </Route>

                <Route path="*" element={<NotFoundPage />} />
            </Routes>

            <Toaster position="top-right" richColors />
        </ErrorBoundary>
    );
}
