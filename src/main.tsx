import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "./sign-out.css";
import "./polish.css";
import { App } from "./App";
import { ErrorBoundary } from "./ErrorBoundary";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("Root element #root was not found in index.html");
}

createRoot(rootEl).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
