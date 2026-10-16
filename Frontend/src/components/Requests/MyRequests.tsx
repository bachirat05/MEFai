import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { User } from "firebase/auth";

import {
  CalendarDays,
  ChevronRight,
  CheckCircle2,
  Clock3,
  Eye,
  FileText,
  Inbox,
  RefreshCw,
  Search,
  UserRound,
  X,
  XCircle,
} from "lucide-react";

import {
  getMyLeaveRequests,
} from "../../services/api";

import type {
  AppPage,
  LeaveRequestRecord,
  LeaveRequestStatus,
} from "../../types";

type RequestFilter =
  | "all"
  | LeaveRequestStatus;

type MyRequestsProps = {
  user: User;
  onSelectPage?: (page: AppPage) => void;
};

const statusCopy: Record<
  LeaveRequestStatus,
  {
    label: string;
    tone: string;
    icon: typeof Clock3;
  }
> = {
  pending: {
    label: "En attente",
    tone: "bg-amber-50 text-amber-700 ring-amber-200",
    icon: Clock3,
  },
  accepted: {
    label: "Acceptée",
    tone: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    icon: CheckCircle2,
  },
  rejected: {
    label: "Refusée",
    tone: "bg-red-50 text-red-700 ring-red-200",
    icon: XCircle,
  },
};

const typeLabels: Record<string, string> = {
  conge_annuel: "Congé annuel",
  conge_maladie: "Congé maladie",
  conge_maternite: "Congé maternité",
  conge_paternite: "Congé paternité",
  conge_sans_solde: "Congé sans solde",
  conge_formation: "Congé formation",
  autre: "Autre",
};

function formatLeaveType(value: string): string {
  return (
    typeLabels[value] ??
    value
      .replaceAll("_", " ")
      .replace(/^\w/, (letter) =>
        letter.toUpperCase()
      )
  );
}

function parseDate(value: string): Date | null {
  const parsed = new Date(`${value}T00:00:00`);

  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

function formatDate(value: string): string {
  const parsed = parseDate(value);

  if (!parsed) {
    return value;
  }

  return parsed.toLocaleDateString("fr-FR");
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString(
    "fr-FR",
    {
      dateStyle: "short",
      timeStyle: "short",
    }
  );
}

function getDurationLabel(
  dateDebut: string,
  dateFin: string
): string {
  const start = parseDate(dateDebut);
  const end = parseDate(dateFin);

  if (!start || !end) {
    return "Non calculée";
  }

  const millisecondsPerDay =
    1000 * 60 * 60 * 24;

  const days = Math.max(
    1,
    Math.round(
      (end.getTime() - start.getTime()) /
        millisecondsPerDay
    ) + 1
  );

  return days === 1
    ? "1 jour"
    : `${days} jours`;
}

function StatusBadge({
  status,
}: {
  status: LeaveRequestStatus;
}) {
  const config = statusCopy[status];
  const Icon = config.icon;

  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${config.tone}`}>
      <Icon size={13} />
      {config.label}
    </span>
  );
}

function KpiCard({
  label,
  value,
  caption,
  tone,
  icon: Icon,
}: {
  label: string;
  value: number;
  caption: string;
  tone: string;
  icon: typeof UserRound;
}) {
  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
      <div className="flex items-center gap-4">
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${tone}`}>
          <Icon size={22} />
        </div>

        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-500">
            {label}
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-950">
            {value}
          </p>
          <p className="mt-1 text-xs font-medium text-slate-400">
            {caption}
          </p>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-violet-100 bg-white p-6 shadow-sm">
        <div className="h-4 w-32 animate-pulse rounded bg-slate-100" />
        <div className="mt-5 h-5 w-44 animate-pulse rounded bg-slate-100" />
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <div className="space-y-4">
            <div className="h-4 w-40 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-52 animate-pulse rounded bg-slate-100" />
            <div className="h-9 w-28 animate-pulse rounded-xl bg-slate-100" />
          </div>
          <div className="space-y-4">
            <div className="h-4 w-48 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-40 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-44 animate-pulse rounded bg-slate-100" />
          </div>
        </div>
      </div>

      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 animate-pulse rounded-2xl bg-slate-100" />
            <div className="flex-1 space-y-3">
              <div className="h-4 w-36 animate-pulse rounded bg-slate-100" />
              <div className="h-4 w-56 animate-pulse rounded bg-slate-100" />
            </div>
            <div className="h-6 w-24 animate-pulse rounded-full bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ProgressSteps({
  request,
}: {
  request: LeaveRequestRecord;
}) {
  const isDone =
    request.statut !== "pending";

  return (
    <div>
      <h3 className="text-sm font-bold text-slate-950">
        Progression de ma demande
      </h3>
      <div className="mt-4 space-y-5 border-l border-slate-200 pl-5">
        <div className="relative">
          <span className="absolute -left-[26px] top-1 h-3 w-3 rounded-full bg-violet-600 ring-4 ring-white" />
          <p className="text-sm font-semibold text-slate-900">
            Soumise
          </p>
          <p className="mt-1 text-xs font-medium text-slate-500">
            {formatDateTime(request.created_at)}
          </p>
        </div>
        <div className="relative">
          <span className="absolute -left-[26px] top-1 h-3 w-3 rounded-full bg-violet-600 ring-4 ring-white" />
          <p className="text-sm font-semibold text-slate-900">
            Statut actuel
          </p>
          <p className="mt-1 text-xs font-medium text-slate-500">
            {statusCopy[request.statut].label}
          </p>
        </div>
        <div className="relative">
          <span className={`absolute -left-[26px] top-1 h-3 w-3 rounded-full ring-4 ring-white ${
            isDone
              ? "bg-violet-600"
              : "bg-white ring-slate-300"
          }`} />
          <p className="text-sm font-semibold text-slate-900">
            Décision
          </p>
          <p className="mt-1 text-xs font-medium text-slate-500">
            {isDone
              ? statusCopy[request.statut].label
              : "En attente"}
          </p>
        </div>
      </div>
    </div>
  );
}

