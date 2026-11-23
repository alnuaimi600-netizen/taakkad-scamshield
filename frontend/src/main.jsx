import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
import { applySavedTheme } from "./theme.jsx";

applySavedTheme();

// The staff dashboard is a separate bundle, loaded only at /admin.
const Admin = lazy(() => import("./Admin.jsx"));
const isAdmin = window.location.pathname.startsWith("/admin");

createRoot(document.getElementById("root")).render(
  <StrictMode>
    {isAdmin ? (
      <Suspense fallback={null}>
        <Admin />
      </Suspense>
    ) : (
      <App />
    )}
  </StrictMode>,
);
