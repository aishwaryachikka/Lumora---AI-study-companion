import {
  LayoutDashboard,
  Upload,
  MessageCircle,
  ClipboardCheck,
  ChartNoAxesCombined,
  BookOpen,
  Sparkles,
} from "lucide-react";

type Page =
  | "dashboard"
  | "upload"
  | "tutor"
  | "assessment"
  | "results";

interface SidebarProps {
  activePage: Page;
  onNavigate: (page: Page) => void;
}

const navigation = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "upload", label: "My Materials", icon: Upload },
  { id: "tutor", label: "AI Tutor", icon: MessageCircle },
  { id: "assessment", label: "Assessments", icon: ClipboardCheck },
  { id: "results", label: "My Progress", icon: ChartNoAxesCombined },
] as const;

export default function Sidebar({
  activePage,
  onNavigate,
}: SidebarProps) {
  return (
    <aside className="flex h-full w-64 flex-col border-r border-[#EDE2E5] bg-white p-5 dark:border-[#3C3044] dark:bg-[#241A2B]">
      <div className="mb-10 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#6D3B66] text-white">
          <BookOpen size={23} />
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-tight text-[#43243F] dark:text-[#F9F1F4]">
            Lumora
          </h1>
          <p className="text-xs text-[#827580] dark:text-[#A99DAB]">
            Your AI learning buddy
          </p>
        </div>
      </div>

      <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-widest text-[#827580] dark:text-[#A99DAB]">
        Learning
      </p>

      <nav className="flex-1 space-y-2">
        {navigation.map(({ id, label, icon: Icon }) => {
          const isActive = activePage === id;

          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[#F6D8C8] text-[#43243F] dark:bg-[#493044] dark:text-[#F9F1F4]"
                  : "text-[#827580] hover:bg-[#FFF9F5] hover:text-[#6D3B66] dark:text-[#A99DAB] dark:hover:bg-[#30213A] dark:hover:text-[#F9F1F4]"
              }`}
            >
              <Icon size={19} />
              <span>{label}</span>
              {isActive && (
                <span className="ml-auto h-2 w-2 rounded-full bg-[#6D3B66] dark:bg-[#D19AB7]" />
              )}
            </button>
          );
        })}
      </nav>

      <div className="rounded-2xl bg-[#FFF9F5] p-4 dark:bg-[#30213A]">
        <Sparkles size={20} className="mb-2 text-[#6D3B66] dark:text-[#D19AB7]" />

        <p className="text-sm font-semibold text-[#43243F] dark:text-[#F9F1F4]">
          Small steps, big progress!
        </p>

        <p className="mt-1 text-xs leading-relaxed text-[#827580] dark:text-[#A99DAB]">
          Keep learning at your own pace. You're doing great!
        </p>
      </div>
    </aside>
  );
}