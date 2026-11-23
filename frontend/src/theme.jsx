// Light/dark theme. Default follows the device; the user's choice is kept on this device only.
import { useState } from "react";
import { load, save } from "./storage.js";

const systemDark = () => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;

export function currentTheme() {
  const saved = load("theme");
  return saved === "light" || saved === "dark" ? saved : systemDark() ? "dark" : "light";
}

export function applySavedTheme() {
  const saved = load("theme");
  if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
}

export function useTheme() {
  const [theme, setTheme] = useState(currentTheme);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    save("theme", next);
    setTheme(next);
  };
  return [theme, toggle];
}

export function ThemeToggle({ t }) {
  const [theme, toggle] = useTheme();
  const label = theme === "dark" ? t.themeLight : t.themeDark;
  return (
    <button className="link theme-toggle" onClick={toggle} aria-label={label} title={label}>
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
