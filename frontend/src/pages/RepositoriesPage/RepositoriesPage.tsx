import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequestFull } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import { LoadingSpinner } from "../../components/LoadingSpinner/LoadingSpinner";
import { EmptyState } from "../../components/EmptyState/EmptyState";
import type { Repository } from "../../types/api";
import styles from "./RepositoriesPage.module.css";

export function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ statusCode?: number; error: unknown } | null>(null);

  const [registerUrl, setRegisterUrl] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registerSuccess, setRegisterSuccess] = useState<string | null>(null);

  const fetchRepositories = useCallback(async (pageNum: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiRequestFull<Repository[]>(
        `/api/v1/repositories?page=${pageNum}&page_size=10`
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

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!registerUrl.trim()) return;
    setIsRegistering(true);
    setRegisterError(null);
    setRegisterSuccess(null);
    try {
      const repo = await apiRequestFull<Repository>("/api/v1/repositories", {
        method: "POST",
        body: { url: registerUrl.trim() },
      });
      setRegisterSuccess(`Repository "${repo.data.name}" berhasil didaftarkan.`);
      setRegisterUrl("");
      await fetchRepositories(1);
      setPage(1);
    } catch (err) {
      if (err instanceof ApiError) {
        setRegisterError(err.message);
      } else {
        setRegisterError("Gagal mendaftarkan repository.");
      }
    } finally {
      setIsRegistering(false);
    }
  };

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

      <div className={styles.registerSection}>
        <h3 className={styles.registerTitle}>Daftarkan Repository</h3>
        <form onSubmit={handleRegister} className={styles.registerForm}>
          <input
            type="url"
            className={styles.registerInput}
            value={registerUrl}
            onChange={(e) => setRegisterUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            required
            disabled={isRegistering}
          />
          <button
            type="submit"
            className={styles.registerButton}
            disabled={isRegistering || !registerUrl.trim()}
          >
            {isRegistering ? "Mendaftarkan..." : "Daftarkan"}
          </button>
        </form>
        {registerError && <div className={styles.registerError}>{registerError}</div>}
        {registerSuccess && <div className={styles.registerSuccess}>{registerSuccess}</div>}
      </div>

      {isLoading ? (
        <LoadingSpinner message="Memuat repositories..." />
      ) : repositories.length === 0 ? (
        <EmptyState
          icon="📦"
          title="Belum ada repositories"
          description="Daftarkan repository GitHub pertama Anda untuk memulai analisis."
        />
      ) : (
        <>
          <div className={styles.grid}>
            {repositories.map((repo) => (
              <Link
                key={repo.id}
                to={`/repositories/${repo.id}`}
                className={styles.card}
              >
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
                  <span className={styles.viewDetail}>Lihat Detail →</span>
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
  );
}
