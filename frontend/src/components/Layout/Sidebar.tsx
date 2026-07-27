import { NavLink } from "react-router-dom";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <span className={styles.logoIcon}>R</span>
        <span className={styles.logoText}>RepoInsight</span>
      </div>
      <nav className={styles.nav}>
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.active : ""}`
          }
        >
          <span className={styles.navIcon}>📊</span>
          Dashboard
        </NavLink>
        <NavLink
          to="/repositories"
          className={({ isActive }) =>
            `${styles.navLink} ${isActive ? styles.active : ""}`
          }
        >
          <span className={styles.navIcon}>📦</span>
          Repositories
        </NavLink>
      </nav>
    </aside>
  );
}
