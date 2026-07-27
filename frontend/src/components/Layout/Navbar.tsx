import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import styles from "./Navbar.module.css";

export function Navbar() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const initial = user?.email?.charAt(0).toUpperCase() || "?";

  const closeMobile = () => setMobileOpen(false);

  return (
    <nav className={styles.navbar}>
      <div className={styles.inner}>
        {/* LEFT — Logo */}
        <NavLink to="/dashboard" className={styles.brand} onClick={closeMobile}>
          <span className={styles.logoIcon}>R</span>
          <span className={styles.logoText}>RepoInsight</span>
        </NavLink>

        {/* CENTER — Nav links (desktop) */}
        <div className={`${styles.navLinks} ${mobileOpen ? styles.open : ""}`}>
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `${styles.navLink} ${isActive ? styles.active : ""}`
            }
            onClick={closeMobile}
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/repositories"
            className={({ isActive }) =>
              `${styles.navLink} ${isActive ? styles.active : ""}`
            }
            onClick={closeMobile}
          >
            Repositories
          </NavLink>
        </div>

        {/* RIGHT — User + Logout */}
        <div className={styles.userArea}>
          <div className={styles.avatar}>{initial}</div>
          <span className={styles.email}>{user?.email}</span>
          <button className={styles.logoutButton} onClick={logout}>
            Keluar
          </button>
        </div>

        {/* Mobile toggle */}
        <button
          className={`${styles.hamburger} ${mobileOpen ? styles.hamburgerOpen : ""}`}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle navigation"
        >
          <span className={styles.hamburgerLine} />
          <span className={styles.hamburgerLine} />
          <span className={styles.hamburgerLine} />
        </button>
      </div>
    </nav>
  );
}
