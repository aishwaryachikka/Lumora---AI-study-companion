import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend?: number;
}

export default function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
}: StatCardProps) {
  const positive = trend !== undefined && trend >= 0;

  return (
    <article className="rounded-2xl border border-[#EDE2E5] bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md dark:border-[#3C3044] dark:bg-[#241A2B]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#827580] dark:text-[#A99DAB]">
            {title}
          </p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-[#29202A] dark:text-[#F9F1F4]">
            {value}
          </h3>
        </div>

        <div className="rounded-xl bg-[#F6D8C8]/60 p-3 text-[#6D3B66] dark:bg-[#493044] dark:text-[#D19AB7]">
          <Icon size={22} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-1.5 text-xs">
        {trend !== undefined && (
          <span
            className={`inline-flex items-center gap-0.5 font-semibold ${
              positive
                ? "text-[#56856C] dark:text-[#91B8A4]"
                : "text-rose-600 dark:text-rose-300"
            }`}
          >
            {positive ? (
              <ArrowUpRight size={14} />
            ) : (
              <ArrowDownRight size={14} />
            )}
            {positive ? "+" : ""}
            {trend}%
          </span>
        )}

        <span className="text-[#827580] dark:text-[#A99DAB]">
          {description}
        </span>
      </div>
    </article>
  );
}