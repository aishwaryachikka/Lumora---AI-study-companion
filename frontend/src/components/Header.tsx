import { Bell, ChevronDown, Sparkles } from "lucide-react";
import ThemeToggle from "./ThemeToggle";

interface HeaderProps {
  title: string;
  subtitle: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 flex min-h-20 items-center justify-between gap-4 border-b border-[#EDE2E5] bg-[#FFF9F5]/95 px-5 py-4 backdrop-blur-md sm:px-8 dark:border-[#3C3044] dark:bg-[#17121C]/95">
      <div className="min-w-0">
        <div className="mb-1 flex items-center gap-2">
          <Sparkles
            size={15}
            className="shrink-0 text-[#C98FA5] dark:text-[#D19AB7]"
          />
          <span className="text-xs font-medium text-[#827580] dark:text-[#A99DAB]">
            YOUR PERSONAL LEARNING SPACE
          </span>
        </div>

        <h2 className="truncate text-xl font-bold text-[#29202A] sm:text-2xl dark:text-[#F9F1F4]">
          {title}
        </h2>

        <p className="hidden text-sm text-[#827580] sm:block dark:text-[#A99DAB]">
          {subtitle}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <ThemeToggle />

        <button
          type="button"
          aria-label="Notifications"
          className="relative flex h-11 w-11 items-center justify-center rounded-2xl border border-[#EDE2E5] bg-white text-[#6D3B66] transition-colors hover:bg-[#F6D8C8] dark:border-[#3C3044] dark:bg-[#241A2B] dark:text-[#D19AB7] dark:hover:bg-[#30213A]"
        >
          <Bell size={19} />
          <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-[#C98FA5]" />
        </button>

        <button
          type="button"
          className="flex items-center gap-2 rounded-2xl p-1.5 transition-colors hover:bg-[#F6D8C8]/50 dark:hover:bg-[#30213A]"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#B8A4D9] text-sm font-bold text-[#43243F]">
            S
          </div>

          <div className="hidden text-left sm:block">
            <p className="text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
              Student
            </p>
            <p className="text-xs text-[#827580] dark:text-[#A99DAB]">
              Learner
            </p>
          </div>

          <ChevronDown
            size={15}
            className="hidden text-[#827580] sm:block dark:text-[#A99DAB]"
          />
        </button>
      </div>
    </header>
  );
}