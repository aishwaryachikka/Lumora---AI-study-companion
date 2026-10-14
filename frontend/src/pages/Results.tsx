import { useState } from "react";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Brain,
  CheckCircle2,
  Clock3,
  Flame,
  Lightbulb,
  Target,
  TrendingUp,
  Trophy,
} from "lucide-react";

const subjects = [
  {
    name: "Database Management Systems",
    shortName: "DBMS",
    mastery: 78,
    completed: 18,
    total: 24,
    note: "Good progress!",
    color: "#8EAF9D",
  },
  {
    name: "Java Programming",
    shortName: "Java",
    mastery: 62,
    completed: 15,
    total: 24,
    note: "Keep practising",
    color: "#B8A4D9",
  },
  {
    name: "Computer Organization",
    shortName: "COA",
    mastery: 45,
    completed: 9,
    total: 20,
    note: "Needs attention",
    color: "#C98FA5",
  },
  {
    name: "Software Engineering",
    shortName: "Software Engineering",
    mastery: 86,
    completed: 19,
    total: 22,
    note: "Strong understanding",
    color: "#D8B66D",
  },
];

const recentAssessments = [
  {
    title: "Database Normalization",
    subject: "DBMS",
    date: "Demo · Recent",
    score: 90,
    total: 10,
  },
  {
    title: "Java Fundamentals",
    subject: "Java",
    date: "Demo · Recent",
    score: 70,
    total: 10,
  },
  {
    title: "Computer Memory",
    subject: "COA",
    date: "Demo · Recent",
    score: 50,
    total: 10,
  },
];

const recommendations = [
  {
    subject: "COMPUTER ORGANIZATION",
    title: "Revise memory hierarchy",
    description:
      "Review registers, cache, and main memory before attempting another quiz.",
    duration: "15 min",
    priority: "High priority",
    color: "#C985A3",
    icon: Brain,
  },
  {
    subject: "JAVA PROGRAMMING",
    title: "Practise method overloading",
    description:
      "Strengthen your understanding of method signatures and parameter lists.",
    duration: "10 min",
    priority: "Practise next",
    color: "#B8A4D9",
    icon: BookOpen,
  },
  {
    subject: "DATABASE MANAGEMENT",
    title: "Review database keys",
    description:
      "Practise identifying primary keys, foreign keys, and their relationships.",
    duration: "12 min",
    priority: "Quick revision",
    color: "#8EAF9D",
    icon: Target,
  },
];

const revisionContent: Record<
  string,
  {
    recap: string;
    keyPoints: string[];
    questions: string[];
  }
> = {
  "Revise memory hierarchy": {
    recap:
      "Memory hierarchy organizes storage into levels with different speeds, capacities, and costs.",
    keyPoints: [
      "Registers are located inside the CPU and are extremely fast.",
      "Cache stores frequently used data for quick access.",
      "RAM holds programs and data currently in use.",
      "Secondary storage provides long-term storage.",
    ],
    questions: [
      "Why do computers need cache memory?",
      "Arrange registers, cache, RAM, and secondary storage from fastest to slowest.",
      "How do speed and capacity differ across memory levels?",
    ],
  },

  "Practise method overloading": {
    recap:
      "Method overloading allows multiple Java methods to have the same name but different parameter lists.",
    keyPoints: [
      "Methods can differ in the number of parameters.",
      "Parameter types or their order can differ.",
      "Changing only the return type is not enough.",
      "Method overloading is compile-time polymorphism.",
    ],
    questions: [
      "What is method overloading?",
      "Can two methods differ only in their return type?",
      "Write two overloaded methods with different parameter types.",
    ],
  },

  "Review database keys": {
    recap:
      "Database keys identify records and help establish relationships between tables.",
    keyPoints: [
      "A primary key uniquely identifies each row.",
      "Primary key values cannot be NULL.",
      "A foreign key references a candidate key in a table.",
      "A composite key contains two or more columns.",
    ],
    questions: [
      "What is the difference between primary and foreign keys?",
      "Can a primary key contain duplicate values?",
      "What is a composite key?",
    ],
  },
};

const weeklyActivity = [
  { day: "Mon", value: 35 },
  { day: "Tue", value: 65 },
  { day: "Wed", value: 45 },
  { day: "Thu", value: 85 },
  { day: "Fri", value: 55 },
  { day: "Sat", value: 100 },
  { day: "Sun", value: 25 },
];

