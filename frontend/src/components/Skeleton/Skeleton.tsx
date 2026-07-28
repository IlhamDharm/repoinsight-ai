import styles from "./Skeleton.module.css";

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  lines?: number;
}

export function Skeleton({ width, height = "1rem", borderRadius, lines = 1 }: SkeletonProps) {
  if (lines > 1) {
    return (
      <div className={styles.lines}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={styles.line}
            style={{
              width: i === lines - 1 ? "60%" : "100%",
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={styles.skeleton}
      style={{ width, height, borderRadius }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <Skeleton width="60%" height="1rem" />
        <Skeleton width="48px" height="20px" borderRadius="var(--radius-full)" />
      </div>
      <Skeleton width="40%" height="0.75rem" />
      <div className={styles.cardFooter}>
        <Skeleton width="80px" height="0.75rem" />
      </div>
    </div>
  );
}
