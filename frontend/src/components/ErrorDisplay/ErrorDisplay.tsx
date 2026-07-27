import { getErrorMessage, getErrorTitle } from "../../utils/errors";
import styles from "./ErrorDisplay.module.css";

interface ErrorDisplayProps {
  statusCode?: number;
  error: unknown;
  onRetry?: () => void;
}

export function ErrorDisplay({ statusCode, error, onRetry }: ErrorDisplayProps) {
  const title = statusCode ? getErrorTitle(statusCode) : "Kesalahan";
  const message = getErrorMessage(error);

  return (
    <div className={styles.container}>
      <div className={styles.icon}>!</div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.message}>{message}</p>
      {onRetry && (
        <button className={styles.retryButton} onClick={onRetry}>
          Coba Lagi
        </button>
      )}
    </div>
  );
}
