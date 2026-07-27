import { useAuth } from "../../context/AuthContext";
import styles from "./Header.module.css";

export function Header() {
  const { user, logout } = useAuth();
  const initial = user?.email?.charAt(0).toUpperCase() || "?";

  return (
    <header className={styles.header}>
      <div className={styles.spacer} />
      <div className={styles.userArea}>
        <span className={styles.email}>{user?.email}</span>
        <div className={styles.avatar}>{initial}</div>
        <button className={styles.logoutButton} onClick={logout}>
          Keluar
        </button>
      </div>
    </header>
  );
}