function FeaturedRequest({
  request,
  onSelect,
}: {
  request: LeaveRequestRecord;
  onSelect: () => void;
}) {
  return (
    <section className="mb-8 overflow-hidden rounded-2xl border border-violet-200 bg-white shadow-sm shadow-violet-100/70 ring-1 ring-violet-100">
      <div className="grid md:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]">
        <div className="p-5 md:p-6">
          <span className="inline-flex rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-violet-700">
            Dernière demande
          </span>
          <h2 className="mt-5 text-lg font-bold text-slate-950">
            {request.demande_id}
          </h2>

          <div className="mt-4 inline-flex items-center gap-2 rounded-xl bg-violet-50 px-3 py-2 text-sm font-bold text-violet-700">
            <CalendarDays size={16} />
            {formatLeaveType(request.type_conge)}
          </div>

          <p className="mt-4 text-sm font-semibold text-slate-700">
            {formatDate(request.date_debut)}
            <span className="px-2 text-slate-400">
              →
            </span>
            {formatDate(request.date_fin)}
          </p>
          <p className="mt-3 text-sm font-medium text-slate-600">
            Durée:{" "}
            <span className="font-semibold text-slate-900">
              {getDurationLabel(
                request.date_debut,
                request.date_fin
              )}
            </span>
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <StatusBadge status={request.statut} />
            <button
              type="button"
              onClick={onSelect}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-violet-100 bg-white px-4 text-sm font-bold text-violet-700 transition hover:bg-violet-50"
            >
              <Eye size={15} />
              Voir détails
            </button>
          </div>
        </div>

        <div className="border-t border-violet-100 bg-white/70 p-5 md:border-l md:border-t-0 md:p-6">
          <ProgressSteps request={request} />
        </div>
      </div>
    </section>
  );
}

