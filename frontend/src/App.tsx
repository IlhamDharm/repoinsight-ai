import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastProvider } from "./components/Toast/Toast";
import { ErrorBoundary } from "./components/ErrorBoundary/ErrorBoundary";
import { Layout } from "./components/Layout/Layout";
import { DashboardPage } from "./pages/DashboardPage/DashboardPage";
import { RepositoriesPage } from "./pages/RepositoriesPage/RepositoriesPage";
import { RepositoryDetailPage } from "./pages/RepositoryDetailPage/RepositoryDetailPage";
import { AnalysisResultPage } from "./pages/AnalysisResultPage/AnalysisResultPage";
import { NotFoundPage } from "./pages/NotFoundPage/NotFoundPage";

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/repositories" element={<RepositoriesPage />} />
              <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
              <Route path="/analyses/:id" element={<AnalysisResultPage />} />
              <Route index element={<Navigate to="/dashboard" replace />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
