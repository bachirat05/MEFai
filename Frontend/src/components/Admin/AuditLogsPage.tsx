import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { FormEvent } from "react";
import type { User } from "firebase/auth";

import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileClock,
  ListChecks,
  LoaderCircle,
  RotateCcw,
  Search,
  X,
} from "lucide-react";

import {
  getAuditLogs,
} from "../../services/api";

import type {
  AuditLogFilters,
  AuditLogItem,
} from "../../types";

import {
  EmptyState,
  PageHeader,
  SectionCard,
  StatCard,
} from "../ui";

type AuditLogsPageProps = {
  user: User;
};

const ACTIONS = [
  "CHAT_MESSAGE",
  "DOCUMENT_UPLOAD",
  "DOCUMENT_DELETE",
  "LEAVE_CREATED",
  "LEAVE_ACCEPTED",
  "LEAVE_REJECTED",
] as const;

const ROLES = [
  "employee",
  "manager",
  "admin",
] as const;

const PAGE_SIZES = [
  20,
  50,
  100,
] as const;

const SENSITIVE_KEYS = [
  "authorization",
  "content",
  "firebase_token",
  "message",
  "n8n_secret",
  "password",
  "prompt",
  "secret",
  "system_prompt",
  "token",
];

function isSensitiveKey(key: string): boolean {
  const normalizedKey = key.toLowerCase();

  return SENSITIVE_KEYS.some((sensitiveKey) =>
    normalizedKey.includes(sensitiveKey)
  );
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(
    "fr-FR",
    {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  ).format(new Date(value));
}

function actionTone(action: string): string {
  if (action === "CHAT_MESSAGE") {
    return "bg-violet-50 text-violet-700 ring-violet-200";
  }

  if (action === "DOCUMENT_UPLOAD") {
    return "bg-blue-50 text-blue-700 ring-blue-200";
  }

  if (action === "DOCUMENT_DELETE") {
    return "bg-red-50 text-red-700 ring-red-200";
  }

  if (action === "LEAVE_CREATED") {
    return "bg-amber-50 text-amber-700 ring-amber-200";
  }

  if (action === "LEAVE_ACCEPTED") {
    return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  }

  if (action === "LEAVE_REJECTED") {
    return "bg-orange-50 text-orange-700 ring-orange-200";
  }

  return "bg-slate-50 text-slate-700 ring-slate-200";
}

function roleTone(role: string | null): string {
  if (role === "admin") {
    return "bg-violet-50 text-violet-700 ring-violet-200";
  }

  if (role === "manager") {
    return "bg-blue-50 text-blue-700 ring-blue-200";
  }

  return "bg-slate-50 text-slate-700 ring-slate-200";
}

function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className: string;
}) {
  return (
    <span className={`inline-flex max-w-full items-center rounded-full px-2.5 py-1 text-[11px] font-bold ring-1 ring-inset ${className}`}>
      <span className="truncate">
        {children}
      </span>
    </span>
  );
}

function detailsAsEntries(
  item: AuditLogItem
): Array<[string, string]> {
  if (
    item.details === null ||
    item.details === undefined
  ) {
    return [];
  }

  if (typeof item.details === "string") {
    return [
      [
        "details",
        item.details,
      ],
    ];
  }

  return Object.entries(item.details)
    .filter(([key]) => !isSensitiveKey(key))
    .map(([key, value]) => [
      key,
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
        ? String(value)
        : JSON.stringify(value),
    ]);
}

function detailsPreview(item: AuditLogItem): string {
  if (item.action === "CHAT_MESSAGE") {
    const length = detailsAsEntries(item).find(
      ([key]) => key === "message_length"
    )?.[1];

    return length
      ? `Message envoye (${length} caracteres)`
      : "Message envoye";
  }

  const entries = detailsAsEntries(item);

  if (entries.length === 0) {
    return "Aucun detail";
  }

  const preferred =
    entries.find(([key]) => key === "filename") ??
    entries.find(([key]) => key === "demande_id") ??
    entries[0];

  return preferred[1];
}

