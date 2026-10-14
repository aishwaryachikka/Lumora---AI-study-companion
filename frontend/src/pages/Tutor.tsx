import { useState } from "react";
import {
  Send,
  Sparkles,
  BookOpen,
  FileText,
  Video,
  ChevronRight,
  MessageCircle,
  Lightbulb,
  RotateCcw,
  GraduationCap,
  Bot,
  User,
  ExternalLink,
} from "lucide-react";

interface Citation {
  id: number;
  source: string;
  location: string;
  excerpt: string;
  type: "pdf" | "slide" | "video";
}

interface Message {
  id: number;
  role: "assistant" | "user";
  content: string;
  citations?: Citation[];
}

const sampleCitations: Citation[] = [
  {
    id: 1,
    source: "Database Systems.pdf",
    location: "Page 24",
    excerpt:
      "Normalization organizes relational tables to reduce redundant data and prevent insertion, update, and deletion anomalies.",
    type: "pdf",
  },
  {
    id: 2,
    source: "DBMS Lecture Slides.pptx",
    location: "Slide 12",
    excerpt:
      "First Normal Form requires each attribute to contain atomic values and each record to be uniquely identifiable.",
    type: "slide",
  },
];

const suggestions = [
  {
    icon: Lightbulb,
    title: "Explain a concept",
    prompt: "Explain database normalization in simple terms.",
  },
  {
    icon: BookOpen,
    title: "Help me revise",
    prompt: "Give me a quick revision of the main concepts in my materials.",
  },
  {
    icon: GraduationCap,
    title: "Test my understanding",
    prompt: "Ask me one question to check my understanding.",
  },
];

