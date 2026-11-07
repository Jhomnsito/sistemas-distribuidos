import React, { useEffect, useState } from "react";

const preferenceKey = "vayxer-theme";
const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

function savedTheme() {
  try {
    const saved = localStorage.getItem(preferenceKey);
    return saved === "dark" || saved === "light" ? saved : null;
  } catch {
    return null;
  }
}

export default function ThemeToggle() {
  const [preference, setPreference] = useState(savedTheme);
  const [systemDark, setSystemDark] = useState(() => systemTheme.matches);
  const dark = preference ? preference === "dark" : systemDark;

  useEffect(() => {
    const update = (event) => setSystemDark(event.matches);
    systemTheme.addEventListener("change", update);
    return () => systemTheme.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);

  function toggle() {
    const next = dark ? "light" : "dark";
    setPreference(next);
    try {
      localStorage.setItem(preferenceKey, next);
    } catch {
      // El tema se aplica aunque no se pueda guardar la preferencia.
    }
  }

  return (
    <button
      type="button"
      className="signout"
      aria-pressed={dark}
      onClick={toggle}
    >
      Modo oscuro
    </button>
  );
}
