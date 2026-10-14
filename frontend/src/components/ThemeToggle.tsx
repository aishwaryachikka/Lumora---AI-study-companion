import { useEffect, useState } from "react";
import { Moon, Sun, Sparkles } from "lucide-react";

type Theme = "light" | "dark";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => {
    return localStorage.getItem("theme") === "dark" ? "dark" : "light";
  });

  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  function toggleTheme() {
    if (animating) return;

    setAnimating(true);

    window.setTimeout(() => {
      setTheme((current) => (current === "light" ? "dark" : "light"));
      setAnimating(false);
    }, 150);
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      className="group relative flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl border border-[#EDE2E5] bg-white text-[#6D3B66] shadow-sm transition-all duration-300 hover:scale-105 hover:shadow-md dark:border-[#3C3044] dark:bg-[#30213A] dark:text-[#D19AB7]"
    >
      <span
        className={`transition-all duration-300 ${
          animating ? "rotate-90 scale-50 opacity-0" : "rotate-0 scale-100 opacity-100"
        }`}
      >
        {animating ? (
          <Sparkles size={20} />
        ) : theme === "light" ? (
          <Sun size={20} />
        ) : (
          <Moon size={20} />
        )}
      </span>
    </button>
  );
}