function RequestRow({
  request,
  isSelected,
  onSelect,
}: {
  request: LeaveRequestRecord;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group w-full rounded-2xl border bg-white p-4 text-left shadow-sm shadow-slate-200/40 transition hover:border-violet-200 hover:shadow-md ${
        isSelected
          ? "border-violet-300 bg-violet-50/20 ring-1 ring-violet-200"
          : "border-slate-200"
      }`}
    >
      <div className="grid gap-4 md:grid-cols-[56px_minmax(0,1.5fr)_auto_auto_24px] md:items-center">
        <div className="hidden h-14 w-14 items-center justify-center rounded-2xl bg-violet-50 text-violet-700 md:flex">
          <FileText size={24} />
        </div>

        <div className="min-w-0">
          <p className="truncate text-xs font-semibold text-violet-700">
            {request.demande_id}
          </p>
          <p className="mt-2 truncate text-sm font-bold text-slate-950">
            {formatLeaveType(request.type_conge)}
          </p>
          <p className="mt-2 text-xs font-semibold text-slate-500">
            {formatDate(request.date_debut)}
            <span className="px-1.5 text-slate-400">
              →
            </span>
            {formatDate(request.date_fin)}
            <span className="px-3 text-slate-300">
              |
            </span>
            Durée:{" "}
            {getDurationLabel(
              request.date_debut,
              request.date_fin
            )}
          </p>
        </div>

        <StatusBadge status={request.statut} />

        <div className="text-left md:text-right">
          <p className="text-[11px] font-semibold text-slate-500">
            Créée le
        </p>
          <p className="mt-1 text-sm font-bold text-slate-900">
            {formatDateTime(request.created_at)}
          </p>
        </div>

        <ChevronRight
          size={20}
          className="hidden text-slate-400 transition group-hover:text-violet-600 md:block"
        />
      </div>
    </button>
  );
}

function DetailPanel({
  request,
  onClose,
}: {
  request: LeaveRequestRecord;
  onClose: () => void;
}) {
  const isDone =
    request.statut !== "pending";

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l border-slate-200 bg-white shadow-2xl shadow-slate-900/10 md:max-w-[440px] lg:sticky lg:top-0 lg:h-[calc(100vh-74px)] xl:max-w-[460px]">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="text-base font-bold text-slate-950">
            Détails de la demande
          </h2>
          <p className="mt-2 text-sm font-bold text-violet-700">
            {request.demande_id}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          aria-label="Fermer"
        >
          <X size={19} />
        </button>
      </div>

      <div className="sidebar-scroll flex-1 overflow-y-auto px-5 py-5">
        <div className="mb-6 flex flex-wrap items-center gap-2.5">
          <span className="rounded-xl bg-violet-50 px-3 py-2 text-sm font-bold text-violet-700 ring-1 ring-violet-100">
            {request.demande_id}
          </span>
          <StatusBadge status={request.statut} />
        </div>

        <section>
          <h3 className="text-sm font-bold text-slate-950">
            Informations de la demande
          </h3>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                Type de congé
              </dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {formatLeaveType(request.type_conge)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                Durée
              </dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {getDurationLabel(
                  request.date_debut,
                  request.date_fin
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                Date début
              </dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {formatDate(request.date_debut)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                Date fin
              </dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {formatDate(request.date_fin)}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-semibold text-slate-500">
                Date création
              </dt>
              <dd className="mt-1 font-semibold text-slate-900">
                {formatDateTime(request.created_at)}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-semibold text-slate-500">
                Motif
              </dt>
              <dd className="mt-2 rounded-xl bg-slate-50 p-3.5 text-sm leading-6 text-slate-600 ring-1 ring-inset ring-slate-100">
                {request.motif}
              </dd>
            </div>
          </dl>
        </section>

        {request.message ? (
          <section className="mt-7 border-t border-slate-100 pt-6">
            <h3 className="text-sm font-bold text-slate-950">
              Informations
            </h3>
            <p className="mt-3 rounded-xl bg-slate-50 p-3.5 text-sm leading-6 text-slate-600 ring-1 ring-inset ring-slate-100">
              {request.message}
            </p>
          </section>
        ) : null}

        <section className="mt-7 border-t border-slate-100 pt-6">
          <h3 className="text-sm font-bold text-slate-950">
            Historique
          </h3>
          <div className="mt-4 space-y-5 border-l border-slate-200 pl-5">
            <div className="relative">
              <span className="absolute -left-[26px] top-1 h-3 w-3 rounded-full bg-violet-600 ring-4 ring-white" />
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Demande soumise
                  </p>
                  <p className="mt-1 text-xs font-medium text-slate-500">
                    Par vous
                  </p>
                </div>
                <p className="shrink-0 text-xs font-medium text-slate-500">
                  {formatDateTime(request.created_at)}
                </p>
              </div>
            </div>
            <div className="relative">
              <span className="absolute -left-[26px] top-1 h-3 w-3 rounded-full bg-violet-600 ring-4 ring-white" />
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Statut actuel
                  </p>
                  <p className="mt-1 text-xs font-medium text-slate-500">
                    {statusCopy[request.statut].label}
                  </p>
                </div>
                <p className="shrink-0 text-xs font-medium text-slate-500">
                  {formatDateTime(request.created_at)}
                </p>
              </div>
            </div>
            <div className="relative">
              <span className={`absolute -left-[26px] top-1 h-3 w-3 rounded-full ring-4 ring-white ${
                isDone
                  ? "bg-violet-600"
                  : "bg-white ring-slate-300"
              }`} />
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Décision
                </p>
                <p className="mt-1 text-xs font-medium text-slate-500">
                  {isDone
                    ? statusCopy[request.statut].label
                    : "En attente"}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div className="border-t border-slate-100 px-5 py-4">
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-12 w-full items-center justify-center rounded-xl border border-violet-200 bg-white px-4 text-sm font-bold text-violet-700 transition hover:bg-violet-50"
        >
          Fermer
        </button>
      </div>
    </aside>
  );
}

function MyRequests({
  user,
  onSelectPage,
}: MyRequestsProps) {
  const [requests, setRequests] =
    useState<LeaveRequestRecord[]>([]);
  const [loading, setLoading] =
    useState(true);
  const [error, setError] =
    useState("");
  const [selectedRequest, setSelectedRequest] =
    useState<LeaveRequestRecord | null>(null);
  const [isDetailOpen, setIsDetailOpen] =
    useState(true);
  const [searchQuery, setSearchQuery] =
    useState("");
  const [statusFilter, setStatusFilter] =
    useState<RequestFilter>("all");
  const [typeFilter, setTypeFilter] =
    useState("all");

  const loadRequests = useCallback(
    async (): Promise<void> => {
      try {
        setLoading(true);
        setError("");

        const token =
          await user.getIdToken();
        const data =
          await getMyLeaveRequests(token);

        setRequests(data);
        setSelectedRequest((current) => {
          if (!current) {
            return null;
          }

          return (
            data.find(
              (request) =>
                request.demande_id ===
                current.demande_id
            ) ?? null
          );
        });
      } catch (loadError: unknown) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Impossible de charger les demandes."
        );
      } finally {
        setLoading(false);
      }
    },
    [user]
  );

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  const counts = useMemo(
    () =>
      requests.reduce(
        (result, request) => ({
          ...result,
          [request.statut]:
            result[request.statut] + 1,
        }),
        {
          pending: 0,
          accepted: 0,
          rejected: 0,
        }
      ),
    [requests]
  );

  const leaveTypes = useMemo(
    () =>
      Array.from(
        new Set(
          requests.map(
            (request) => request.type_conge
          )
        )
      ).sort((left, right) =>
        formatLeaveType(left).localeCompare(
          formatLeaveType(right),
          "fr"
        )
      ),
    [requests]
  );

  const hasActiveFilters =
    searchQuery.trim() !== "" ||
    statusFilter !== "all" ||
    typeFilter !== "all";

  const filteredRequests = useMemo(() => {
    const normalizedQuery =
      searchQuery.trim().toLowerCase();

    return requests.filter((request) => {
      const matchesSearch =
        !normalizedQuery ||
        [
          request.demande_id,
          request.type_conge,
          formatLeaveType(request.type_conge),
          request.motif,
        ].some((value) =>
          value
            .toLowerCase()
            .includes(normalizedQuery)
        );

      const matchesStatus =
        statusFilter === "all" ||
        request.statut === statusFilter;

      const matchesType =
        typeFilter === "all" ||
        request.type_conge === typeFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesType
      );
    });
  }, [
    requests,
    searchQuery,
    statusFilter,
    typeFilter,
  ]);

  const sortedFilteredRequests = useMemo(
    () =>
      [...filteredRequests].sort((left, right) => {
        const leftTime =
          new Date(left.created_at).getTime();
        const rightTime =
          new Date(right.created_at).getTime();

        if (
          Number.isNaN(leftTime) ||
          Number.isNaN(rightTime)
        ) {
          return 0;
        }

        return rightTime - leftTime;
      }),
    [filteredRequests]
  );

  const latestRequest =
    sortedFilteredRequests[0] ?? null;
  const historyRequests =
    latestRequest
      ? sortedFilteredRequests.filter(
          (request) =>
            request.demande_id !==
            latestRequest.demande_id
        )
      : [];
  const detailRequest =
    selectedRequest ??
    (isDetailOpen ? latestRequest : null);

  const openRequest = (
    request: LeaveRequestRecord
  ): void => {
    setSelectedRequest(request);
    setIsDetailOpen(true);
  };

  const closeDetails = (): void => {
    setSelectedRequest(null);
    setIsDetailOpen(false);
  };

  const resetFilters = (): void => {
    setSearchQuery("");
    setStatusFilter("all");
    setTypeFilter("all");
  };

  return (
    <div className="h-full overflow-y-auto bg-slate-50">
      <div className={`mx-auto grid w-full ${
        detailRequest
          ? "max-w-[1500px] lg:grid-cols-[minmax(0,1fr)_420px] xl:grid-cols-[minmax(0,1fr)_460px]"
          : "max-w-[1400px]"
      }`}>
        <main className="min-w-0 px-5 py-6 md:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Mes demandes
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Suivez l’état de vos demandes de congé en temps réel.
          </p>
        </header>

        <section className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            label="Total demandes"
            value={requests.length}
            caption="Toutes périodes"
            icon={UserRound}
            tone="bg-violet-100 text-violet-700"
          />
          <KpiCard
            label="En attente"
            value={counts.pending}
            caption="À suivre"
            icon={Clock3}
            tone="bg-amber-100 text-amber-700"
          />
          <KpiCard
            label="Acceptées"
            value={counts.accepted}
            caption="Demandes validées"
            icon={CheckCircle2}
            tone="bg-emerald-100 text-emerald-700"
          />
          <KpiCard
            label="Refusées"
            value={counts.rejected}
            caption="Demandes refusées"
            icon={XCircle}
            tone="bg-red-100 text-red-700"
          />
        </section>

        <section className="mb-4 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm shadow-slate-200/50">
          <div className="flex flex-col gap-3 md:flex-row md:flex-wrap xl:flex-nowrap">
            <label className="relative block min-w-0 md:basis-full xl:basis-auto xl:flex-1">
              <span className="sr-only">
                Rechercher
              </span>
              <Search
                size={18}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={searchQuery}
                onChange={(event) =>
                  setSearchQuery(
                    event.target.value
                  )
                }
                placeholder="Rechercher référence, type, motif..."
                className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-3 text-sm font-medium text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              />
            </label>

            <label className="block min-w-0 md:w-[180px] xl:w-[200px]">
              <span className="sr-only">
                Filtrer par statut
              </span>
              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(
                    event.target
                      .value as RequestFilter
                  )
                }
                className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              >
                <option value="all">
                  Statut: Tous
                </option>
                <option value="pending">
                  En attente
                </option>
                <option value="accepted">
                  Acceptées
                </option>
                <option value="rejected">
                  Refusées
                </option>
              </select>
            </label>

            <label className="block min-w-0 md:w-[200px] xl:w-[220px]">
              <span className="sr-only">
                Filtrer par type
              </span>
              <select
                value={typeFilter}
                onChange={(event) =>
                  setTypeFilter(
                    event.target.value
                  )
                }
                className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
              >
                <option value="all">
                  Type: Tous
                </option>
                {leaveTypes.map((type) => (
                  <option
                    key={type}
                    value={type}
                  >
                    {formatLeaveType(type)}
                  </option>
                ))}
              </select>
            </label>

            {hasActiveFilters ? (
              <div className="flex md:w-auto">
                <button
                  type="button"
                  onClick={resetFilters}
                  className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-600 transition hover:border-violet-200 hover:bg-violet-50 hover:text-violet-700 sm:w-auto"
                >
                  <RefreshCw size={16} />
                  Reset
                </button>
              </div>
            ) : null}
          </div>
        </section>

        <p className="mb-3 border-t border-violet-100 pt-3 text-xs font-semibold text-slate-500">
          {filteredRequests.length} demandes trouvées
        </p>

        {error ? (
          <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-red-100 bg-red-50 px-5 py-4 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between">
            <p>{error}</p>
            <button
              type="button"
              onClick={() => void loadRequests()}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-2 font-semibold text-red-700 ring-1 ring-red-200 transition hover:bg-red-100"
            >
              <RefreshCw size={16} />
              Réessayer
            </button>
          </div>
        ) : null}

        {loading ? (
          <LoadingSkeleton />
        ) : filteredRequests.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <Inbox size={24} />
            </div>
            <p className="mt-4 text-sm font-semibold text-slate-800">
              {requests.length === 0
                ? "Aucune demande pour le moment"
                : "Aucune demande ne correspond à vos filtres."}
            </p>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
              {requests.length === 0
                ? "Vos demandes de congé apparaîtront ici après leur création."
                : "Essayez de modifier votre recherche ou de réinitialiser les filtres."}
            </p>
            {requests.length === 0 ? (
              <button
                type="button"
                onClick={() =>
                  onSelectPage?.("leave")
                }
                className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 text-sm font-bold text-white shadow-sm shadow-violet-200 transition hover:bg-violet-700"
              >
                <CalendarDays size={17} />
                Nouvelle demande
              </button>
            ) : hasActiveFilters ? (
              <button
                type="button"
                onClick={resetFilters}
                className="mt-5 rounded-xl bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-700 transition hover:bg-violet-100"
              >
                Réinitialiser les filtres
              </button>
            ) : null}
          </div>
        ) : latestRequest ? (
          <>
            <FeaturedRequest
              request={latestRequest}
              onSelect={() =>
                openRequest(latestRequest)
              }
            />

            <section>
              <h2 className="mb-4 text-xl font-bold text-slate-950">
                Historique de mes demandes
              </h2>
              {historyRequests.length > 0 ? (
                <div className="space-y-3">
                  {historyRequests.map((request) => (
                    <RequestRow
                      key={request.demande_id}
                      request={request}
                      isSelected={
                        detailRequest?.demande_id ===
                        request.demande_id
                      }
                      onSelect={() =>
                        openRequest(request)
                      }
                    />
                  ))}
                  <div className="flex items-center gap-4 py-5">
                    <div className="h-px flex-1 bg-slate-200" />
                    <span className="text-xs font-medium text-slate-500">
                      Fin de la liste
                    </span>
                    <div className="h-px flex-1 bg-slate-200" />
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
                  <p className="text-sm font-semibold text-slate-800">
                    Aucune autre demande à afficher.
                  </p>
                </div>
              )}
            </section>
          </>
        ) : null}
        </main>

        {detailRequest ? (
          <div className="hidden min-w-0 lg:block">
            <DetailPanel
              request={detailRequest}
              onClose={closeDetails}
            />
          </div>
        ) : null}
      </div>

      {selectedRequest ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-[1px] lg:hidden">
          <button
            type="button"
            aria-label="Fermer les détails"
            className="hidden flex-1 cursor-default md:block"
            onClick={closeDetails}
          />
          <DetailPanel
            request={selectedRequest}
            onClose={closeDetails}
          />
        </div>
      ) : null}
    </div>
  );
}

export default MyRequests;
