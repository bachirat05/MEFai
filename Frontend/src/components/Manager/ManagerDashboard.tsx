import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type MouseEvent,
} from "react";

import type { User } from "firebase/auth";

import {
  Check,
  CheckCircle2,
  Clock3,
  Eye,
  Inbox,
  Loader2,
  RefreshCw,
  Search,
  UserRound,
  X,
  XCircle,
} from "lucide-react";

import {
  getManagerLeaveRequests,
  updateLeaveRequestStatus,
} from "../../services/api";

import type {
  LeaveRequestStatus,
  ManagerLeaveRequest,
} from "../../types";

type ManagerDashboardProps = {
  user: User;
};

type StatusFilter =
  | "all"
  | LeaveRequestStatus;

type ConfirmationState = {
  request: ManagerLeaveRequest;
  statut: Extract<LeaveRequestStatus, "accepted" | "rejected">;
};

const statusCopy: Record<
  LeaveRequestStatus,
  {
    label: string;
    tone: string;
    dot: string;
    icon: typeof Clock3;
  }
> = {
  pending: {
    label: "En attente",
    tone: "bg-amber-50 text-amber-700 ring-amber-200",
    dot: "bg-amber-500",
    icon: Clock3,
  },
  accepted: {
    label: "Acceptée",
    tone: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    dot: "bg-emerald-500",
    icon: CheckCircle2,
  },
  rejected: {
    label: "Refusée",
    tone: "bg-red-50 text-red-700 ring-red-200",
    dot: "bg-red-500",
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
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex items-start justify-between">
            <div className="h-3.5 w-36 animate-pulse rounded bg-slate-100" />
            <div className="h-5 w-20 animate-pulse rounded-full bg-slate-100" />
          </div>
          <div className="mt-5 h-4 w-28 animate-pulse rounded bg-slate-100" />
          <div className="mt-2 h-3 w-44 animate-pulse rounded bg-slate-100" />
          <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4">
            <div className="h-9 animate-pulse rounded-xl bg-slate-100" />
            <div className="h-9 animate-pulse rounded-xl bg-slate-100" />
            <div className="h-9 animate-pulse rounded-xl bg-slate-100" />
            <div className="h-9 animate-pulse rounded-xl bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

function RequestCard({
  request,
  isSelected,
  onSelect,
}: {
  request: ManagerLeaveRequest;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group flex h-full w-full flex-col rounded-xl border bg-white p-5 text-left shadow-sm shadow-slate-200/40 transition duration-150 hover:-translate-y-0.5 hover:border-violet-200 hover:shadow-md ${
        isSelected
          ? "border-violet-300 bg-violet-50/20 ring-1 ring-violet-200"
          : "border-slate-200"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 truncate text-xs font-semibold text-violet-700">
          {request.demande_id}
        </p>
        <StatusBadge status={request.statut} />
      </div>

      <div className="mt-4 border-b border-slate-100 pb-4">
        <p className="truncate text-sm font-semibold text-slate-950">
          {request.employe_id}
        </p>
        {request.employee_email ? (
          <p className="mt-1 truncate text-xs text-slate-500">
            {request.employee_email}
          </p>
        ) : null}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Type
          </p>
          <p className="mt-1 truncate text-sm font-medium text-slate-800">
            {formatLeaveType(request.type_conge)}
          </p>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Durée
          </p>
          <p className="mt-1 text-sm font-medium text-slate-800">
            {getDurationLabel(
              request.date_debut,
              request.date_fin
            )}
          </p>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Période
          </p>
          <p className="mt-1 truncate text-sm font-medium text-slate-800">
            {formatDate(request.date_debut)}
            <span className="px-1.5 text-slate-400">
              →
            </span>
            {formatDate(request.date_fin)}
          </p>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Créée le
          </p>
          <p className="mt-1 truncate text-sm font-medium text-slate-800">
            {formatDateTime(request.created_at)}
          </p>
        </div>
      </div>

      <div className="mt-auto flex justify-end pt-4">
        <span className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-violet-700 transition group-hover:bg-violet-50">
          <Eye size={14} />
          Voir détails
        </span>
      </div>
    </button>
  );
}

function DetailPanel({
  request,
  updatingId,
  selectedStatus,
  SelectedStatusIcon,
  onClose,
  onDecision,
}: {
  request: ManagerLeaveRequest;
  updatingId: string | null;
  selectedStatus: (typeof statusCopy)[LeaveRequestStatus] | null;
  SelectedStatusIcon: typeof Clock3 | undefined;
  onClose: () => void;
  onDecision: (
    event: MouseEvent<HTMLButtonElement>,
    request: ManagerLeaveRequest,
    statut: Extract<
      LeaveRequestStatus,
      "accepted" | "rejected"
    >
  ) => void;
}) {
  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-l border-slate-200 bg-white shadow-2xl shadow-slate-900/10 lg:sticky lg:top-0 lg:h-[calc(100vh-74px)] lg:max-w-[440px] xl:max-w-[460px]">
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
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-violet-100 text-base font-bold text-violet-700">
              {request.employe_id
                .split(/[ .@_-]+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((part) =>
                  part[0]?.toUpperCase()
                )
                .join("") || "U"}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-slate-950">
                {request.employe_id}
              </p>
              {request.employee_email ? (
                <p className="mt-1 truncate text-xs font-medium text-slate-500">
                  {request.employee_email}
                </p>
              ) : null}
            </div>
          </div>
          <StatusBadge status={request.statut} />
        </div>

        <section>
          <h3 className="text-sm font-bold text-slate-950">
            Informations de la demande
          </h3>
          <dl className="mt-4 space-y-4 text-sm">
            <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
              <dt className="text-xs font-semibold text-slate-500">
                Type de congé
              </dt>
              <dd className="font-semibold text-slate-900">
                {formatLeaveType(request.type_conge)}
              </dd>
            </div>
            <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
              <dt className="text-xs font-semibold text-slate-500">
                Durée
              </dt>
              <dd className="font-semibold text-slate-900">
                {getDurationLabel(
                  request.date_debut,
                  request.date_fin
                )}
              </dd>
            </div>
            <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
              <dt className="text-xs font-semibold text-slate-500">
                Période
              </dt>
              <dd className="font-semibold text-slate-900">
                {formatDate(request.date_debut)}
                <span className="px-1.5 text-slate-400">
                  →
                </span>
                {formatDate(request.date_fin)}
              </dd>
            </div>
            <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
              <dt className="text-xs font-semibold text-slate-500">
                Créée le
              </dt>
              <dd className="font-semibold text-slate-900">
                {formatDateTime(request.created_at)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                Motif
              </dt>
              <dd className="mt-2 rounded-xl bg-slate-50 p-3.5 text-sm leading-6 text-slate-600 ring-1 ring-inset ring-slate-100">
                {request.motif}
              </dd>
            </div>
          </dl>
        </section>

        <section className="mt-7 border-t border-slate-100 pt-6">
          <h3 className="text-sm font-bold text-slate-950">
            Suivi
          </h3>
          <dl className="mt-4 grid gap-4 text-sm">
            <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
              <dt className="text-xs font-semibold text-slate-500">
                Créée le
              </dt>
              <dd className="font-semibold text-slate-900">
                {formatDateTime(request.created_at)}
              </dd>
            </div>
            <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
              <dt className="text-xs font-semibold text-slate-500">
                Statut actuel
              </dt>
              <dd>
                <StatusBadge status={request.statut} />
              </dd>
            </div>
          </dl>
        </section>
      </div>

      <div className="border-t border-slate-100 px-5 py-4">
        {request.statut === "pending" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              disabled={updatingId === request.demande_id}
              onClick={(event) =>
                onDecision(
                  event,
                  request,
                  "rejected"
                )
              }
              className="inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 text-sm font-bold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <XCircle size={18} />
              Refuser
            </button>
            <button
              type="button"
              disabled={updatingId === request.demande_id}
              onClick={(event) =>
                onDecision(
                  event,
                  request,
                  "accepted"
                )
              }
              className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 text-sm font-bold text-white shadow-sm shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Check size={18} />
              Accepter
            </button>
          </div>
        ) : (
          <div className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold ring-1 ring-inset ${selectedStatus?.tone ?? ""}`}>
            {SelectedStatusIcon ? (
              <SelectedStatusIcon size={18} />
            ) : null}
            {selectedStatus?.label}
          </div>
        )}
      </div>
    </aside>
  );
}

function ManagerDashboard({
  user,
}: ManagerDashboardProps) {
  const [requests, setRequests] =
    useState<ManagerLeaveRequest[]>([]);
  const [isLoading, setIsLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);
  const [updatingId, setUpdatingId] =
    useState<string | null>(null);
  const [selectedRequest, setSelectedRequest] =
    useState<ManagerLeaveRequest | null>(null);
  const [confirmation, setConfirmation] =
    useState<ConfirmationState | null>(null);
  const [searchQuery, setSearchQuery] =
    useState("");
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>("all");
  const [typeFilter, setTypeFilter] =
    useState("all");

  const loadRequests = useCallback(
    async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const token = await user.getIdToken();
        const data =
          await getManagerLeaveRequests(token);

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
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Impossible de charger les demandes."
        );
      } finally {
        setIsLoading(false);
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
          request.employe_id,
          request.employee_email ?? "",
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

  const resetFilters = (): void => {
    setSearchQuery("");
    setStatusFilter("all");
    setTypeFilter("all");
  };

  const handleStatusUpdate = async (
    request: ManagerLeaveRequest,
    statut: Extract<
      LeaveRequestStatus,
      "accepted" | "rejected"
    >
  ): Promise<void> => {
    setUpdatingId(request.demande_id);
    setError(null);

    try {
      const token = await user.getIdToken();
      const updatedRequest =
        await updateLeaveRequestStatus(
          token,
          request.demande_id,
          statut
        );

      setRequests((current) =>
        current.map((item) =>
          item.demande_id ===
          updatedRequest.demande_id
            ? updatedRequest
            : item
        )
      );
      setSelectedRequest((current) =>
        current?.demande_id ===
        updatedRequest.demande_id
          ? updatedRequest
          : current
      );
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "Impossible de mettre à jour la demande."
      );
    } finally {
      setUpdatingId(null);
      setConfirmation(null);
    }
  };

  const openConfirmation = (
    event: MouseEvent<HTMLButtonElement>,
    request: ManagerLeaveRequest,
    statut: Extract<
      LeaveRequestStatus,
      "accepted" | "rejected"
    >
  ): void => {
    event.stopPropagation();
    setConfirmation({
      request,
      statut,
    });
  };

  const detailRequest = selectedRequest;

  const selectedStatus = detailRequest
    ? statusCopy[detailRequest.statut]
    : null;
  const SelectedStatusIcon =
    selectedStatus?.icon;

  return (
    <div className="h-full overflow-y-auto bg-slate-50">
      <div className={`mx-auto grid w-full transition-[max-width] duration-200 ${
        detailRequest
          ? "max-w-[1500px] lg:grid-cols-[minmax(0,1fr)_420px] xl:grid-cols-[minmax(0,1fr)_460px]"
          : "max-w-[1400px]"
      }`}>
        <main className="min-w-0 px-5 py-6 md:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Espace Manager
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Gérez et validez les demandes de congé de votre équipe.
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
            caption="À traiter"
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
                placeholder="Rechercher employé, email, référence..."
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
                      .value as StatusFilter
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

        <p className="mb-3 text-xs font-semibold text-slate-500">
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

        {isLoading ? (
          <LoadingSkeleton />
        ) : filteredRequests.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <Inbox size={24} />
            </div>
            <p className="mt-4 text-sm font-semibold text-slate-800">
              {requests.length === 0
                ? "Aucune demande de congé à afficher."
                : "Aucune demande ne correspond à vos filtres."}
            </p>
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={resetFilters}
                className="mt-4 rounded-xl bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-700 transition hover:bg-violet-100"
              >
                Réinitialiser les filtres
              </button>
            ) : null}
          </div>
        ) : (
          <section className={`grid grid-cols-1 gap-4 md:grid-cols-2 ${
            detailRequest
              ? "xl:grid-cols-2"
              : "xl:grid-cols-3"
          }`}>
            {filteredRequests.map((request) => (
              <RequestCard
                key={request.demande_id}
                request={request}
                isSelected={
                  detailRequest?.demande_id ===
                  request.demande_id
                }
                onSelect={() =>
                  setSelectedRequest(request)
                }
              />
            ))}
          </section>
        )}
        </main>

        {detailRequest ? (
          <>
            <div className="hidden min-w-0 lg:block">
              <DetailPanel
                request={detailRequest}
                updatingId={updatingId}
                selectedStatus={selectedStatus}
                SelectedStatusIcon={SelectedStatusIcon}
                onClose={() =>
                  setSelectedRequest(null)
                }
                onDecision={openConfirmation}
              />
            </div>

            {selectedRequest ? (
              <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-[1px] lg:hidden">
                <button
                  type="button"
                  aria-label="Fermer les détails"
                  className="hidden flex-1 cursor-default sm:block"
                  onClick={() =>
                    setSelectedRequest(null)
                  }
                />
                <DetailPanel
                  request={selectedRequest}
                  updatingId={updatingId}
                  selectedStatus={selectedStatus}
                  SelectedStatusIcon={SelectedStatusIcon}
                  onClose={() =>
                    setSelectedRequest(null)
                  }
                  onDecision={openConfirmation}
                />
              </div>
            ) : null}
          </>
        ) : null}

      </div>

      {confirmation ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl shadow-slate-900/20">
            <h2 className="text-lg font-bold text-slate-950">
              Confirmation
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {confirmation.statut === "accepted"
                ? "Confirmer l’acceptation de cette demande ?"
                : "Confirmer le refus de cette demande ?"}
            </p>
            <p className="mt-2 text-sm font-semibold text-violet-700">
              {confirmation.request.demande_id}
            </p>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() =>
                  setConfirmation(null)
                }
                className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
              >
                Annuler
              </button>
              <button
                type="button"
                disabled={
                  updatingId ===
                  confirmation.request.demande_id
                }
                onClick={() =>
                  void handleStatusUpdate(
                    confirmation.request,
                    confirmation.statut
                  )
                }
                className={`inline-flex h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${
                  confirmation.statut === "accepted"
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {updatingId ===
                confirmation.request.demande_id ? (
                  <Loader2
                    size={17}
                    className="animate-spin"
                  />
                ) : confirmation.statut ===
                  "accepted" ? (
                  <Check size={17} />
                ) : (
                  <XCircle size={17} />
                )}
                Confirmer
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default ManagerDashboard;
