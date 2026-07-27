import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import { LoadingSpinner } from "../../components/LoadingSpinner/LoadingSpinner";
import { EmptyState } from "../../components/EmptyState/EmptyState";
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

  return (
    <div className={styles.page}>
      <div className={styles.welcome}>
        <h1 className={styles.welcomeTitle}>
          Selamat datang, {user?.email?.split("@")[0]}
        </h1>
        <p className={styles.welcomeText}>
          Kelola dan analisis repository GitHub Anda.
        </p>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>📦</div>
          <div className={styles.statInfo}>
            <div className={styles.statValue}>{stats?.repository_count ?? 0}</div>
            <div className={styles.statLabel}>Repositories</div>
          </div>
          <Link to="/repositories" className={styles.statLink}>
            Lihat semua
          </Link>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>🔍</div>
          <div className={styles.statInfo}>
            <div className={styles.statValue}>{stats?.analysis_count ?? 0}</div>
            <div className={styles.statLabel}>Total Analisis</div>
          </div>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Aktivitas Terbaru</h2>
        </div>

        {!stats || stats.recent_analyses.length === 0 ? (
          <EmptyState
            icon="📊"
            title="Belum ada aktivitas"
            description="Mulai dengan mendaftarkan repository atau menjalankan analisis."
            action={
              <Link to="/repositories" className={styles.primaryButton}>
                Mulai Sekarang
              </Link>
            }
          />
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

      {stats && stats.repository_count > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Aksi Cepat</h2>
          </div>
          <div className={styles.actions}>
            <Link to="/repositories" className={styles.actionButton}>
              <span className={styles.actionIcon}>📦</span>
              <span className={styles.actionText}>Lihat Repositories</span>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
