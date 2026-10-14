import { useState } from "react";
import MainLayout, { type Page } from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Tutor from "./pages/Tutor"; 
import Assessment from "./pages/Assessment";
import Results from "./pages/Results";

const pageDetails: Record<Page, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Your Dashboard",
    subtitle: "Your progress, your pace, your learning journey.",
  },
  upload: {
    title: "My Materials",
    subtitle: "Bring your learning resources together.",
  },
  tutor: {
    title: "AI Tutor",
    subtitle: "Get help understanding your study materials.",
  },
  assessment: {
    title: "Assessments",
    subtitle: "Practice, learn, and strengthen your understanding.",
  },
  results: {
    title: "My Progress",
    subtitle: "Review your learning and discover what to improve.",
  },
};

export default function App() {
  const [activePage, setActivePage] = useState<Page>("dashboard");

  return (
    <MainLayout
      activePage={activePage}
      title={pageDetails[activePage].title}
      subtitle={pageDetails[activePage].subtitle}
      onNavigate={setActivePage}
    >
      {activePage === "dashboard" ? (
  <Dashboard onNavigate={setActivePage} />
) : activePage === "upload" ? (
  <Upload />
) : activePage === "tutor" ? (
  <Tutor />
) : activePage === "assessment" ? (
  <Assessment />
) : activePage === "results" ? (
  <Results />
) : (
  <section className="rounded-3xl border border-[#EDE2E5] bg-white p-8 dark:border-[#3C3044] dark:bg-[#241A2B]">
    <h2 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
      {pageDetails[activePage].title}
    </h2>

    <p className="mt-2 text-sm text-[#827580] dark:text-[#A99DAB]">
      This page is coming next. We're building the core learning
      experience one screen at a time.
    </p>
  </section>
)}
    </MainLayout>
  );
}