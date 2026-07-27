import { Link } from "react-router-dom";
import styles from "./NotFoundPage.module.css";

export function NotFoundPage() {
  return (
    <div className={styles.page}>
      <div className={styles.code}>404</div>
      <h1 className={styles.title}>Halaman Tidak Ditemukan</h1>
      <p className={styles.text}>Halaman yang Anda cari tidak tersedia.</p>
      <Link to="/dashboard" className={styles.link}>
        Kembali ke Dashboard
      </Link>
    </div>
  );
}