function hasActiveFilters(filters: AuditLogFilters): boolean {
  return Boolean(
    filters.action ||
      filters.role ||
      filters.resource ||
      filters.user ||
      filters.date_from ||
      filters.date_to
  );
}

function AuditLogsPage({
  user,
}: AuditLogsPageProps) {
  const [logs, setLogs] =
    useState<AuditLogItem[]>([]);
  const [total, setTotal] =
    useState(0);
  const [totalPages, setTotalPages] =
    useState(0);
  const [isLoading, setIsLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);
  const [selectedLog, setSelectedLog] =
    useState<AuditLogItem | null>(null);

  const [filters, setFilters] =
    useState<AuditLogFilters>({
      page: 1,
      page_size: 20,
    });
  const [draftFilters, setDraftFilters] =
    useState<AuditLogFilters>({
      page: 1,
      page_size: 20,
    });

  const page = filters.page ?? 1;
  const pageSize = filters.page_size ?? 20;

  const loadLogs = useCallback(
    async (): Promise<void> => {
      try {
        setIsLoading(true);
        setError(null);

        const token =
          await user.getIdToken();

        const response =
          await getAuditLogs(
            token,
            filters
          );

        setLogs(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
      } catch (loadError) {
        console.error(
          "Audit logs loading error:",
          loadError
        );

        setError(
          loadError instanceof Error
            ? loadError.message
            : "Impossible de charger les audit logs."
        );
      } finally {
        setIsLoading(false);
      }
    },
    [
      filters,
      user,
    ]
  );

  useEffect(() => {
    void loadLogs();
  }, [loadLogs]);

  const showingCount = useMemo(
    () => logs.length,
    [logs]
  );

  function applyFilters(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setFilters({
      ...draftFilters,
      page: 1,
    });
  }

  function resetFilters(): void {
    const reset = {
      page: 1,
      page_size: pageSize,
    };

    setDraftFilters(reset);
    setFilters(reset);
  }

  function setPage(nextPage: number): void {
    setFilters((current) => ({
      ...current,
      page: nextPage,
    }));
    setDraftFilters((current) => ({
      ...current,
      page: nextPage,
    }));
  }

  function setPageSize(nextPageSize: number): void {
    setFilters((current) => ({
      ...current,
      page: 1,
      page_size: nextPageSize,
    }));
    setDraftFilters((current) => ({
      ...current,
      page: 1,
      page_size: nextPageSize,
    }));
  }

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 p-5 md:p-8">
      <div className="mx-auto max-w-7xl">
        <PageHeader
          title="Audit Logs"
          description="Consultez les evenements enregistres dans le systeme."
          icon={FileClock}
          eyebrow="Administration"
        />

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <StatCard
            label="Total evenements"
            value={isLoading ? "..." : total}
            caption="Total retourne par SQLite"
            icon={ListChecks}
            tone="violet"
          />
          <StatCard
            label="Page courante"
            value={`${page}/${totalPages || 1}`}
            caption="Pagination serveur"
            icon={FileClock}
            tone="blue"
          />
          <StatCard
            label="Evenements affiches"
            value={isLoading ? "..." : showingCount}
            caption={`${pageSize} maximum par page`}
            icon={Eye}
            tone="emerald"
          />
        </div>

        <SectionCard
          title="Filtres"
          description="Rechercher dans les logs sans charger tout l'historique."
          icon={Search}
          className="mb-6"
        >
          <form
            onSubmit={applyFilters}
            className="grid gap-4 lg:grid-cols-12"
          >
            <label className="lg:col-span-3">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Utilisateur / email
              </span>
              <input
                value={draftFilters.user ?? ""}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    user: event.target.value,
                  }))
                }
                className="mt-1.5 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
                placeholder="email ou UID"
              />
            </label>

            <label className="lg:col-span-2">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Action
              </span>
              <select
                value={draftFilters.action ?? ""}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    action: event.target.value,
                  }))
                }
                className="mt-1.5 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              >
                <option value="">Toutes</option>
                {ACTIONS.map((action) => (
                  <option
                    key={action}
                    value={action}
                  >
                    {action}
                  </option>
                ))}
              </select>
            </label>

            <label className="lg:col-span-2">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Role
              </span>
              <select
                value={draftFilters.role ?? ""}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    role: event.target.value,
                  }))
                }
                className="mt-1.5 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              >
                <option value="">Tous</option>
                {ROLES.map((role) => (
                  <option
                    key={role}
                    value={role}
                  >
                    {role}
                  </option>
                ))}
              </select>
            </label>

            <label className="lg:col-span-2">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Ressource
              </span>
              <input
                value={draftFilters.resource ?? ""}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    resource: event.target.value,
                  }))
                }
                className="mt-1.5 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
                placeholder="documents"
              />
            </label>

            <label className="lg:col-span-1">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Debut
              </span>
              <input
                type="date"
                value={draftFilters.date_from ?? ""}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    date_from: event.target.value,
                  }))
                }
                className="mt-1.5 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              />
            </label>

            <label className="lg:col-span-1">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                Fin
              </span>
              <input
                type="date"
                value={draftFilters.date_to ?? ""}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    date_to: event.target.value,
                  }))
                }
                className="mt-1.5 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              />
            </label>

            <div className="flex items-end gap-2 lg:col-span-1">
              <button
                type="submit"
                className="inline-flex h-11 flex-1 items-center justify-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-700"
                title="Rechercher"
              >
                <Search size={18} />
              </button>
              <button
                type="button"
                onClick={resetFilters}
                disabled={!hasActiveFilters(draftFilters)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
                title="Reinitialiser"
              >
                <RotateCcw size={18} />
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard
          title="Journal d'audit"
          description="Donnees issues de la table activity_logs."
          icon={FileClock}
          action={
            <select
              value={pageSize}
              onChange={(event) =>
                setPageSize(Number(event.target.value))
              }
              className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-600 outline-none"
            >
              {PAGE_SIZES.map((size) => (
                <option
                  key={size}
                  value={size}
                >
                  {size} / page
                </option>
              ))}
            </select>
          }
        >
          {error ? (
            <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-red-200 bg-red-50 px-6 py-10 text-center">
              <AlertCircle
                size={28}
                className="text-red-600"
              />
              <p className="text-sm font-semibold text-red-700">
                {error}
              </p>
              <button
                type="button"
                onClick={() => void loadLogs()}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
              >
                <RotateCcw size={16} />
                Reessayer
              </button>
            </div>
          ) : isLoading ? (
            <div className="space-y-3">
              {Array.from({
                length: 6,
              }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-xl bg-slate-100"
                />
              ))}
            </div>
          ) : logs.length === 0 ? (
            <EmptyState
              icon={FileClock}
              title={
                hasActiveFilters(filters)
                  ? "Aucun resultat"
                  : "Aucun audit log"
              }
              description={
                hasActiveFilters(filters)
                  ? "Aucun evenement ne correspond aux filtres selectionnes."
                  : "Les evenements apparaitront ici apres les actions dans Cortex AI."
              }
            />
          ) : (
            <>
              <div className="hidden overflow-x-auto rounded-xl border border-slate-200 md:block">
                <table className="min-w-[980px] w-full divide-y divide-slate-100 text-left">
                  <thead className="bg-slate-50">
                    <tr className="text-xs font-bold uppercase tracking-wide text-slate-500">
                      <th className="px-4 py-3">
                        Date / heure
                      </th>
                      <th className="px-4 py-3">
                        Utilisateur
                      </th>
                      <th className="px-4 py-3">
                        Role
                      </th>
                      <th className="px-4 py-3">
                        Action
                      </th>
                      <th className="px-4 py-3">
                        Ressource
                      </th>
                      <th className="px-4 py-3">
                        Details
                      </th>
                      <th className="px-4 py-3 text-right">
                        Voir
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {logs.map((log) => (
                      <tr
                        key={log.id}
                        onClick={() => setSelectedLog(log)}
                        className="cursor-pointer transition hover:bg-slate-50"
                      >
                        <td className="whitespace-nowrap px-4 py-4 text-sm font-semibold text-slate-700">
                          {formatDateTime(log.created_at)}
                        </td>
                        <td className="max-w-[220px] px-4 py-4">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            {log.email || "Email indisponible"}
                          </p>
                          <p className="mt-0.5 truncate text-xs text-slate-400">
                            {log.user_uid}
                          </p>
                        </td>
                        <td className="px-4 py-4">
                          <Badge className={roleTone(log.role)}>
                            {(log.role || "unknown").toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-4 py-4">
                          <Badge className={actionTone(log.action)}>
                            {log.action}
                          </Badge>
                        </td>
                        <td className="px-4 py-4 text-sm font-semibold text-slate-600">
                          {log.resource}
                        </td>
                        <td className="max-w-[240px] px-4 py-4 text-sm text-slate-500">
                          <span className="line-clamp-1">
                            {detailsPreview(log)}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setSelectedLog(log);
                            }}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-violet-50 hover:text-violet-700"
                            title="Voir les details"
                          >
                            <Eye size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="space-y-3 md:hidden">
                {logs.map((log) => (
                  <button
                    key={log.id}
                    type="button"
                    onClick={() => setSelectedLog(log)}
                    className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-900">
                          {formatDateTime(log.created_at)}
                        </p>
                        <p className="mt-1 truncate text-xs text-slate-500">
                          {log.email || log.user_uid}
                        </p>
                      </div>
                      <Badge className={roleTone(log.role)}>
                        {log.role || "unknown"}
                      </Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge className={actionTone(log.action)}>
                        {log.action}
                      </Badge>
                      <Badge className="bg-slate-50 text-slate-700 ring-slate-200">
                        {log.resource}
                      </Badge>
                    </div>
                    <p className="mt-3 text-sm text-slate-600">
                      {detailsPreview(log)}
                    </p>
                  </button>
                ))}
              </div>

              <div className="mt-5 flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm font-medium text-slate-500">
                  Page {page} sur {totalPages || 1} - {total} evenement(s)
                </p>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page <= 1 || isLoading}
                    className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <ChevronLeft size={17} />
                    Precedent
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage(page + 1)}
                    disabled={page >= totalPages || isLoading}
                    className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Suivant
                    <ChevronRight size={17} />
                  </button>
                </div>
              </div>
            </>
          )}
        </SectionCard>
      </div>

      {selectedLog ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 px-4 py-6 sm:items-center">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-violet-600">
                  Audit log #{selectedLog.id}
                </p>
                <h2 className="mt-1 text-lg font-semibold text-slate-950">
                  {selectedLog.action}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {formatDateTime(selectedLog.created_at)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                title="Fermer"
              >
                <X size={19} />
              </button>
            </div>

            <div className="max-h-[70vh] overflow-y-auto p-6">
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  [
                    "Email",
                    selectedLog.email || "Non disponible",
                  ],
                  [
                    "UID",
                    selectedLog.user_uid,
                  ],
                  [
                    "Role",
                    selectedLog.role || "unknown",
                  ],
                  [
                    "Ressource",
                    selectedLog.resource,
                  ],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                      {label}
                    </p>
                    <p className="mt-1 break-words text-sm font-semibold text-slate-800">
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-5 rounded-xl border border-slate-200">
                <div className="border-b border-slate-100 px-4 py-3">
                  <p className="text-sm font-semibold text-slate-950">
                    Details
                  </p>
                </div>
                <div className="divide-y divide-slate-100">
                  {detailsAsEntries(selectedLog).length === 0 ? (
                    <p className="px-4 py-4 text-sm text-slate-500">
                      Aucun detail disponible.
                    </p>
                  ) : (
                    detailsAsEntries(selectedLog).map(([key, value]) => (
                      <div
                        key={key}
                        className="grid gap-2 px-4 py-3 sm:grid-cols-[180px_1fr]"
                      >
                        <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                          {key.replaceAll("_", " ")}
                        </p>
                        <p className="break-words text-sm font-medium text-slate-700">
                          {value}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <div className="fixed bottom-5 right-5 hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 shadow-sm md:flex">
          <LoaderCircle
            size={16}
            className="animate-spin"
          />
          Chargement
        </div>
      ) : null}
    </div>
  );
}

export default AuditLogsPage;
