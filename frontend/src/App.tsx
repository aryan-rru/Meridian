import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Controls } from "./pages/Controls";
import { Crosswalk } from "./pages/Crosswalk";
import { Coverage } from "./pages/Coverage";
import { Risks } from "./pages/Risks";
import { RiskDetail } from "./pages/RiskDetail";
import { RiskHeatmap } from "./pages/RiskHeatmap";
import { Remediation } from "./pages/Remediation";
import { Evidence } from "./pages/Evidence";
import { Settings } from "./pages/Settings";
import { ImportExport } from "./pages/ImportExport";
import { NotFound } from "./pages/NotFound";
import { ToastProvider } from "./components/feedback/Toast";

export const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="controls" element={<Controls />} />
        <Route path="crosswalk" element={<Crosswalk />} />
        <Route path="coverage" element={<Coverage />} />
        <Route path="risks" element={<Risks />} />
        <Route path="risks/:id" element={<RiskDetail />} />
        <Route path="risk-heatmap" element={<RiskHeatmap />} />
        <Route path="remediation" element={<Remediation />} />
        <Route path="evidence" element={<Evidence />} />
        <Route path="settings" element={<Settings />} />
        <Route path="import-export" element={<ImportExport />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={defaultQueryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