export default function Results() {
    const [selectedRevision, setSelectedRevision] = useState<string | null>(null);

const [showRevisionQuestions, setShowRevisionQuestions] = useState(false);
const [practiceAnswers, setPracticeAnswers] = useState<Record<string, string>>({});
const [practiceSubmitted, setPracticeSubmitted] = useState(false);
const overallMastery = Math.round(
    subjects.reduce((sum, subject) => sum + subject.mastery, 0) /
      subjects.length,
  );

  const cardClass =
    "rounded-3xl border border-[#EDE2E5] bg-white dark:border-[#3C3044] dark:bg-[#241A2B]";

  const mutedText = "text-[#827580] dark:text-[#A99DAB]";

  return (
    <div className="space-y-7">
      {/* Welcome banner */}
      <section className="relative overflow-hidden rounded-3xl bg-[#43243F] p-6 text-white sm:p-9">
        <div className="pointer-events-none absolute -right-10 -top-16 h-52 w-52 rounded-full bg-[#C98FA5]/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 right-40 h-48 w-48 rounded-full bg-[#B8A4D9]/20 blur-3xl" />

        <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div className="max-w-xl">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-[#F6D8C8]">
              <TrendingUp size={14} />
              YOUR LEARNING JOURNEY
            </span>

            <h2 className="mt-5 text-2xl font-bold sm:text-3xl">
              Progress, not perfection. ✨
            </h2>

            <p className="mt-3 text-sm leading-6 text-white/75">
              Every question you answer helps you understand your strengths and
              discover what to learn next. Keep going at your own pace.
            </p>
          </div>

          <div className="flex h-32 w-32 shrink-0 flex-col items-center justify-center self-center rounded-full border-4 border-[#C98FA5]/50 bg-white/5 sm:self-auto">
            <span className="text-3xl font-bold">{overallMastery}%</span>
            <span className="mt-1 text-xs text-white/70">Overall mastery</span>
          </div>
        </div>
      </section>

      {/* Summary statistics */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            title: "Overall mastery",
            value: `${overallMastery}%`,
            detail: "Across 4 subjects",
            icon: Target,
            color: "#6D3B66",
            bg: "#F6D8C8",
          },
          {
            title: "Questions answered",
            value: "42",
            detail: "Demo activity",
            icon: CheckCircle2,
            color: "#426C53",
            bg: "#E5F0E9",
          },
          {
            title: "Study time",
            value: "6.5 hrs",
            detail: "Illustrative total",
            icon: Clock3,
            color: "#7556A2",
            bg: "#EDE5F8",
          },
          {
            title: "Study streak",
            value: "4 days",
            detail: "Demo activity",
            icon: Flame,
            color: "#99516A",
            bg: "#F8E4E8",
          },
        ].map((stat) => {
          const Icon = stat.icon;

          return (
            <article key={stat.title} className={`${cardClass} p-5`}>
              <div className="flex items-center justify-between">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-2xl dark:bg-[#30213A]"
                  style={{ backgroundColor: stat.bg }}
                >
                  <Icon
                    size={21}
                    style={{ color: stat.color }}
                  />
                </div>

                <ArrowUpRight className={mutedText} size={18} />
              </div>

              <p className={`mt-5 text-sm ${mutedText}`}>{stat.title}</p>

              <p className="mt-1 text-2xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
                {stat.value}
              </p>

              <p className={`mt-1 text-xs ${mutedText}`}>{stat.detail}</p>
            </article>
          );
        })}
      </section>

      {/* Subject mastery */}
      <section className={`${cardClass} p-6 sm:p-8`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
              Subject mastery
            </h3>

            <p className={`mt-1 text-sm ${mutedText}`}>
              See where you feel confident and where to focus next.
            </p>
          </div>

          <span className="rounded-full bg-[#F6D8C8] px-3 py-1.5 text-xs font-semibold text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]">
            {subjects.length} subjects
          </span>
        </div>

        <div className="mt-7 space-y-7">
          {subjects.map((subject) => (
            <div key={subject.shortName}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                    {subject.name}
                  </h4>

                  <p className={`mt-1 text-xs ${mutedText}`}>
                    {subject.completed} of {subject.total} demo learning
                    activities completed
                  </p>
                </div>

                <span
                  className="text-xl font-bold"
                  style={{ color: subject.color }}
                >
                  {subject.mastery}%
                </span>
              </div>

              <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#EDE2E5] dark:bg-[#3C3044]">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${subject.mastery}%`,
                    backgroundColor: subject.color,
                  }}
                />
              </div>

              <p className={`mt-2 text-xs ${mutedText}`}>
                {subject.note}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Activity chart */}
      <section className={`${cardClass} p-6 sm:p-8`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
              Learning activity
            </h3>

            <p className={`mt-1 text-sm ${mutedText}`}>
              An illustrative snapshot of your weekly activity.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-medium text-[#6D3B66] dark:text-[#D19AB7]">
            <span className="h-2.5 w-2.5 rounded-full bg-[#6D3B66] dark:bg-[#D19AB7]" />
            Activity level
          </div>
        </div>

        <div className="mt-8 flex h-48 items-end justify-between gap-2 sm:gap-5">
          {weeklyActivity.map((item) => (
            <div
              key={item.day}
              className="flex h-full flex-1 flex-col items-center justify-end gap-3"
            >
              <div className="flex h-full w-full max-w-12 items-end">
                <div
                  title={`${item.value}% illustrative activity`}
                  className="w-full rounded-t-xl bg-[#C98FA5] transition-all hover:bg-[#6D3B66] dark:bg-[#854F6C] dark:hover:bg-[#D19AB7]"
                  style={{ height: `${item.value}%` }}
                />
              </div>

              <span className={`text-xs ${mutedText}`}>{item.day}</span>
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-start gap-3 rounded-2xl bg-[#FFF9F5] p-4 dark:bg-[#17121C]">
          <Lightbulb
            className="mt-0.5 shrink-0 text-[#B58B3C]"
            size={20}
          />

          <p className={`text-sm leading-6 ${mutedText}`}>
            <span className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
              A little reminder:
            </span>{" "}
            Consistent practice can help you retain concepts. You don't need to
            study for hours every day to make progress.
          </p>
        </div>
      </section>

      {/* Recommended learning */}
      <section>
        <div className="mb-5">
          <h3 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
            Recommended for you
          </h3>

          <p className={`mt-1 text-sm ${mutedText}`}>
            Suggested revision activities based on the sample mastery data.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {recommendations.map((item) => {
            const Icon = item.icon;

            return (
              <article
                key={item.title}
                className={`${cardClass} flex flex-col p-5`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-2xl"
                    style={{
                      backgroundColor: `${item.color}20`,
                      color: item.color,
                    }}
                  >
                    <Icon size={23} />
                  </div>

                  <span
                    className="rounded-full px-2.5 py-1 text-[10px] font-semibold"
                    style={{
                      backgroundColor: `${item.color}20`,
                      color: item.color,
                    }}
                  >
                    {item.priority}
                  </span>
                </div>

                <p className="mt-5 text-[10px] font-bold tracking-wider text-[#6D3B66] dark:text-[#D19AB7]">
                  {item.subject}
                </p>

                <h4 className="mt-2 text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
                  {item.title}
                </h4>

                <p className={`mt-2 flex-1 text-sm leading-6 ${mutedText}`}>
                  {item.description}
                </p>

                <div className="mt-5 flex items-center justify-between border-t border-[#EDE2E5] pt-4 dark:border-[#3C3044]">
                  <span className={`text-xs ${mutedText}`}>
                    <Clock3 className="mr-1 inline" size={14} />
                    {item.duration}
                  </span>

                  <button
  type="button"
  onClick={() => {
    setSelectedRevision(item.title);
    setShowRevisionQuestions(false);
  }}
  className="inline-flex items-center gap-1 text-xs font-semibold text-[#6D3B66] transition hover:opacity-75 dark:text-[#D19AB7]"
>
  Revision idea
  <ArrowRight size={15} />
</button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
      {/* Revision Panel */}
{selectedRevision && revisionContent[selectedRevision] && (
  <section
    className={`${cardClass} p-6 sm:p-8`}
    aria-live="polite"
  >
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-[#6D3B66] dark:text-[#D19AB7]">
          Lumora Revision Studio
        </p>

        <h3 className="mt-2 text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
          {selectedRevision}
        </h3>

        <p className={`mt-2 text-sm ${mutedText}`}>
          Your personalized revision session starts here.
        </p>
      </div>

      <button
        type="button"
        onClick={() => {
          setSelectedRevision(null);
          setShowRevisionQuestions(false);
        }}
        className={`rounded-xl border border-[#EDE2E5] px-3 py-2 text-sm dark:border-[#3C3044] ${mutedText}`}
      >
        Close
      </button>
    </div>

    <div className="mt-6 rounded-2xl bg-[#F6D8C8]/40 p-5 dark:bg-[#30213A]">
      <div className="flex items-center gap-2">
        <Lightbulb size={20} className="text-[#6D3B66] dark:text-[#D19AB7]" />
        <h4 className="font-bold text-[#29202A] dark:text-[#F9F1F4]">
          Quick recap
        </h4>
      </div>

      <p className={`mt-3 text-sm leading-7 ${mutedText}`}>
        {revisionContent[selectedRevision].recap}
      </p>
    </div>

    <div className="mt-6">
      <h4 className="font-bold text-[#29202A] dark:text-[#F9F1F4]">
        Key points to remember
      </h4>

      <ul className="mt-3 space-y-3">
        {revisionContent[selectedRevision].keyPoints.map((point, index) => (
          <li
            key={point}
            className="flex items-start gap-3 text-sm leading-6 text-[#29202A] dark:text-[#F9F1F4]"
          >
            <CheckCircle2
              size={18}
              className="mt-1 shrink-0 text-[#8EAF9D]"
            />
            <span>{point}</span>
          </li>
        ))}
      </ul>
    </div>

    <div className="mt-7 rounded-2xl border border-[#EDE2E5] p-5 dark:border-[#3C3044]">
      <h4 className="font-bold text-[#29202A] dark:text-[#F9F1F4]">
        Test yourself
      </h4>

      <p className={`mt-1 text-sm ${mutedText}`}>
        Try these questions to check your understanding.
      </p>

      <ol className="mt-4 list-decimal space-y-3 pl-5 text-sm leading-6 text-[#29202A] dark:text-[#F9F1F4]">
        {revisionContent[selectedRevision].questions.map((question) => (
          <li key={question}>{question}</li>
        ))}
      </ol>

      <button
        type="button"
onClick={() => {
  setShowRevisionQuestions((previous) => !previous);
  setPracticeSubmitted(false);
}}        className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[#6D3B66] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F]"
      >
        {showRevisionQuestions ? "Hide practice questions" : "Start practice"}
        <ArrowRight size={16} />
      </button>

      {showRevisionQuestions && (
        <div className="mt-5 space-y-4">
          {revisionContent[selectedRevision].questions.map((question, index) => (
            <div
              key={question}
              className="rounded-xl bg-[#FFF9F5] p-4 dark:bg-[#17121C]"
            >
              <p className="text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                {index + 1}. {question}
              </p>

              <textarea
  rows={2}
  placeholder="Type your answer here..."
  className="mt-3 w-full resize-y rounded-xl border border-[#EDE2E5] bg-white p-3 text-sm text-[#29202A] outline-none focus:border-[#6D3B66] dark:border-[#3C3044] dark:bg-[#241A2B] dark:text-[#F9F1F4]"
  value={practiceAnswers[question] ?? ""}
  onChange={(event) =>
    setPracticeAnswers((previous) => ({
      ...previous,
      [question]: event.target.value,
    }))
  }
/>
            </div>
          ))}
          <button
  type="button"
  onClick={() => setPracticeSubmitted(true)}
  disabled={revisionContent[selectedRevision].questions.some(
    (question) => !(practiceAnswers[question] ?? "").trim()
  )}
  className="mt-5 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F] disabled:cursor-not-allowed disabled:opacity-50"
>
  Submit answers
</button>

{practiceSubmitted && (
  <div className="mt-4 rounded-xl border border-[#8EAF9D] bg-[#8EAF9D]/10 p-4">
    <p className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
      Answers submitted! 🎉
    </p>
    <p className={`mt-1 text-sm ${mutedText}`}>
      Your responses are saved in this page session. AI-based grading and
      personalized feedback will be available after backend integration.
    </p>
  </div>
)}
        </div>
      )}
    </div>
  </section>
)}

      {/* Recent assessments */}
      <section className={`${cardClass} p-6 sm:p-8`}>
        <div>
          <h3 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
            Recent assessments
          </h3>

          <p className={`mt-1 text-sm ${mutedText}`}>
            Sample assessment history for the demo.
          </p>
        </div>

        <div className="mt-6 space-y-3">
          {recentAssessments.map((assessment) => {
            const passed = assessment.score >= 70;

            return (
              <div
                key={assessment.title}
                className="flex flex-col gap-4 rounded-2xl border border-[#EDE2E5] p-4 sm:flex-row sm:items-center sm:justify-between dark:border-[#3C3044]"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]">
                    <BookOpen size={21} />
                  </div>

                  <div>
                    <h4 className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                      {assessment.title}
                    </h4>

                    <p className={`mt-1 text-xs ${mutedText}`}>
                      {assessment.subject} · {assessment.date}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 sm:justify-end">
                  <span
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                      passed
                        ? "bg-[#E5F0E9] text-[#426C53] dark:bg-[#253D31] dark:text-[#A5D5B5]"
                        : "bg-[#FFF0D6] text-[#8A6326] dark:bg-[#44351F] dark:text-[#F0D18C]"
                    }`}
                  >
                    {passed ? "Good progress" : "Needs practice"}
                  </span>

                  <span className="min-w-12 text-right text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
                    {assessment.score}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Demo notice */}
      <p className={`text-xs leading-5 ${mutedText}`}>
        Demo mode: mastery scores, study time, activity, and assessment history
        are illustrative. Real learner analytics, automatically detected weak
        topics, and adaptive recommendations will require backend integration.
      </p>
    </div>
  );
}