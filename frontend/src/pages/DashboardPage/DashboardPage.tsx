import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import { LoadingSpinner } from "../../components/LoadingSpinner/LoadingSpinner";
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import { useAuth } from "../../context/AuthContext";
import type { DashboardStats } from "../../types/api";
import styles from "./DashboardPage.module.css";

export function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ statusCode?: number; error: unknown } | null>(null);

  const fetchStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiRequest<DashboardStats>("/api/v1/dashboard/stats");
      setStats(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ statusCode: err.statusCode, error: err });
      } else {
        setError({ error: err });
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (error) {
    return (
      <ErrorDisplay
        statusCode={error.statusCode}
        error={error.error}
        onRetry={fetchStats}
      />
    );
  }

  if (isLoading) {
    return <LoadingSpinner message="Memuat dashboard..." />;
  }

  const displayName = user?.email?.split("@")[0] || "User";

  return (
    <div className={styles.page}>
      <div className={styles.greeting}>
        <p className={styles.greetingText}>Dashboard</p>
        <h1 className={styles.greetingName}>Selamat datang, {displayName}</h1>
      </div>

      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>{stats?.repository_count ?? 0}</div>
          <div className={styles.metricLabel}>Repositories</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>{stats?.analysis_count ?? 0}</div>
          <div className={styles.metricLabel}>Analisis Selesai</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>
            {stats?.recent_analyses?.filter((a) => a.status === "RUNNING").length ?? 0}
          </div>
          <div className={styles.metricLabel}>Sedang Berjalan</div>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Aktivitas Terbaru</h2>
          {stats && stats.recent_analyses.length > 0 && (
            <Link to="/repositories" className={styles.sectionLink}>
              Lihat semua →
            </Link>
          )}
        </div>

        {!stats || stats.recent_analyses.length === 0 ? (
          <div className={styles.activityList}>
            <div style={{ padding: "var(--space-8)", textAlign: "center" }}>
              <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)", marginBottom: "var(--space-4)" }}>
                Belum ada aktivitas analisis.
              </p>
              <div className={styles.emptyActions}>
                <Link to="/repositories" className={styles.emptyButton}>
                  Lihat Repositories
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.activityList}>
            {stats.recent_analyses.map((item) => (
              <Link
                key={item.id}
                to={`/analyses/${item.id}`}
                className={styles.activityItem}
              >
                <div className={styles.activityInfo}>
                  <div className={styles.activityRepo}>{item.repository_name}</div>
                  <div className={styles.activityTime}>
                    {item.created_at
                      ? new Date(item.created_at).toLocaleDateString("id-ID", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "-"}
                  </div>
                </div>
                <div className={styles.activityRight}>
                  {item.score !== null && (
                    <span className={styles.activityScore}>{item.score}</span>
                  )}
                  <StatusBadge status={item.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
