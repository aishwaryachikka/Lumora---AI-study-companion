import { useState } from "react";
import { Menu, X } from "lucide-react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

export type Page =
  | "dashboard"
  | "upload"
  | "tutor"
  | "assessment"
  | "results";

interface MainLayoutProps {
  activePage: Page;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  onNavigate: (page: Page) => void;
}

export default function MainLayout({
  activePage,
  title,
  subtitle,
  children,
  onNavigate,
}: MainLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  function navigateTo(page: Page) {
    onNavigate(page);
    setMobileMenuOpen(false);
  }

  return (
    <div className="min-h-screen bg-[#FFF9F5] transition-colors duration-300 dark:bg-[#17121C]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden lg:block">
        <Sidebar activePage={activePage} onNavigate={navigateTo} />
      </aside>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Close navigation menu"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileMenuOpen(false)}
          />

          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw]">
            <div className="flex h-full flex-col bg-white dark:bg-[#241A2B]">
              <div className="flex justify-end p-3">
                <button
                  aria-label="Close menu"
                  onClick={() => setMobileMenuOpen(false)}
                  className="rounded-lg p-2 text-[#6D3B66] dark:text-[#D19AB7]"
                >
                  <X size={22} />
                </button>
              </div>

              <div className="min-h-0 flex-1">
                <Sidebar
                  activePage={activePage}
                  onNavigate={navigateTo}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="min-h-screen lg:pl-64">
        <div className="sticky top-0 z-30 flex items-center gap-3 border-b border-[#EDE2E5] bg-[#FFF9F5]/95 px-4 py-2 backdrop-blur-md dark:border-[#3C3044] dark:bg-[#17121C]/95 lg:hidden">
          <button
            aria-label="Open navigation menu"
            onClick={() => setMobileMenuOpen(true)}
            className="rounded-xl p-2 text-[#6D3B66] hover:bg-[#F6D8C8] dark:text-[#D19AB7] dark:hover:bg-[#30213A]"
          >
            <Menu size={22} />
          </button>

          <span className="text-sm font-semibold text-[#43243F] dark:text-[#F9F1F4]">
            Lumora
          </span>
        </div>

        <Header title={title} subtitle={subtitle} />

        <main className="mx-auto w-full max-w-[1600px] p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}