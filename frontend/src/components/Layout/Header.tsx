import { useAuth } from "../../context/AuthContext";
import styles from "./Header.module.css";

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header className={styles.header}>
      <div className={styles.spacer} />
      <div className={styles.userArea}>
        <span className={styles.email}>{user?.email}</span>
        <button className={styles.logoutButton} onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  );
}
