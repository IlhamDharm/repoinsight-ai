import type { AnalysisStatus } from "../../types/api";
import styles from "./StatusBadge.module.css";

interface StatusBadgeProps {
  status: AnalysisStatus | string;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  PENDING: { label: "Menunggu", className: styles.pending },
  RUNNING: { label: "Berjalan", className: styles.running },
  COMPLETED: { label: "Selesai", className: styles.completed },
  FAILED: { label: "Gagal", className: styles.failed },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || { label: status, className: "" };

  return (
    <span className={`${styles.badge} ${config.className}`}>
      {status === "RUNNING" && <span className={styles.dot} />}
      {config.label}
    </span>
  );
}
