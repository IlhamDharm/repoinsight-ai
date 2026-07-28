import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{ padding: "var(--space-12)", textAlign: "center" }}>
          <div style={{ fontSize: "3rem", marginBottom: "var(--space-4)" }}>⚠️</div>
          <h2 style={{ color: "var(--text-primary)", fontSize: "var(--text-lg)", marginBottom: "var(--space-2)" }}>
            Terjadi kesalahan
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)", marginBottom: "var(--space-6)" }}>
            {this.state.error?.message || "Komponen mengalami error yang tidak terduga."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = "/dashboard";
            }}
            style={{
              padding: "var(--space-2) var(--space-5)",
              background: "var(--gradient-accent)",
              color: "white",
              border: "none",
              borderRadius: "var(--radius-lg)",
              fontSize: "var(--text-sm)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Kembali ke Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
