import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../../api/client";
import { ApiError } from "../../utils/errors";
import { ErrorDisplay } from "../../components/ErrorDisplay/ErrorDisplay";
import { LoadingSpinner } from "../../components/LoadingSpinner/LoadingSpinner";
import { EmptyState } from "../../components/EmptyState/EmptyState";
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import { ScoreCard } from "../../components/ScoreCard/ScoreCard";
import type { Analysis, Finding } from "../../types/api";
import styles from "./AnalysisResultPage.module.css";

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

function sortFindings(findings: Finding[]): Finding[] {
  return [...findings].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 5) - (SEVERITY_ORDER[b.severity] ?? 5)
  );
}

export function AnalysisResultPage() {
  const { id } = useParams<{ id: string }>();
  const analysisId = Number(id);

  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ statusCode?: number; error: unknown } | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAnalysis = useCallback(async () => {
    if (!analysisId) return;
    try {
      const data = await api.get<Analysis>(`/api/v1/analyses/${analysisId}`);
      setAnalysis(data);
      setIsLoading(false);

      if (data.status === "PENDING" || data.status === "RUNNING") {
        if (!pollingRef.current) {
          pollingRef.current = setInterval(async () => {
            try {
              const updated = await api.get<Analysis>(`/api/v1/analyses/${analysisId}`);
              setAnalysis(updated);
              if (updated.status === "COMPLETED" || updated.status === "FAILED") {
                if (pollingRef.current) {
                  clearInterval(pollingRef.current);
                  pollingRef.current = null;
                }
              }
            } catch {
              // polling error - keep trying
            }
          }, 3000);
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ statusCode: err.statusCode, error: err });
      } else {
        setError({ error: err });
      }
      setIsLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    fetchAnalysis();
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [fetchAnalysis]);

  if (error) {
    return (
      <ErrorDisplay
        statusCode={error.statusCode}
        error={error.error}
        onRetry={fetchAnalysis}
      />
    );
  }

  if (isLoading) {
    return <LoadingSpinner message="Memuat hasil analisis..." />;
  }

  if (!analysis) {
    return <EmptyState icon="❌" title="Analisis tidak ditemukan" />;
  }

  const isRunning = analysis.status === "PENDING" || analysis.status === "RUNNING";
  const scores = analysis.scores;
  const findings = analysis.findings as Finding[] | null;
  const recommendations = analysis.recommendations;
  const summary = analysis.summary as Record<string, unknown> | null;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link
          to={`/repositories/${analysis.repository_id}`}
          className={styles.backLink}
        >
          ← Kembali ke Repository
        </Link>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Analisis #{analysis.id}</h1>
          <StatusBadge status={analysis.status} />
        </div>
        <div className={styles.meta}>
          <span>Repository ID: {analysis.repository_id}</span>
          {analysis.created_at && (
            <span>
              Dibuat:{" "}
              {new Date(analysis.created_at).toLocaleDateString("id-ID", {
                day: "numeric",
                month: "long",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
          {analysis.completed_at && (
            <span>
              Selesai:{" "}
              {new Date(analysis.completed_at).toLocaleDateString("id-ID", {
                day: "numeric",
                month: "long",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
        </div>
      </div>

      {isRunning && (
        <div className={styles.runningBanner}>
          <div className={styles.runningSpinner} />
          <span>
            Analisis sedang diproses... Status: {analysis.status}
          </span>
        </div>
      )}

      {analysis.status === "FAILED" && analysis.error && (
        <div className={styles.errorBanner}>
          <div className={styles.errorTitle}>Analisis Gagal</div>
          <div className={styles.errorMessage}>{analysis.error.message}</div>
        </div>
      )}

      {analysis.status === "COMPLETED" && (
        <>
          {scores && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Skor</h2>
              <div className={styles.scoresGrid}>
                <ScoreCard label="Kualitas Kode" value={scores.code_quality ?? 0} />
                <ScoreCard label="Arsitektur" value={scores.architecture ?? 0} />
                <ScoreCard label="Kemudahan Perawatan" value={scores.maintainability ?? 0} />
              </div>
            </div>
          )}

          {summary && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Ringkasan</h2>
              <div className={styles.summaryGrid}>
                <div className={styles.summaryItem}>
                  <div className={styles.summaryValue}>{String((summary as Record<string, unknown>).total_files ?? 0)}</div>
                  <div className={styles.summaryLabel}>Total File</div>
                </div>
                <div className={styles.summaryItem}>
                  <div className={styles.summaryValue}>{String((summary as Record<string, unknown>).total_source_files ?? 0)}</div>
                  <div className={styles.summaryLabel}>Source File</div>
                </div>
                <div className={styles.summaryItem}>
                  <div className={styles.summaryValue}>{String((summary as Record<string, unknown>).total_lines ?? 0)}</div>
                  <div className={styles.summaryLabel}>Total Baris</div>
                </div>
                {typeof (summary as Record<string, unknown>).dominant_language === "string" && (
                  <div className={styles.summaryItem}>
                    <div className={styles.summaryValue}>
                      {String((summary as Record<string, unknown>).dominant_language)}
                    </div>
                    <div className={styles.summaryLabel}>Bahasa Utama</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {findings && findings.length > 0 && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>
                Temuan ({findings.length})
              </h2>
              <div className={styles.findingsList}>
                {sortFindings(findings).map((finding, idx) => (
                  <div key={idx} className={styles.findingCard}>
                    <div className={styles.findingHeader}>
                      <span
                        className={`${styles.findingSeverity} ${styles[finding.severity]}`}
                      >
                        {finding.severity}
                      </span>
                      <span className={styles.findingTitle}>{finding.title}</span>
                    </div>
                    <p className={styles.findingDescription}>{finding.description}</p>
                    {finding.file_path && (
                      <div className={styles.findingFile}>📄 {finding.file_path}</div>
                    )}
                    <div className={styles.findingRecommendation}>
                      💡 {finding.recommendation}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {recommendations && recommendations.length > 0 && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Rekomendasi</h2>
              <div className={styles.recommendationsList}>
                {recommendations.map((rec, idx) => (
                  <div key={idx} className={styles.recommendationItem}>
                    <span className={styles.recommendationBullet}>•</span>
                    {rec}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!scores && !findings && !recommendations && (
            <EmptyState
              icon="📋"
              title="Data hasil belum tersedia"
              description="Analisis selesai namun data skor/findings belum tersedia."
            />
          )}
        </>
      )}
    </div>
  );
}
