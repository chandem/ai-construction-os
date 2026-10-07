import React from "react";

type Props = { children: React.ReactNode };
type State = { error: Error | null };

/** Prevent a full blank white screen when any child throws. */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("UI crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, fontFamily: "system-ui, sans-serif", background: "#f3f5f7", color: "#15202b" }}>
          <div style={{ maxWidth: 420, background: "#fff", border: "1px solid #e2e7eb", borderRadius: 16, padding: 24 }}>
            <h1 style={{ margin: "0 0 8px", fontSize: 18 }}>Something went wrong</h1>
            <p style={{ margin: "0 0 12px", color: "#5f6b76", fontSize: 14, lineHeight: 1.5 }}>
              The app hit a display error instead of a blank page. Reload, or sign out and try again.
            </p>
            <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12, background: "#f1f4f6", padding: 12, borderRadius: 8, margin: "0 0 16px" }}>
              {this.state.error.message || String(this.state.error)}
            </pre>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{ width: "100%", padding: "12px 14px", border: 0, borderRadius: 10, background: "#15202b", color: "#fff", fontWeight: 700 }}
            >
              Reload app
            </button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
