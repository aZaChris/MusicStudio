"use client";

import { useEffect, useState } from "react";

export function ThemeToggle({ label }: { label: string }) {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    setTheme((document.documentElement.dataset.theme as "light" | "dark") ?? "light");
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    document.cookie = `musicstudio-theme=${next}; path=/; max-age=31536000`;
  };

  return (
    <button type="button" onClick={toggle} title={label} aria-label={label}>
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