export default function Tutor() {
  const [input, setInput] = useState("");
  const [activeSource, setActiveSource] = useState<Citation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  function sendMessage(text = input) {
    const question = text.trim();

    if (!question || isTyping) return;

    const userMessage: Message = {
      id: Date.now(),
      role: "user",
      content: question,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsTyping(true);

    // Demo response only. Replace this with the AI backend integration.
    window.setTimeout(() => {
      const response: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content:
          "Here's a simple way to approach your question. In database normalization, we organize tables so that information is stored consistently and unnecessary duplication is reduced. This helps prevent common data anomalies when records are inserted, updated, or deleted.\n\nFor example, instead of repeatedly storing a student's department details in every course registration, we can keep department information in a separate related table.\n\nThis is a demonstration response, not an answer generated from your uploaded materials. Connect the AI backend to enable grounded answers and verified citations.",
        citations: sampleCitations,
      };

      setMessages((current) => [...current, response]);
      setIsTyping(false);
    }, 900);
  }

  function resetChat() {
    setMessages([]);
    setActiveSource(null);
    setInput("");
    setIsTyping(false);
  }

  return (
    <div className="space-y-6">
      {/* Introduction */}
      <section>
        <div className="mb-2 flex items-center gap-2">
          <Sparkles
            size={17}
            className="text-[#C98FA5] dark:text-[#D19AB7]"
          />
          <span className="text-xs font-semibold tracking-widest text-[#827580] dark:text-[#A99DAB]">
            YOUR PERSONAL AI LEARNING COMPANION
          </span>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-[#29202A] sm:text-3xl dark:text-[#F9F1F4]">
              Let's figure it out together. 💜
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#827580] dark:text-[#A99DAB]">
              Ask questions, explore concepts, and learn at your own pace.
              Your tutor will use your learning materials once the AI backend
              is connected.
            </p>
          </div>

          <button
            type="button"
            onClick={resetChat}
            className="inline-flex items-center gap-2 rounded-xl border border-[#EDE2E5] bg-white px-3 py-2 text-sm font-medium text-[#6D3B66] transition-colors hover:bg-[#FFF9F5] dark:border-[#3C3044] dark:bg-[#241A2B] dark:text-[#D19AB7] dark:hover:bg-[#30213A]"
          >
            <RotateCcw size={15} />
            New chat
          </button>
        </div>
      </section>

      {/* Main tutor workspace */}
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        {/* Chat */}
        <section className="flex min-h-[620px] flex-col overflow-hidden rounded-3xl border border-[#EDE2E5] bg-white dark:border-[#3C3044] dark:bg-[#241A2B]">
          {/* Chat header */}
          <div className="flex items-center gap-3 border-b border-[#EDE2E5] p-4 sm:p-5 dark:border-[#3C3044]">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
              <Bot size={23} />
            </div>

            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                Lumora AI Tutor
              </h3>
              <p className="mt-0.5 text-xs text-[#827580] dark:text-[#A99DAB]">
                Your learning partner
              </p>
            </div>

            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F6D8C8]/50 px-3 py-1.5 text-xs font-medium text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#8EAF9D]" />
              Demo mode
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 space-y-5 p-4 sm:p-6">
            {messages.length === 0 ? (
              <div className="flex min-h-[380px] flex-col items-center justify-center text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
                  <Sparkles size={29} />
                </div>

                <h3 className="mt-5 text-xl font-bold text-[#29202A] dark:text-[#F9F1F4]">
                  Hey, learner! 👋
                </h3>

                <p className="mt-2 max-w-sm text-sm leading-6 text-[#827580] dark:text-[#A99DAB]">
                  What's on your mind today? Choose a prompt below or ask
                  your own question to get started.
                </p>

                <div className="mt-7 grid w-full max-w-lg gap-3 sm:grid-cols-3">
                  {suggestions.map(({ icon: Icon, title, prompt }) => (
                    <button
                      key={title}
                      type="button"
                      onClick={() => sendMessage(prompt)}
                      className="rounded-2xl border border-[#EDE2E5] bg-[#FFF9F5] p-3 text-left transition-all hover:-translate-y-0.5 hover:border-[#C98FA5] dark:border-[#3C3044] dark:bg-[#30213A] dark:hover:border-[#D19AB7]"
                    >
                      <Icon
                        size={19}
                        className="mb-3 text-[#6D3B66] dark:text-[#D19AB7]"
                      />
                      <span className="block text-xs font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                        {title}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-[#827580] dark:text-[#A99DAB]">
                        Try this prompt
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === "user" ? "flex-row-reverse" : ""
                  }`}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                      message.role === "assistant"
                        ? "bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]"
                        : "bg-[#B8A4D9] text-[#43243F]"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      <Bot size={19} />
                    ) : (
                      <User size={19} />
                    )}
                  </div>

                  <div className="min-w-0 max-w-[88%]">
                    <div
                      className={`rounded-2xl p-4 ${
                        message.role === "user"
                          ? "bg-[#6D3B66] text-white dark:bg-[#493044] dark:text-[#F9F1F4]"
                          : "bg-[#FFF9F5] text-[#29202A] dark:bg-[#30213A] dark:text-[#F9F1F4]"
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-sm leading-7">
                        {message.content}
                      </p>
                    </div>

                    {message.citations && (
                      <div className="mt-3 space-y-2">
                        <p className="flex items-center gap-2 text-xs font-semibold text-[#827580] dark:text-[#A99DAB]">
                          <BookOpen size={14} />
                          Example source references · demo only
                        </p>

                        {message.citations.map((citation) => (
                          <button
                            key={citation.id}
                            type="button"
                            onClick={() => setActiveSource(citation)}
                            className="flex w-full items-center gap-3 rounded-xl border border-[#EDE2E5] bg-white p-3 text-left transition-colors hover:border-[#C98FA5] dark:border-[#3C3044] dark:bg-[#241A2B] dark:hover:border-[#D19AB7]"
                          >
                            <FileText
                              size={18}
                              className="shrink-0 text-[#6D3B66] dark:text-[#D19AB7]"
                            />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-xs font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                                {citation.source}
                              </span>
                              <span className="mt-1 block text-xs text-[#827580] dark:text-[#A99DAB]">
                                {citation.location}
                              </span>
                            </span>
                            <ExternalLink
                              size={15}
                              className="shrink-0 text-[#827580] dark:text-[#A99DAB]"
                            />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {isTyping && (
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
                  <Bot size={19} />
                </div>
                <div className="rounded-2xl bg-[#FFF9F5] px-4 py-3 text-sm text-[#827580] dark:bg-[#30213A] dark:text-[#A99DAB]">
                  Lumora is preparing a demo response...
                </div>
              </div>
            )}
          </div>

          {/* Message input */}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              sendMessage();
            }}
            className="border-t border-[#EDE2E5] p-4 sm:p-5 dark:border-[#3C3044]"
          >
            <div className="flex items-end gap-3 rounded-2xl border border-[#EDE2E5] bg-[#FFF9F5] p-2 focus-within:border-[#C98FA5] dark:border-[#3C3044] dark:bg-[#30213A] dark:focus-within:border-[#D19AB7]">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Ask Lumora anything..."
                rows={2}
                aria-label="Ask the AI tutor a question"
                className="max-h-32 min-h-12 flex-1 resize-y bg-transparent px-3 py-3 text-sm text-[#29202A] outline-none placeholder:text-[#827580] dark:text-[#F9F1F4] dark:placeholder:text-[#A99DAB]"
              />

              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                aria-label="Send message"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#6D3B66] text-white transition-colors hover:bg-[#43243F] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-[#D19AB7] dark:text-[#241A2B] dark:hover:bg-[#E3B4CB]"
              >
                <Send size={18} />
              </button>
            </div>

            <p className="mt-2 text-center text-xs text-[#827580] dark:text-[#A99DAB]">
              Demo responses are simulated. AI-powered tutoring will be
              connected to your backend.
            </p>
          </form>
        </section>

        {/* Learning context */}
        <aside className="space-y-5">
          <section className="rounded-3xl border border-[#EDE2E5] bg-white p-5 dark:border-[#3C3044] dark:bg-[#241A2B]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
                <BookOpen size={21} />
              </div>
              <div>
                <h3 className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                  Learning context
                </h3>
                <p className="text-xs text-[#827580] dark:text-[#A99DAB]">
                  Sample workspace
                </p>
              </div>
            </div>

            <div className="mt-5 rounded-2xl bg-[#FFF9F5] p-4 dark:bg-[#30213A]">
              <p className="text-xs font-medium text-[#827580] dark:text-[#A99DAB]">
                CURRENT SUBJECT
              </p>
              <p className="mt-2 font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                Database Management
              </p>
              <p className="mt-1 text-xs text-[#827580] dark:text-[#A99DAB]">
                Example learning context
              </p>
            </div>

            <div className="mt-5">
              <p className="mb-3 text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                Suggested topics
              </p>

              {[
                "Database normalization",
                "Relational algebra",
                "Transaction management",
              ].map((topic) => (
                <button
                  key={topic}
                  type="button"
                  onClick={() => sendMessage(`Help me understand ${topic}.`)}
                  className="flex w-full items-center gap-2 border-b border-[#EDE2E5] py-3 text-left text-sm text-[#827580] transition-colors hover:text-[#6D3B66] last:border-0 dark:border-[#3C3044] dark:text-[#A99DAB] dark:hover:text-[#D19AB7]"
                >
                  <span className="flex-1">{topic}</span>
                  <ChevronRight size={16} />
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-3xl bg-[#6D3B66] p-5 text-white dark:bg-[#30213A]">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15">
              <GraduationCap size={22} />
            </div>

            <h3 className="mt-4 font-semibold">
              Learning tip of the day
            </h3>

            <p className="mt-2 text-sm leading-6 text-white/85 dark:text-[#F9F1F4]">
              Don't just memorize a concept. Try explaining it in your own
              words, then use an example to check your understanding.
            </p>

            <div className="mt-4 flex items-center gap-2 text-xs font-medium text-white/75 dark:text-[#D19AB7]">
              <MessageCircle size={15} />
              Learn by explaining
            </div>
          </section>

          {activeSource && (
            <section
              className="rounded-3xl border border-[#C98FA5]/50 bg-white p-5 dark:border-[#493044] dark:bg-[#241A2B]"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-[#827580] dark:text-[#A99DAB]">
                    Demo source preview
                  </p>
                  <h3 className="mt-2 break-words font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                    {activeSource.source}
                  </h3>
                  <p className="mt-1 text-xs text-[#827580] dark:text-[#A99DAB]">
                    {activeSource.location}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setActiveSource(null)}
                  aria-label="Close source preview"
                  className="rounded-lg px-2 py-1 text-sm text-[#827580] hover:bg-[#FFF9F5] dark:text-[#A99DAB] dark:hover:bg-[#30213A]"
                >
                  ✕
                </button>
              </div>

              <p className="mt-4 text-sm leading-6 text-[#827580] dark:text-[#A99DAB]">
                {activeSource.excerpt}
              </p>

              <p className="mt-3 text-xs leading-5 text-[#C98FA5] dark:text-[#D19AB7]">
                Example excerpt for UI demonstration only. This is not
                extracted from a real uploaded file.
              </p>
            </section>
          )}

          <section className="rounded-2xl border border-[#EDE2E5] p-4 dark:border-[#3C3044]">
            <div className="flex items-start gap-3">
              <Video
                size={19}
                className="mt-0.5 text-[#6D3B66] dark:text-[#D19AB7]"
              />
              <div>
                <h4 className="text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                  Source-grounded learning
                </h4>
                <p className="mt-1 text-xs leading-5 text-[#827580] dark:text-[#A99DAB]">
                  The completed system will link answers to verified
                  pages, slides, or video timestamps from your materials.
                </p>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}