import {
  ArrowRight,
  BookOpen,
  Brain,
  Clock3,
  Flame,
  Play,
  Sparkles,
  Target,
} from "lucide-react";

import StatCard from "../components/StatCard";
import ProgressBar from "../components/ProgressBar";
import { dashboardData } from "../data/mockData";

interface DashboardProps {
  onNavigate: (
    page: "dashboard" | "upload" | "tutor" | "assessment" | "results",
  ) => void;
}

export default function Dashboard({ onNavigate }: DashboardProps) {
  const data = dashboardData;

  return (
    <div className="space-y-8">
      {/* Welcome section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#43243F] via-[#6D3B66] to-[#854F6C] p-6 text-white sm:p-8 lg:p-10">
        <div className="pointer-events-none absolute -right-10 -top-16 h-56 w-56 rounded-full bg-[#D19AB7]/20 blur-3xl" />

        <div className="relative z-10 max-w-2xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs text-white/90">
            <Sparkles size={14} />
            YOUR PERSONAL LEARNING SPACE
          </div>

          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Small steps,{" "}
            <span className="text-[#F6D8C8]">big progress.</span>
          </h1>

          <p className="mt-3 max-w-lg text-sm leading-6 text-white/75 sm:text-base">
            Learn at your own pace, understand what needs attention, and let
            your AI study companion help you figure out what comes next.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate("tutor")}
              className="inline-flex items-center gap-2 rounded-xl bg-[#F6D8C8] px-5 py-3 text-sm font-semibold text-[#43243F] transition hover:bg-white"
            >
              <Brain size={17} />
              Ask your AI tutor
              <ArrowRight size={16} />
            </button>

            <button
              onClick={() => onNavigate("upload")}
              className="inline-flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/20"
            >
              <BookOpen size={17} />
              Add materials
            </button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Overall mastery"
          value={`${data.mastery}%`}
          description="from your previous level"
          icon={Brain}
          trend={data.weeklyChange}
        />

        <StatCard
          title="Study time"
          value={`${data.studyHours}h`}
          description="sample weekly total"
          icon={Clock3}
        />

        <StatCard
          title="Assessments"
          value={`${data.completedAssessments}`}
          description="sample completed count"
          icon={Target}
        />

        <StatCard
          title="Learning streak"
          value="4 days"
          description="sample activity streak"
          icon={Flame}
        />
      </section>

      {/* Focus areas and recommendations */}
      <section className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <div className="rounded-3xl border border-[#EDE2E5] bg-white p-5 sm:p-6 xl:col-span-3 dark:border-[#3C3044] dark:bg-[#241A2B]">
          <div className="mb-6 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
                Let's strengthen these topics
              </h2>
              <p className="mt-1 text-sm text-[#827580] dark:text-[#A99DAB]">
                Sample focus areas for the demo
              </p>
            </div>

            <div className="rounded-xl bg-[#F6D8C8]/60 p-2.5 text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
              <Target size={20} />
            </div>
          </div>

          <div className="space-y-6">
            {data.focusAreas.map((area) => (
              <div key={area.topic}>
                <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                      {area.topic}
                    </p>
                    <p className="mt-1 text-xs text-[#827580] dark:text-[#A99DAB]">
                      {area.subject} · {area.action}
                    </p>
                  </div>

                  <span className="text-sm font-bold text-[#6D3B66] dark:text-[#D19AB7]">
                    {area.mastery}%
                  </span>
                </div>

                <ProgressBar
                  value={area.mastery}
                  showLabel={false}
                  color={
                    area.mastery < 50
                      ? "bg-[#C98FA5]"
                      : area.mastery < 65
                        ? "bg-[#B8A4D9]"
                        : "bg-[#8EAF9D]"
                  }
                />

                <p className="mt-2 text-xs text-[#827580] dark:text-[#A99DAB]">
                  {area.reason}
                </p>
              </div>
            ))}
          </div>

          <button
            onClick={() => onNavigate("assessment")}
            className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[#6D3B66] hover:gap-3 dark:text-[#D19AB7]"
          >
            Practice your weak topics <ArrowRight size={16} />
          </button>
        </div>

        <div className="rounded-3xl border border-[#EDE2E5] bg-white p-5 sm:p-6 xl:col-span-2 dark:border-[#3C3044] dark:bg-[#241A2B]">
          <div className="mb-6 flex items-center gap-3">
            <div className="rounded-xl bg-[#B8A4D9]/25 p-3 text-[#6D3B66] dark:text-[#D19AB7]">
              <Sparkles size={21} />
            </div>

            <div>
              <h2 className="font-bold text-[#29202A] dark:text-[#F9F1F4]">
                Pick up where you need it
              </h2>
              <p className="text-xs text-[#827580] dark:text-[#A99DAB]">
                Sample recommendations
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {data.recommendations.map((item) => (
              <article
                key={item.title}
                className="rounded-2xl border border-[#EDE2E5] p-4 dark:border-[#3C3044]"
              >
                <span className="rounded-full bg-[#F6D8C8]/70 px-2.5 py-1 text-[11px] font-semibold text-[#6D3B66] dark:bg-[#493044] dark:text-[#F0BFAE]">
                  {item.type}
                </span>

                <h3 className="mt-3 font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                  {item.title}
                </h3>

                <p className="mt-1 text-sm leading-5 text-[#827580] dark:text-[#A99DAB]">
                  {item.description}
                </p>

                <div className="mt-4 flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 text-xs text-[#827580] dark:text-[#A99DAB]">
                    <Clock3 size={14} />
                    {item.duration}
                  </span>

                  <button
                    aria-label={`Start ${item.title}`}
                    onClick={() => onNavigate("assessment")}
                    className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#6D3B66] text-white transition hover:bg-[#43243F] dark:bg-[#D19AB7] dark:text-[#241A2B]"
                  >
                    <Play size={15} fill="currentColor" />
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Weekly progress */}
      <section className="rounded-3xl border border-[#EDE2E5] bg-white p-5 sm:p-6 dark:border-[#3C3044] dark:bg-[#241A2B]">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
              Your learning rhythm
            </h2>
            <p className="mt-1 text-sm text-[#827580] dark:text-[#A99DAB]">
              Illustrative weekly activity — not live analytics
            </p>
          </div>

          <span className="rounded-full bg-[#8EAF9D]/20 px-3 py-1.5 text-xs font-semibold text-[#56856C] dark:text-[#91B8A4]">
            Demo data
          </span>
        </div>

        <div className="flex h-48 items-end justify-between gap-2 sm:gap-5">
          {data.weeklyProgress.map((item) => (
            <div
              key={item.day}
              className="flex h-full flex-1 flex-col items-center justify-end gap-3"
            >
              <span className="text-[10px] text-[#827580] sm:text-xs dark:text-[#A99DAB]">
                {item.value}%
              </span>

              <div className="flex h-32 w-full items-end overflow-hidden rounded-t-xl bg-[#F6D8C8]/35 dark:bg-[#30213A]">
                <div
                  className="w-full rounded-t-xl bg-gradient-to-t from-[#6D3B66] to-[#C98FA5] transition-all duration-700 dark:from-[#854F6C] dark:to-[#D19AB7]"
                  style={{ height: `${item.value}%` }}
                />
              </div>

              <span className="text-xs text-[#827580] dark:text-[#A99DAB]">
                {item.day}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Continue learning */}
      <section className="flex flex-col gap-4 rounded-3xl border border-[#EDE2E5] bg-[#F6D8C8]/40 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6 dark:border-[#3C3044] dark:bg-[#30213A]">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
            <BookOpen size={23} />
          </div>

          <div>
            <h2 className="font-bold text-[#29202A] dark:text-[#F9F1F4]">
              Ready to learn something new?
            </h2>
            <p className="mt-1 text-sm text-[#827580] dark:text-[#A99DAB]">
              Upload your study materials to get started.
            </p>
          </div>
        </div>

        <button
          onClick={() => onNavigate("upload")}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F] dark:bg-[#D19AB7] dark:text-[#241A2B]"
        >
          Upload materials <ArrowRight size={16} />
        </button>
      </section>
    </div>
  );
}