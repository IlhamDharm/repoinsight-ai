import styles from "./ScoreCard.module.css";

interface ScoreCardProps {
  label: string;
  value: number;
  max?: number;
}

function getScoreColor(value: number): string {
  if (value >= 80) return styles.good;
  if (value >= 60) return styles.fair;
  if (value >= 40) return styles.poor;
  return styles.critical;
}

export function ScoreCard({ label, value, max = 100 }: ScoreCardProps) {
  const pct = Math.round((value / max) * 100);
  const colorClass = getScoreColor(pct);

  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={`${styles.value} ${colorClass}`}>{value}</div>
      <div className={styles.bar}>
        <div
          className={`${styles.fill} ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
