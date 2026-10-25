import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./components/Toast/Toast";
import { ErrorBoundary } from "./components/ErrorBoundary/ErrorBoundary";
import { ProtectedRoute } from "./components/ProtectedRoute/ProtectedRoute";
import { Layout } from "./components/Layout/Layout";
import { LoginPage } from "./pages/LoginPage/LoginPage";
import { DashboardPage } from "./pages/DashboardPage/DashboardPage";
import { RepositoriesPage } from "./pages/RepositoriesPage/RepositoriesPage";
import { RepositoryDetailPage } from "./pages/RepositoryDetailPage/RepositoryDetailPage";
import { AnalysisResultPage } from "./pages/AnalysisResultPage/AnalysisResultPage";
import { NotFoundPage } from "./pages/NotFoundPage/NotFoundPage";

export default function App() {
  const authDisabled = import.meta.env.VITE_AUTH_ENABLED !== "true";

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <Routes>
              <Route
                path="/login"
                element={authDisabled ? <Navigate to="/dashboard" replace /> : <LoginPage />}
              />
              <Route
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }
              >
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/repositories" element={<RepositoriesPage />} />
                <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
                <Route path="/analyses/:id" element={<AnalysisResultPage />} />
                <Route index element={<Navigate to="/dashboard" replace />} />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
