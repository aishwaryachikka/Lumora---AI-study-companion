import { useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  RotateCcw,
  Target,
  Trophy,
  XCircle,
  Zap,
} from "lucide-react";

type Question = {
  id: number;
  topic: string;
  difficulty: "Easy" | "Medium" | "Hard";
  type: "MCQ" | "Short Answer" | "Numerical";
  question: string;
  options: string[];
  answer: number;
  acceptedAnswers?: string[];
  numericalAnswer?: number;
  explanation: string;
};

const questions: Question[] = [
  {
    id: 1,
    topic: "DBMS",
    difficulty: "Easy",
    type: "MCQ",
    question: "What is the primary purpose of database normalization?",
    options: [
      "To increase data duplication",
      "To reduce redundancy and improve data integrity",
      "To make every table contain identical data",
      "To remove all relationships between tables",
    ],
    answer: 1,
    explanation:
      "Normalization organizes data into related tables to reduce unnecessary duplication and prevent insertion, update, and deletion anomalies.",
  },
  {
    id: 2,
    topic: "DBMS",
    difficulty: "Easy",
    type: "MCQ",
    question: "Which key uniquely identifies each record in a table?",
    options: [
      "Foreign key",
      "Composite attribute",
      "Primary key",
      "Non-key attribute",
    ],
    answer: 2,
    explanation:
      "A primary key uniquely identifies each record in a table. Its values must be unique and cannot be NULL.",
  },
  {
    id: 3,
    topic: "Java",
    difficulty: "Medium",
    type: "MCQ",
    question: "Which concept allows a Java class to have multiple methods with the same name but different parameter lists?",
    options: [
      "Method overriding",
      "Encapsulation",
      "Inheritance",
      "Method overloading",
    ],
    answer: 3,
    explanation:
      "Method overloading allows multiple methods in the same class to share a name while differing in their parameter lists.",
  },
  {
    id: 4,
    topic: "Java",
    difficulty: "Medium",
    type: "MCQ",
    question: "Which keyword is used to create a subclass in Java?",
    options: ["implements", "extends", "inherits", "super"],
    answer: 1,
    explanation:
      "The extends keyword establishes class inheritance in Java, allowing a subclass to inherit accessible members from its superclass.",
  },

    {
  id: 5,
  topic: "COA",
  difficulty: "Hard",
  type: "MCQ",
    question: "Which type of memory is typically the fastest among these options?",
    options: ["Hard disk", "Main memory", "CPU registers", "Optical disk"],
    answer: 2,
    explanation:
      "CPU registers are located within the processor and provide extremely fast access to the values currently needed for computation.",
  },
    {
    id: 6,
    topic: "DBMS",
    difficulty: "Medium",
    type: "Short Answer",
    question: "Explain the difference between a primary key and a foreign key.",
    options: [],
    answer: -1,
    acceptedAnswers: [
      "A primary key uniquely identifies a record, while a foreign key references a key in another table.",
    ],
    explanation:
      "A primary key uniquely identifies a row. A foreign key establishes a relationship by referencing a key in another table.",
  },
  {
    id: 7,
    topic: "COA",
    difficulty: "Easy",
    type: "Numerical",
    question: "How many bits are there in 4 bytes?",
    options: [],
    answer: -1,
    numericalAnswer: 32,
    explanation:
      "One byte contains 8 bits. Therefore, 4 bytes contain 4 × 8 = 32 bits.",
  },
];

const difficultyStyles: Record<Question["difficulty"], string> = {
  Easy: "bg-[#E5F0E9] text-[#426C53] dark:bg-[#253D31] dark:text-[#A5D5B5]",
  Medium:
    "bg-[#FFF0D6] text-[#8A6326] dark:bg-[#44351F] dark:text-[#F0D18C]",
  Hard: "bg-[#F8E4E8] text-[#99516A] dark:bg-[#432633] dark:text-[#E6A8BD]",
};

