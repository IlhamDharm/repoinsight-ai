import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import { LoadingSpinner } from "../../components/LoadingSpinner/LoadingSpinner";
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import type { DashboardStats } from "../../types/api";
import styles from "./DashboardPage.module.css";

const LINE_CHART_POINTS = [
  { day: "1 Jul", value: 12 },
  { day: "5 Jul", value: 19 },
  { day: "10 Jul", value: 8 },
  { day: "15 Jul", value: 25 },
  { day: "20 Jul", value: 18 },
  { day: "25 Jul", value: 32 },
  { day: "28 Jul", value: 28 },
];

const LANGUAGES = [
  { name: "TypeScript", pct: 38, color: "#3178C6" },
  { name: "Python", pct: 28, color: "#3776AB" },
  { name: "JavaScript", pct: 18, color: "#F7DF1E" },
  { name: "CSS", pct: 10, color: "#264DE4" },
  { name: "Lainnya", pct: 6, color: "#64748B" },
];

function getScoreColor(score: number): string {
  if (score >= 80) return "var(--success)";
  if (score >= 60) return "var(--accent)";
  if (score >= 40) return "var(--warning)";
  return "var(--error)";
}

function getRepoInitial(name: string): string {
  return name.charAt(0).toUpperCase();
}

function getRepoColor(name: string): string {
  const colors = ["#3B82F6", "#A855F7", "#22C55E", "#F59E0B", "#EF4444", "#EC4899"];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

export function DashboardPage() {
  const user = { email: "demo@repoinsight.local" };
  const navigate = useNavigate();
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
  const completedCount = stats?.recent_analyses?.filter((a) => a.status === "COMPLETED").length ?? 0;
  const runningCount = stats?.recent_analyses?.filter((a) => a.status === "RUNNING" || a.status === "PENDING").length ?? 0;

  const maxChartValue = Math.max(...LINE_CHART_POINTS.map((p) => p.value));

  return (
    <div className={styles.page}>
      {/* ── Greeting + CTA ── */}
      <div className={styles.greetingRow}>
        <div className={styles.greeting}>
          <p className={styles.greetingText}>Dashboard</p>
          <h1 className={styles.greetingName}>Selamat datang, {displayName}</h1>
        </div>
        <button
          className={styles.ctaButton}
          onClick={() => navigate("/repositories")}
          type="button"
        >
          <span className={styles.ctaPlus}>+</span>
          Analisis Repository
        </button>
      </div>

      {/* ── Metric Cards ── */}
      <div className={styles.metricsGrid}>
        <div className={`${styles.metricCard} ${styles.metricBorderRepos}`}>
          <div className={styles.metricTop}>
            <div className={`${styles.metricIcon} ${styles.metricIconRepos}`}>📦</div>
            <span className={`${styles.metricTrend} ${styles.trendPositive}`}>↑ 3</span>
          </div>
          <div className={styles.metricValue}>{stats?.repository_count ?? 0}</div>
          <div className={styles.metricLabel}>Repositories</div>
        </div>

        <div className={`${styles.metricCard} ${styles.metricBorderAnalyses}`}>
          <div className={styles.metricTop}>
            <div className={`${styles.metricIcon} ${styles.metricIconAnalyses}`}>📊</div>
            <span className={`${styles.metricTrend} ${styles.trendPositive}`}>↑ 8</span>
          </div>
          <div className={styles.metricValue}>{stats?.analysis_count ?? 0}</div>
          <div className={styles.metricLabel}>Total Analisis</div>
        </div>

        <div className={`${styles.metricCard} ${styles.metricBorderCompleted}`}>
          <div className={styles.metricTop}>
            <div className={`${styles.metricIcon} ${styles.metricIconCompleted}`}>✅</div>
            <span className={`${styles.metricTrend} ${styles.trendPositive}`}>↑ 5</span>
          </div>
          <div className={styles.metricValue}>{completedCount}</div>
          <div className={styles.metricLabel}>Selesai</div>
        </div>

        <div className={`${styles.metricCard} ${styles.metricBorderRunning}`}>
          <div className={styles.metricTop}>
            <div className={`${styles.metricIcon} ${styles.metricIconRunning}`}>⏳</div>
            <span className={`${styles.metricTrend} ${styles.trendNegative}`}>↓ 1</span>
          </div>
          <div className={styles.metricValue}>{runningCount}</div>
          <div className={styles.metricLabel}>Berjalan</div>
        </div>
      </div>

      {/* ── Charts Section ── */}
      <div className={styles.chartsGrid}>
        {/* Line Chart */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <h3 className={styles.chartTitle}>Aktivitas Analisis (30 Hari Terakhir)</h3>
            <span className={styles.chartBadge}>Live</span>
          </div>
          <div className={styles.lineChart}>
            <div className={styles.lineChartYAxis}>
              <span>{maxChartValue}</span>
              <span>{Math.round(maxChartValue * 0.5)}</span>
              <span>0</span>
            </div>
            <div className={styles.lineChartArea}>
              <svg viewBox="0 0 280 100" className={styles.lineChartSvg} preserveAspectRatio="none">
                <defs>
                  <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--purple)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="var(--purple)" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <polygon
                  points={LINE_CHART_POINTS.map((p, i) => {
                    const x = (i / (LINE_CHART_POINTS.length - 1)) * 280;
                    const y = 100 - (p.value / maxChartValue) * 85;
                    return `${x},${y}`;
                  }).join(" ") + " 280,100 0,100"}
                  fill="url(#lineGrad)"
                />
                <polyline
                  points={LINE_CHART_POINTS.map((p, i) => {
                    const x = (i / (LINE_CHART_POINTS.length - 1)) * 280;
                    const y = 100 - (p.value / maxChartValue) * 85;
                    return `${x},${y}`;
                  }).join(" ")}
                  fill="none"
                  stroke="var(--purple)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {LINE_CHART_POINTS.map((p, i) => {
                  const x = (i / (LINE_CHART_POINTS.length - 1)) * 280;
                  const y = 100 - (p.value / maxChartValue) * 85;
                  return (
                    <circle key={i} cx={x} cy={y} r="3.5" fill="var(--bg-primary)" stroke="var(--purple)" strokeWidth="2" />
                  );
                })}
              </svg>
              <div className={styles.lineChartLabels}>
                {LINE_CHART_POINTS.map((p, i) => (
                  <span key={i}>{p.day}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Donut Chart */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <h3 className={styles.chartTitle}>Bahasa Teratas</h3>
          </div>
          <div className={styles.donutSection}>
            <div className={styles.donutChart}>
              <svg viewBox="0 0 120 120" className={styles.donutSvg}>
                {(() => {
                  let cumulative = 0;
                  const radius = 42;
                  const circumference = 2 * Math.PI * radius;
                  return LANGUAGES.map((lang, i) => {
                    const offset = (cumulative / 100) * circumference;
                    const length = (lang.pct / 100) * circumference;
                    cumulative += lang.pct;
                    return (
                      <circle
                        key={i}
                        cx="60"
                        cy="60"
                        r={radius}
                        fill="none"
                        stroke={lang.color}
                        strokeWidth="14"
                        strokeDasharray={`${length} ${circumference - length}`}
                        strokeDashoffset={-offset}
                        strokeLinecap="butt"
                        style={{ transition: "stroke-dasharray 0.6s ease" }}
                      />
                    );
                  });
                })()}
              </svg>
              <div className={styles.donutCenter}>
                <span className={styles.donutCenterValue}>{LANGUAGES.length}</span>
                <span className={styles.donutCenterLabel}>Bahasa</span>
              </div>
            </div>
            <div className={styles.donutLegend}>
              {LANGUAGES.map((lang, i) => (
                <div key={i} className={styles.legendItem}>
                  <span className={styles.legendDot} style={{ background: lang.color }} />
                  <span className={styles.legendName}>{lang.name}</span>
                  <span className={styles.legendPct}>{lang.pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Recent Activity ── */}
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
            <div className={styles.emptyState}>
              <p className={styles.emptyText}>
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
                <div
                  className={styles.activityAvatar}
                  style={{ background: getRepoColor(item.repository_name) }}
                >
                  {getRepoInitial(item.repository_name)}
                </div>
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
                  {item.score !== null && item.status === "COMPLETED" && (
                    <div className={styles.scoreBadge}>
                      <svg viewBox="0 0 36 36" className={styles.scoreRing}>
                        <circle
                          cx="18"
                          cy="18"
                          r="15.915"
                          fill="none"
                          stroke="var(--border-primary)"
                          strokeWidth="3"
                        />
                        <circle
                          cx="18"
                          cy="18"
                          r="15.915"
                          fill="none"
                          stroke={getScoreColor(item.score)}
                          strokeWidth="3"
                          strokeDasharray={`${item.score} ${100 - item.score}`}
                          strokeDashoffset="25"
                          strokeLinecap="round"
                        />
                      </svg>
                      <span className={styles.scoreValue} style={{ color: getScoreColor(item.score) }}>
                        {item.score}
                      </span>
                    </div>
                  )}
                  <StatusBadge status={item.status as "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
