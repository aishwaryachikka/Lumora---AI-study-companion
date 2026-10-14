import { useRef, useState } from "react";
import {
  Upload as UploadIcon,
  FileText,
  FileVideo,
  File as FileIcon,
  FileCheck2,
  Trash2,
  CloudUpload,
  CheckCircle2,
  Clock3,
  Sparkles,
  BookOpen,
  AlertCircle,
} from "lucide-react";

interface Material {
  id: string;
  file: File;
  status: "ready" | "processing";
}

const ACCEPTED_TYPES = [".pdf", ".ppt", ".pptx", ".mp4", ".mov", ".webm"];

function getFileType(fileName: string) {
  const extension = fileName.split(".").pop()?.toLowerCase();

  if (extension === "pdf") return "PDF document";
  if (extension === "ppt" || extension === "pptx") return "Presentation";
  if (["mp4", "mov", "webm"].includes(extension ?? "")) {
    return "Video";
  }

  return "File";
}

function getFileIcon(fileName: string) {
  const type = getFileType(fileName);

  if (type === "PDF document") return FileText;
  if (type === "Video") return FileVideo;
  if (type === "Presentation") return BookOpen;

  return FileIcon;
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Upload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");

  function addFiles(fileList: FileList | File[]) {
    setError("");

    const incomingFiles = Array.from(fileList);
    const validFiles: File[] = [];
    const invalidFiles: string[] = [];

    incomingFiles.forEach((file) => {
      const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;

      if (!ACCEPTED_TYPES.includes(extension)) {
        invalidFiles.push(file.name);
        return;
      }

      if (file.size > 100 * 1024 * 1024) {
        invalidFiles.push(`${file.name} (over 100 MB)`);
        return;
      }

      validFiles.push(file);
    });

    if (invalidFiles.length > 0) {
      setError(
        `Unsupported file or file too large: ${invalidFiles.join(", ")}. Choose PDF, PPT, PPTX, MP4, MOV, or WEBM files under 100 MB.`,
      );
    }

    if (validFiles.length > 0) {
      setMaterials((current) => {
        const existing = new Set(
          current.map(
            (item) =>
              `${item.file.name}-${item.file.size}-${item.file.lastModified}`,
          ),
        );

        const newMaterials = validFiles
          .filter(
            (file) =>
              !existing.has(
                `${file.name}-${file.size}-${file.lastModified}`,
              ),
          )
          .map((file) => ({
            id: `${file.name}-${file.size}-${file.lastModified}`,
            file,
            status: "ready" as const,
          }));

        return [...current, ...newMaterials];
      });
    }

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function removeMaterial(id: string) {
    setMaterials((current) => current.filter((item) => item.id !== id));
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    addFiles(event.dataTransfer.files);
  }

  return (
    <div className="space-y-7">
      {/* Page introduction */}
      <section>
        <div className="mb-2 flex items-center gap-2">
          <Sparkles
            size={18}
            className="text-[#C98FA5] dark:text-[#D19AB7]"
          />
          <span className="text-sm font-medium text-[#827580] dark:text-[#A99DAB]">
            YOUR PERSONAL KNOWLEDGE BASE
          </span>
        </div>

        <h2 className="text-2xl font-bold tracking-tight text-[#29202A] sm:text-3xl dark:text-[#F9F1F4]">
          Your learning materials 📚
        </h2>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#827580] dark:text-[#A99DAB]">
          Bring your textbooks, lecture slides, and videos together.
          Your materials will become the foundation for personalized
          tutoring and assessments.
        </p>
      </section>

      {/* Upload zone */}
      <section
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) {
            setIsDragging(false);
          }
        }}
        onDrop={handleDrop}
        className={`rounded-3xl border-2 border-dashed p-6 text-center transition-all duration-200 sm:p-10 ${
          isDragging
            ? "border-[#6D3B66] bg-[#F6D8C8]/50 dark:border-[#D19AB7] dark:bg-[#30213A]"
            : "border-[#C98FA5]/60 bg-white dark:border-[#493044] dark:bg-[#241A2B]"
        }`}
      >
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F6D8C8] text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
          <CloudUpload size={31} />
        </div>

        <h3 className="mt-5 text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
          Drop your study materials here
        </h3>

        <p className="mt-2 text-sm text-[#827580] dark:text-[#A99DAB]">
          Or choose files from your computer
        </p>

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl bg-[#6D3B66] px-5 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-[#43243F] dark:bg-[#D19AB7] dark:text-[#241A2B] dark:hover:bg-[#E3B4CB]"
        >
          <UploadIcon size={17} />
          Browse files
        </button>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.ppt,.pptx,.mp4,.mov,.webm"
          className="hidden"
          onChange={(event) => {
            if (event.target.files) {
              addFiles(event.target.files);
            }
          }}
        />

        <p className="mt-4 text-xs text-[#827580] dark:text-[#A99DAB]">
          PDF, PPT, PPTX, MP4, MOV, WEBM · Maximum 100 MB per file
        </p>
      </section>

      {/* Error feedback */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200"
        >
          <AlertCircle size={19} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Supported formats */}
      <section>
        <h3 className="mb-4 font-semibold text-[#29202A] dark:text-[#F9F1F4]">
          What you can upload
        </h3>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            {
              icon: FileText,
              title: "PDF documents",
              description: "Textbooks, notes & reading material",
              color: "bg-[#F6D8C8] text-[#6D3B66]",
            },
            {
              icon: BookOpen,
              title: "Presentations",
              description: "Lecture slides and class decks",
              color: "bg-[#E9E0F6] text-[#6D4F91]",
            },
            {
              icon: FileVideo,
              title: "Lecture videos",
              description: "Recorded lessons and lectures",
              color: "bg-[#DDECE3] text-[#46755A]",
            },
          ].map(({ icon: Icon, title, description, color }) => (
            <article
              key={title}
              className="rounded-2xl border border-[#EDE2E5] bg-white p-5 dark:border-[#3C3044] dark:bg-[#241A2B]"
            >
              <div
                className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl ${color}`}
              >
                <Icon size={22} />
              </div>

              <h4 className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                {title}
              </h4>

              <p className="mt-1 text-sm leading-5 text-[#827580] dark:text-[#A99DAB]">
                {description}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Materials list */}
      <section className="rounded-3xl border border-[#EDE2E5] bg-white p-5 sm:p-6 dark:border-[#3C3044] dark:bg-[#241A2B]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-[#29202A] dark:text-[#F9F1F4]">
              Uploaded materials
            </h3>
            <p className="mt-1 text-sm text-[#827580] dark:text-[#A99DAB]">
              {materials.length}{" "}
              {materials.length === 1 ? "file" : "files"} added in this session
            </p>
          </div>

          <span className="rounded-full bg-[#F6D8C8]/70 px-3 py-1.5 text-xs font-medium text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
            Local preview
          </span>
        </div>

        {materials.length === 0 ? (
          <div className="py-12 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#FFF9F5] text-[#C98FA5] dark:bg-[#30213A] dark:text-[#D19AB7]">
              <FileCheck2 size={26} />
            </div>

            <h4 className="mt-4 font-semibold text-[#29202A] dark:text-[#F9F1F4]">
              Your library starts here
            </h4>

            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-[#827580] dark:text-[#A99DAB]">
              Upload your first study material to start building your
              personal learning library.
            </p>
          </div>
        ) : (
          <div className="mt-5 divide-y divide-[#EDE2E5] dark:divide-[#3C3044]">
            {materials.map((material) => {
              const Icon = getFileIcon(material.file.name);

              return (
                <article
                  key={material.id}
                  className="flex flex-wrap items-center gap-3 py-4 first:pt-0 last:pb-0"
                >
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#FFF9F5] text-[#6D3B66] dark:bg-[#30213A] dark:text-[#D19AB7]">
                    <Icon size={22} />
                  </div>

                  <div className="min-w-0 flex-1">
                    <h4 className="break-words text-sm font-semibold text-[#29202A] dark:text-[#F9F1F4]">
                      {material.file.name}
                    </h4>
                    <p className="mt-1 text-xs text-[#827580] dark:text-[#A99DAB]">
                      {getFileType(material.file.name)} ·{" "}
                      {formatSize(material.file.size)}
                    </p>
                  </div>

                  <span className="inline-flex items-center gap-1.5 rounded-full bg-[#DDECE3] px-3 py-1.5 text-xs font-medium text-[#46755A] dark:bg-[#294438] dark:text-[#A9D6B9]">
                    <Clock3 size={13} />
                    Ready to process
                  </span>

                  <button
                    type="button"
                    onClick={() => removeMaterial(material.id)}
                    aria-label={`Remove ${material.file.name}`}
                    title="Remove file"
                    className="rounded-lg p-2 text-[#827580] transition-colors hover:bg-rose-50 hover:text-rose-600 dark:text-[#A99DAB] dark:hover:bg-rose-950/40 dark:hover:text-rose-300"
                  >
                    <Trash2 size={17} />
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Processing notice */}
      <div className="flex items-start gap-3 rounded-2xl border border-[#EDE2E5] bg-[#F6D8C8]/30 p-4 dark:border-[#3C3044] dark:bg-[#30213A]">
        <CheckCircle2
          size={20}
          className="mt-0.5 shrink-0 text-[#6D3B66] dark:text-[#D19AB7]"
        />
        <div>
          <p className="text-sm font-semibold text-[#43243F] dark:text-[#F9F1F4]">
            Next up: building your knowledge base
          </p>
          <p className="mt-1 text-sm leading-6 text-[#827580] dark:text-[#A99DAB]">
            File selection currently runs in your browser. Document extraction,
            topic tagging, and AI-powered processing will be enabled when we
            connect the backend.
          </p>
        </div>
      </div>
    </div>
  );
}