export default function Assessment() {
  const [selectedTopic, setSelectedTopic] = useState("All");
  const [selectedDifficulty, setSelectedDifficulty] = useState("All");
  const [activeQuiz, setActiveQuiz] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
const [answers, setAnswers] = useState<Record<number, string | number>>({});
  const topics = ["All", ...new Set(questions.map((q) => q.topic))];

  const filteredQuestions = questions.filter((question) => {
    const matchesTopic =
      selectedTopic === "All" || question.topic === selectedTopic;
    const matchesDifficulty =
      selectedDifficulty === "All" ||
      question.difficulty === selectedDifficulty;

    return matchesTopic && matchesDifficulty;
  });

  const currentQuestion = filteredQuestions[currentIndex];

  const score = filteredQuestions.reduce(
    (total, question) =>
      total + (answers[question.id] === question.answer ? 1 : 0),
    0,
  );

  const percentage =
    filteredQuestions.length > 0
      ? Math.round((score / filteredQuestions.length) * 100)
      : 0;

  function startQuiz() {
    setAnswers({});
    setCurrentIndex(0);
    setSubmitted(false);
    setActiveQuiz(true);
  }

  function returnToOverview() {
    setActiveQuiz(false);
    setSubmitted(false);
    setCurrentIndex(0);
    setAnswers({});
  }

  function chooseAnswer(optionIndex: number) {
  if (!submitted && currentQuestion) {
    setAnswers((previous) => ({
      ...previous,
      [currentQuestion.id]: optionIndex,
    }));
  }
}

function enterTextAnswer(value: string) {
  if (!submitted && currentQuestion) {
    setAnswers((previous) => ({
      ...previous,
      [currentQuestion.id]: value,
    }));
  }
}

  function nextQuestion() {
    if (currentIndex < filteredQuestions.length - 1) {
      setCurrentIndex((previous) => previous + 1);
    }
  }

  function previousQuestion() {
    if (currentIndex > 0) {
      setCurrentIndex((previous) => previous - 1);
    }
  }

  const cardClass =
    "rounded-3xl border border-[#EDE2E5] bg-white dark:border-[#3C3044] dark:bg-[#241A2B]";

  const mutedText = "text-[#827580] dark:text-[#A99DAB]";

  if (filteredQuestions.length === 0) {
    return (
      <section className={`${cardClass} p-8 text-center`}>
        <h2 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
          No questions found
        </h2>
        <p className={`mt-2 text-sm ${mutedText}`}>
          Try selecting a different topic or difficulty.
        </p>
        <button
          onClick={() => {
            setSelectedTopic("All");
            setSelectedDifficulty("All");
          }}
          className="mt-5 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white"
        >
          Reset filters
        </button>
      </section>
    );
  }

  if (activeQuiz && submitted) {
    return (
      <div className="space-y-6">
        <section className={`${cardClass} overflow-hidden p-6 sm:p-10`}>
          <div className="mx-auto max-w-xl text-center">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]">
              <Trophy size={36} />
            </div>

            <p className={`mt-6 text-sm font-semibold ${mutedText}`}>
              ASSESSMENT COMPLETED
            </p>

            <h2 className="mt-2 text-3xl font-bold text-[#29202A] dark:text-[#F9F1F4] sm:text-4xl">
              {percentage >= 80
                ? "Amazing work!"
                : percentage >= 50
                  ? "Good effort!"
                  : "Keep learning!"}
            </h2>

            <p className={`mt-3 text-sm ${mutedText}`}>
              Every attempt helps you understand what you know and what to
              practise next.
            </p>

            <div className="mt-8 rounded-3xl bg-[#FFF9F5] p-6 dark:bg-[#17121C]">
              <p className="text-5xl font-bold text-[#6D3B66] dark:text-[#D19AB7]">
                {percentage}%
              </p>
              <p className={`mt-2 text-sm ${mutedText}`}>
                {score} out of {filteredQuestions.length} correct
              </p>

              <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#EDE2E5] dark:bg-[#3C3044]">
                <div
                  className="h-full rounded-full bg-[#8EAF9D] transition-all"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="rounded-2xl border border-[#EDE2E5] p-4 dark:border-[#3C3044]">
                <CheckCircle2
                  className="mx-auto text-[#8EAF9D]"
                  size={24}
                />
                <p className="mt-2 text-2xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
                  {score}
                </p>
                <p className={`text-xs ${mutedText}`}>Correct answers</p>
              </div>

              <div className="rounded-2xl border border-[#EDE2E5] p-4 dark:border-[#3C3044]">
                <XCircle className="mx-auto text-[#C985A3]" size={24} />
                <p className="mt-2 text-2xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
                  {filteredQuestions.length - score}
                </p>
                <p className={`text-xs ${mutedText}`}>To review</p>
              </div>
            </div>
          </div>
        </section>

        <section className={`${cardClass} p-6 sm:p-8`}>
          <h3 className="text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
            Answer review
          </h3>

          <div className="mt-6 space-y-5">
            {filteredQuestions.map((question, index) => {
              const correct = answers[question.id] === question.answer;

              return (
                <article
                  key={question.id}
                  className="rounded-2xl border border-[#EDE2E5] p-5 dark:border-[#3C3044]"
                >
                  <div className="flex items-start gap-3">
                    {correct ? (
                      <CheckCircle2
                        className="mt-0.5 shrink-0 text-[#8EAF9D]"
                        size={21}
                      />
                    ) : (
                      <XCircle
                        className="mt-0.5 shrink-0 text-[#C985A3]"
                        size={21}
                      />
                    )}

                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-[#6D3B66] dark:text-[#D19AB7]">
                        QUESTION {index + 1} · {question.topic}
                      </p>

                      <h4 className="mt-2 font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                        {question.question}
                      </h4>

                      <p className={`mt-3 text-sm ${mutedText}`}>
                        Your answer:{" "}
                        <span className="font-medium text-[#29202A] dark:text-[#F9F1F4]">
                          {answers[question.id] === undefined
                            ? "Not answered"
                            : question.options[answers[question.id]]}
                        </span>
                      </p>

                      <p className="mt-2 text-sm text-[#426C53] dark:text-[#A5D5B5]">
                        Correct answer: {question.options[question.answer]}
                      </p>

                      <p className={`mt-3 text-sm leading-6 ${mutedText}`}>
                        {question.explanation}
                      </p>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={startQuiz}
            className="inline-flex items-center gap-2 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F]"
          >
            <RotateCcw size={17} />
            Try again
          </button>

          <button
            onClick={returnToOverview}
            className="rounded-xl border border-[#EDE2E5] px-5 py-3 text-sm font-semibold text-[#6D3B66] dark:border-[#3C3044] dark:text-[#D19AB7]"
          >
            Back to assessments
          </button>
        </div>
      </div>
    );
  }

  if (activeQuiz && currentQuestion) {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={returnToOverview}
            className={`inline-flex items-center gap-2 text-sm font-medium ${mutedText}`}
          >
            <ChevronLeft size={18} />
            Exit assessment
          </button>

          <span className="rounded-full bg-[#F6D8C8] px-3 py-1.5 text-xs font-semibold text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]">
            Question {currentIndex + 1} of {filteredQuestions.length}
          </span>
        </div>

        <section className={`${cardClass} p-6 sm:p-9`}>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-[#F6D8C8] px-3 py-1 text-xs font-semibold text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]">
              {currentQuestion.topic}
            </span>

            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${difficultyStyles[currentQuestion.difficulty]}`}
            >
              {currentQuestion.difficulty}
            </span>
          </div>

          <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#EDE2E5] dark:bg-[#3C3044]">
            <div
              className="h-full rounded-full bg-[#6D3B66] transition-all duration-300 dark:bg-[#D19AB7]"
              style={{
                width: `${((currentIndex + 1) / filteredQuestions.length) * 100}%`,
              }}
            />
          </div>

          <h2 className="mt-8 text-xl font-bold leading-8 text-[#29202A] dark:text-[#F9F1F4] sm:text-2xl">
            {currentQuestion.question}
          </h2>

          <p className={`mt-2 text-sm ${mutedText}`}>
            Choose one answer.
          </p>

          <div className="mt-7 space-y-3">
            {currentQuestion.options.map((option, index) => {
              const selected = answers[currentQuestion.id] === index;

              return (
                <button
                  key={option}
                  onClick={() => chooseAnswer(index)}
                  className={`flex w-full items-center gap-4 rounded-2xl border p-4 text-left transition ${
                    selected
                      ? "border-[#6D3B66] bg-[#F8EFF5] dark:border-[#D19AB7] dark:bg-[#39273A]"
                      : "border-[#EDE2E5] hover:border-[#C98FA5] hover:bg-[#FFF9F5] dark:border-[#3C3044] dark:hover:bg-[#30213A]"
                  }`}
                >
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm font-semibold ${
                      selected
                        ? "bg-[#6D3B66] text-white dark:bg-[#D19AB7] dark:text-[#17121C]"
                        : "bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]"
                    }`}
                  >
                    {String.fromCharCode(65 + index)}
                  </span>

                  <span className="text-sm leading-6 text-[#29202A] dark:text-[#F9F1F4]">
                    {option}
                  </span>

                  {selected && (
                    <CheckCircle2
                      className="ml-auto shrink-0 text-[#6D3B66] dark:text-[#D19AB7]"
                      size={20}
                    />
                  )}
                </button>
              );
            })}
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[#EDE2E5] pt-6 dark:border-[#3C3044]">
            <button
              onClick={previousQuestion}
              disabled={currentIndex === 0}
              className="inline-flex items-center gap-2 rounded-xl border border-[#EDE2E5] px-4 py-3 text-sm font-semibold text-[#6D3B66] transition disabled:cursor-not-allowed disabled:opacity-40 dark:border-[#3C3044] dark:text-[#D19AB7]"
            >
              <ChevronLeft size={17} />
              Previous
            </button>

            {currentIndex < filteredQuestions.length - 1 ? (
              <button
                onClick={nextQuestion}
                className="inline-flex items-center gap-2 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F]"
              >
                Next question
                <ChevronRight size={17} />
              </button>
            ) : (
              <button
                onClick={() => setSubmitted(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F]"
              >
                Submit assessment
                <CheckCircle2 size={17} />
              </button>
            )}
          </div>

          <p className={`mt-4 text-center text-xs ${mutedText}`}>
            {Object.keys(answers).filter((id) =>
              filteredQuestions.some((q) => q.id === Number(id)),
            ).length}{" "}
            of {filteredQuestions.length} questions answered
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-3xl bg-[#43243F] p-6 text-white sm:p-9">
        <div className="pointer-events-none absolute -right-10 -top-16 h-48 w-48 rounded-full bg-[#C98FA5]/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 right-32 h-40 w-40 rounded-full bg-[#B8A4D9]/20 blur-3xl" />

        <div className="relative max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-[#F6D8C8]">
            <Zap size={14} />
            YOUR LEARNING, IN ACTION
          </div>

          <h2 className="mt-5 text-2xl font-bold sm:text-3xl">
            Small steps. Stronger understanding.
          </h2>

          <p className="mt-3 max-w-xl text-sm leading-6 text-white/75">
            Practise what you've learned, discover the concepts that need more
            attention, and build confidence one question at a time.
          </p>

          <div className="mt-6 flex flex-wrap gap-5 text-sm text-white/80">
            <span className="inline-flex items-center gap-2">
              <BookOpen size={17} />
              {questions.length} sample questions
            </span>
            <span className="inline-flex items-center gap-2">
              <Target size={17} />
              Instant scoring
            </span>
            <span className="inline-flex items-center gap-2">
              <Clock3 size={17} />
              Self-paced
            </span>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            label: "Available questions",
            value: questions.length,
            icon: BookOpen,
          },
          {
            label: "Topics to explore",
            value: new Set(questions.map((q) => q.topic)).size,
            icon: Target,
          },
          {
            label: "Difficulty levels",
            value: new Set(questions.map((q) => q.difficulty)).size,
            icon: Zap,
          },
        ].map((stat) => {
          const Icon = stat.icon;

          return (
            <div key={stat.label} className={`${cardClass} p-5`}>
              <div className="flex items-center justify-between">
                <span className={`text-sm ${mutedText}`}>{stat.label}</span>
                <Icon className="text-[#C98FA5]" size={20} />
              </div>

              <p className="mt-3 text-3xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
                {stat.value}
              </p>
            </div>
          );
        })}
      </div>

      <section className={`${cardClass} p-6 sm:p-8`}>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#43243F] dark:text-[#F0BFAE]">
            <CircleHelp size={22} />
          </div>

          <div>
            <h3 className="text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
              Set up your practice
            </h3>
            <p className={`mt-1 text-sm leading-6 ${mutedText}`}>
              Choose a topic and difficulty, then start your assessment.
            </p>
          </div>
        </div>

        <div className="mt-7 grid grid-cols-1 gap-5 sm:grid-cols-2">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
              Select subject
            </span>

            <select
              value={selectedTopic}
              onChange={(event) => setSelectedTopic(event.target.value)}
              className="w-full rounded-xl border border-[#EDE2E5] bg-[#FFF9F5] px-4 py-3 text-sm text-[#29202A] outline-none focus:border-[#6D3B66] dark:border-[#3C3044] dark:bg-[#17121C] dark:text-[#F9F1F4]"
            >
              {topics.map((topic) => (
                <option key={topic} value={topic}>
                  {topic === "All" ? "All subjects" : topic}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
              Difficulty
            </span>

            <select
              value={selectedDifficulty}
              onChange={(event) =>
                setSelectedDifficulty(event.target.value)
              }
              className="w-full rounded-xl border border-[#EDE2E5] bg-[#FFF9F5] px-4 py-3 text-sm text-[#29202A] outline-none focus:border-[#6D3B66] dark:border-[#3C3044] dark:bg-[#17121C] dark:text-[#F9F1F4]"
            >
              {["All", "Easy", "Medium", "Hard"].map((difficulty) => (
                <option key={difficulty} value={difficulty}>
                  {difficulty === "All" ? "All difficulties" : difficulty}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-[#FFF9F5] p-4 dark:bg-[#17121C]">
          <div>
            <p className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
              Your practice set
            </p>
            <p className={`mt-1 text-sm ${mutedText}`}>
              {filteredQuestions.length}{" "}
              {filteredQuestions.length === 1 ? "question" : "questions"}{" "}
              selected
            </p>
          </div>

          <button
            onClick={startQuiz}
            className="inline-flex items-center gap-2 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#43243F]"
          >
            Start assessment
            <ChevronRight size={18} />
          </button>
        </div>
      </section>

      <p className={`text-xs leading-5 ${mutedText}`}>
        Demo mode: these are sample questions. Adaptive question generation,
        uploaded-material citations, and persistent mastery tracking will be
        connected when the backend is ready.
      </p>
    </div>
  );
}