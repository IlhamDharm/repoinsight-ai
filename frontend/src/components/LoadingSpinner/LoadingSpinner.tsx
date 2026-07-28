import styles from "./LoadingSpinner.module.css";

interface LoadingSpinnerProps {
  message?: string;
  fullScreen?: boolean;
}

export function LoadingSpinner({ message, fullScreen }: LoadingSpinnerProps) {
  if (fullScreen) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        {message && <p>{message}</p>}
      </div>
    );
  }

  return (
    <div className={styles.container} role="status">
      <div className={styles.spinner} />
      {message && <p className={styles.message}>{message}</p>}
    </div>
  );
}
