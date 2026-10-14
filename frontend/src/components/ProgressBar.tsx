interface ProgressBarProps {
  value: number;
  color?: string;
  showLabel?: boolean;
}

export default function ProgressBar({
  value,
  color = "bg-[#6D3B66]",
  showLabel = true,
}: ProgressBarProps) {
  const safeValue = Math.min(100, Math.max(0, value));

  return (
    <div className="w-full">
      {showLabel && (
        <div className="mb-2 flex items-center justify-between text-xs">
          <span className="text-[#827580] dark:text-[#A99DAB]">
            Mastery
          </span>
          <span className="font-semibold text-[#29202A] dark:text-[#F9F1F4]">
            {safeValue}%
          </span>
        </div>
      )}

      <div
        className="h-2.5 overflow-hidden rounded-full bg-[#EDE2E5] dark:bg-[#3C3044]"
        role="progressbar"
        aria-valuenow={safeValue}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}