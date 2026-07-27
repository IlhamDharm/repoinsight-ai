import { useCallback, useEffect, useState } from "react";
import { apiRequestFull } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import type { Repository } from "../../types/api";
import styles from "./RepositoriesPage.module.css";

export function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ statusCode?: number; error: unknown } | null>(null);

  const fetchRepositories = useCallback(async (pageNum: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiRequestFull<Repository[]>(
        `/api/v1/repositories?page=${pageNum}&page_size=10`,
      );
      setRepositories(result.data);
      if (result.meta.total_pages) {
        setTotalPages(result.meta.total_pages);
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
  }, []);

  useEffect(() => {
    fetchRepositories(page);
  }, [page, fetchRepositories]);

  if (error) {
    return (
      <ErrorDisplay
        statusCode={error.statusCode}
        error={error.error}
        onRetry={() => fetchRepositories(page)}
      />
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Repositories</h1>
      </div>

      {isLoading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Memuat repositories...</p>
        </div>
      ) : repositories.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📦</div>
          <h3 className={styles.emptyTitle}>Belum ada repositories</h3>
          <p className={styles.emptyText}>
            Daftarkan repository GitHub pertama Anda untuk memulai analisis.
          </p>
        </div>
      ) : (
        <>
          <div className={styles.grid}>
            {repositories.map((repo) => (
              <div key={repo.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <h3 className={styles.repoName}>{repo.name}</h3>
                  <span
                    className={`${styles.badge} ${
                      repo.visibility === "public"
                        ? styles.badgePublic
                        : styles.badgePrivate
                    }`}
                  >
                    {repo.visibility}
                  </span>
                </div>
                <p className={styles.fullName}>{repo.full_name}</p>
                <div className={styles.cardMeta}>
                  <span>Branch: {repo.default_branch}</span>
                  <a
                    href={repo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.link}
                  >
                    Buka di GitHub
                  </a>
                </div>
              </div>
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
  );
}
