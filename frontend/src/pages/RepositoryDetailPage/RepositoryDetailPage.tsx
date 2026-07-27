import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, apiRequestFull } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import { LoadingSpinner } from "../../components/LoadingSpinner/LoadingSpinner";
import { EmptyState } from "../../components/EmptyState/EmptyState";
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import type {
  Repository,
  AnalysisHistoryItem,
  AnalysisJobResponse,
} from "../../types/api";
import styles from "./RepositoryDetailPage.module.css";

export function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const repoId = Number(id);

  const [repository, setRepository] = useState<Repository | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisHistoryItem[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ statusCode?: number; error: unknown } | null>(null);

  const [isStartingAnalysis, setIsStartingAnalysis] = useState(false);
  const [analysisMessage, setAnalysisMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!repoId) return;
    setIsLoading(true);
    setError(null);
    try {
      const repo = await api.get<Repository>(`/api/v1/repositories/${repoId}`);
      setRepository(repo);

      const analysesResult = await apiRequestFull<AnalysisHistoryItem[]>(
        `/api/v1/repositories/${repoId}/analyses?page=${page}&page_size=5`
      );
      setAnalyses(analysesResult.data);
      if (analysesResult.meta.total_pages) {
        setTotalPages(analysesResult.meta.total_pages);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ statusCode: err.statusCode, error: err });
      } else {
        setError({ error: err });
      }
    } finally {
      setIsLoading(false);
    }
  }, [repoId, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAnalyze = async () => {
    if (!repoId) return;
    setIsStartingAnalysis(true);
    setAnalysisMessage(null);
    setError(null);
    try {
      const result = await api.post<AnalysisJobResponse>(
        `/api/v1/repositories/${repoId}/analyze`
      );
      setAnalysisMessage(`Analisis #${result.analysis_id} berhasil dijadwalkan. Status: ${result.status}`);
      await fetchData();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = err.message;
        if (err.statusCode === 409) {
          setAnalysisMessage(msg);
        } else {
          setError({ statusCode: err.statusCode, error: err });
        }
      } else {
        setError({ error: err });
      }
    } finally {
      setIsStartingAnalysis(false);
    }
  };

  if (error) {
    return (
      <ErrorDisplay
        statusCode={error.statusCode}
        error={error.error}
        onRetry={fetchData}
      />
    );
  }

  if (isLoading) {
    return <LoadingSpinner message="Memuat repository..." />;
  }

  if (!repository) {
    return <EmptyState icon="❌" title="Repository tidak ditemukan" />;
  }

  return (
    <div className={styles.page}>
      <nav className={styles.breadcrumb}>
        <Link to="/repositories" className={styles.breadcrumbLink}>Repositories</Link>
        <span className={styles.breadcrumbSep}>/</span>
        <span className={styles.breadcrumbCurrent}>{repository.name}</span>
      </nav>

      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{repository.name}</h1>
          <span
            className={`${styles.badge} ${
              repository.visibility === "public"
                ? styles.badgePublic
                : styles.badgePrivate
            }`}
          >
            {repository.visibility}
          </span>
        </div>
        <p className={styles.fullName}>{repository.full_name}</p>
        <div className={styles.meta}>
          <span>Branch: {repository.default_branch}</span>
          <a
            href={repository.url}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.link}
          >
            Buka di GitHub ↗
          </a>
        </div>
      </div>

      <div className={styles.actions}>
        <button
          className={styles.analyzeButton}
          onClick={handleAnalyze}
          disabled={isStartingAnalysis}
        >
          {isStartingAnalysis ? "Menjadwalkan..." : "Mulai Analisis Baru"}
        </button>
      </div>

      {analysisMessage && (
        <div className={styles.message}>{analysisMessage}</div>
      )}

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Riwayat Analisis</h2>

        {analyses.length === 0 ? (
          <EmptyState
            icon="📊"
            title="Belum ada analisis"
            description="Klik 'Mulai Analisis Baru' untuk menjalankan analisis pertama."
          />
        ) : (
          <>
            <div className={styles.analysisList}>
              {analyses.map((item) => (
                <Link
                  key={item.id}
                  to={`/analyses/${item.id}`}
                  className={styles.analysisItem}
                >
                  <div className={styles.analysisInfo}>
                    <div className={styles.analysisId}>Analisis #{item.id}</div>
                    <div className={styles.analysisTime}>
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
                  <div className={styles.analysisRight}>
                    {item.score !== null && (
                      <span className={styles.analysisScore}>{item.score}</span>
                    )}
                    <StatusBadge status={item.status} />
                  </div>
                </Link>
              ))}
            </div>

            {totalPages > 1 && (
              <div className={styles.pagination}>
                <button
                  className={styles.pageButton}
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Sebelumnya
                </button>
                <span className={styles.pageInfo}>
                  Halaman {page} dari {totalPages}
                </span>
                <button
                  className={styles.pageButton}
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Selanjutnya
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
