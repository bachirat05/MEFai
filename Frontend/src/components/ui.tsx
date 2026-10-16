import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type Tone =
  | "slate"
  | "violet"
  | "blue"
  | "emerald"
  | "amber"
  | "red";

const toneClasses: Record<Tone, string> = {
  slate: "bg-slate-50 text-slate-600 ring-slate-200",
  violet: "bg-violet-50 text-violet-700 ring-violet-200",
  blue: "bg-blue-50 text-blue-700 ring-blue-200",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  amber: "bg-amber-50 text-amber-700 ring-amber-200",
  red: "bg-red-50 text-red-700 ring-red-200",
};

const iconToneClasses: Record<Tone, string> = {
  slate: "bg-slate-100 text-slate-600",
  violet: "bg-violet-100 text-violet-700",
  blue: "bg-blue-100 text-blue-700",
  emerald: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-red-100 text-red-700",
};

type PageHeaderProps = {
  title: string;
  description: string;
  icon?: LucideIcon;
  eyebrow?: string;
  action?: ReactNode;
};

export function PageHeader({
  title,
  description,
  icon: Icon,
  eyebrow,
  action,
}: PageHeaderProps) {
  return (
    <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="flex min-w-0 items-center gap-4">
        {Icon ? (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-violet-600 text-white shadow-sm shadow-violet-200">
            <Icon size={23} />
          </div>
        ) : null}

        <div className="min-w-0">
          {eyebrow ? (
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">
              {eyebrow}
            </p>
          ) : null}

          <h1 className="truncate text-2xl font-semibold text-slate-950">
            {title}
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            {description}
          </p>
        </div>
      </div>

      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

type SectionCardProps = {
  title?: string;
  description?: string;
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
};

export function SectionCard({
  title,
  description,
  icon: Icon,
  children,
  className = "",
  action,
}: SectionCardProps) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {title || description || Icon || action ? (
        <div className="flex flex-col gap-3 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            {Icon ? (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                <Icon size={19} />
              </div>
            ) : null}

            <div>
              {title ? (
                <h2 className="font-semibold text-slate-950">
                  {title}
                </h2>
              ) : null}

              {description ? (
                <p className="mt-1 text-sm text-slate-500">
                  {description}
                </p>
              ) : null}
            </div>
          </div>

          {action}
        </div>
      ) : null}

      <div className="p-6">
        {children}
      </div>
    </section>
  );
}

type StatCardProps = {
  label: string;
  value: ReactNode;
  icon: LucideIcon;
  tone?: Tone;
  caption?: string;
};

export function StatCard({
  label,
  value,
  icon: Icon,
  tone = "violet",
  caption,
}: StatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${iconToneClasses[tone]}`}>
          <Icon size={22} />
        </div>
      </div>

      <p className="mt-5 text-sm font-medium text-slate-500">
        {label}
      </p>

      <p className="mt-1 text-2xl font-semibold text-slate-950">
        {value}
      </p>

      {caption ? (
        <p className="mt-2 text-xs font-medium text-slate-500">
          {caption}
        </p>
      ) : null}
    </div>
  );
}

type StatusBadgeProps = {
  children: ReactNode;
  tone?: Tone;
};

export function StatusBadge({
  children,
  tone = "slate",
}: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${toneClasses[tone]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
};

export function EmptyState({
  icon: Icon,
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className="px-6 py-12 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
        <Icon size={23} />
      </div>
      <p className="mt-4 text-sm font-semibold text-slate-700">
        {title}
      </p>
      <p className="mt-1 text-sm text-slate-500">
        {description}
      </p>
    </div>
  );
}
