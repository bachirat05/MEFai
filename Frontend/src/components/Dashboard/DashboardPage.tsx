import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type { User } from "firebase/auth";

import {
  ArrowRight,
  BarChart3,
  Bot,
  CalendarDays,
  FileText,
  Clock,
  MessageSquare,
  Server,
  Upload,
} from "lucide-react";

import {
  getAdminActivity,
  getDocuments,
  getManagerLeaveRequests,
  getMyLeaveRequests,
  getSystemStatus,
  type ActivitySummary,
  type DailyActivity,
  type RagDocument,
  type RecentActivity,
  type SystemStatus,
} from "../../services/api";

import type {
  AppPage,
  Conversation,
  LeaveRequestRecord,
  ManagerLeaveRequest,
  UserRole,
} from "../../types";

type DashboardPageProps = {
  user: User;
  role: UserRole;
  isAdmin: boolean;
  isManager: boolean;
  conversations: Conversation[];
  onSelectPage: (page: AppPage) => void;
  onSelectConversation: (id: number) => void;
};

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function fileTone(type: string): string {
  if (type === "pdf") {
    return "bg-red-500 text-white";
  }

  if (type === "docx") {
    return "bg-blue-600 text-white";
  }

  return "bg-sky-500 text-white";
}

function systemIsOnline(status: SystemStatus | null): boolean {
  return Boolean(
    status &&
      status.ollama === "online" &&
      status.rag === "ready" &&
      status.n8n === "configured"
  );
}

function formatShortDate(dateValue: string): string {
  return new Intl.DateTimeFormat(
    "fr-FR",
    {
      weekday: "short",
    }
  ).format(new Date(`${dateValue}T00:00:00`));
}

function formatRelativeTime(value: string): string {
  const timestamp = new Date(value).getTime();
  const diffMs = Date.now() - timestamp;
  const diffMinutes = Math.max(
    0,
    Math.round(diffMs / 60000)
  );

  if (diffMinutes < 1) {
    return "A l'instant";
  }

  if (diffMinutes < 60) {
    return `Il y a ${diffMinutes} min`;
  }

  const diffHours = Math.round(diffMinutes / 60);

  if (diffHours < 24) {
    return `Il y a ${diffHours} h`;
  }

  if (diffHours < 48) {
    return "Hier";
  }

  return new Intl.DateTimeFormat(
    "fr-FR",
    {
      day: "2-digit",
      month: "short",
    }
  ).format(new Date(value));
}

function detailValue(
  activity: RecentActivity,
  key: string
): string | null {
  const details = activity.details;

  if (
    typeof details !== "object" ||
    details === null ||
    !(key in details)
  ) {
    return null;
  }

  const value = details[key];

  if (
    typeof value === "string" ||
    typeof value === "number"
  ) {
    return String(value);
  }

  return null;
}

function activityLabel(activity: RecentActivity): {
  title: string;
  subtitle: string;
  tone: string;
} {
  const filename = detailValue(
    activity,
    "filename"
  );
  const demandeId = detailValue(
    activity,
    "demande_id"
  );

  if (activity.action === "DOCUMENT_UPLOAD") {
    return {
      title: "Document ajoute",
      subtitle: filename ?? "documents",
      tone: "bg-blue-100 text-blue-700",
    };
  }

  if (activity.action === "DOCUMENT_DELETE") {
    return {
      title: "Document supprime",
      subtitle: filename ?? "documents",
      tone: "bg-red-100 text-red-700",
    };
  }

  if (activity.action === "LEAVE_CREATED") {
    return {
      title: "Nouvelle demande de conge",
      subtitle: activity.email ?? demandeId ?? "leave_request",
      tone: "bg-emerald-100 text-emerald-700",
    };
  }

  if (activity.action === "LEAVE_ACCEPTED") {
    return {
      title: "Demande acceptee",
      subtitle: demandeId ?? activity.email ?? "leave_request",
      tone: "bg-violet-100 text-violet-700",
    };
  }

  if (activity.action === "LEAVE_REJECTED") {
    return {
      title: "Demande refusee",
      subtitle: demandeId ?? activity.email ?? "leave_request",
      tone: "bg-amber-100 text-amber-700",
    };
  }

  return {
    title: activity.action,
    subtitle: activity.resource,
    tone: "bg-slate-100 text-slate-600",
  };
}

function ActivityChart({
  daily,
}: {
  daily: DailyActivity[];
}) {
  const width = 720;
  const height = 210;
  const paddingX = 40;
  const paddingTop = 18;
  const paddingBottom = 34;
  const chartHeight =
    height - paddingTop - paddingBottom;
  const chartWidth = width - paddingX * 2;

  const series = daily.map((day) => ({
    date: day.date,
    conversations: day.chat_messages,
    documents: day.documents,
    leave:
      day.leave_requests +
      day.manager_actions,
  }));

  const maxValue = Math.max(
    1,
    ...series.flatMap((point) => [
      point.conversations,
      point.documents,
      point.leave,
    ])
  );

  const pointFor = (
    value: number,
    index: number
  ): [number, number] => {
    const x =
      paddingX +
      (series.length <= 1
        ? chartWidth / 2
        : (chartWidth * index) /
          (series.length - 1));
    const y =
      paddingTop +
      chartHeight -
      (value / maxValue) * chartHeight;

    return [x, y];
  };

  const pathFor = (
    key: "conversations" | "documents" | "leave"
  ): string =>
    series
      .map((point, index) => {
        const [x, y] = pointFor(
          point[key],
          index
        );

        return `${index === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");

  return (
    <div className="px-5 py-4">
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs font-semibold text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-violet-500" />
          Conversations
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500" />
          Documents
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          RH
        </span>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-[210px] w-full overflow-visible"
        role="img"
        aria-label="Activite applicative des sept derniers jours"
      >
        {[0, 0.5, 1].map((ratio) => {
          const y =
            paddingTop +
            chartHeight -
            ratio * chartHeight;

          return (
            <g key={ratio}>
              <line
                x1={paddingX}
                x2={width - paddingX}
                y1={y}
                y2={y}
                stroke="#e2e8f0"
                strokeWidth="1"
              />
              <text
                x="8"
                y={y + 4}
                className="fill-slate-400 text-[11px] font-semibold"
              >
                {Math.round(maxValue * ratio)}
              </text>
            </g>
          );
        })}

        <path
          d={pathFor("conversations")}
          fill="none"
          stroke="#8b5cf6"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d={pathFor("documents")}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d={pathFor("leave")}
          fill="none"
          stroke="#10b981"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {series.map((point, index) => {
          const [x] = pointFor(
            point.conversations,
            index
          );

          return (
            <text
              key={point.date}
              x={x}
              y={height - 10}
              textAnchor="middle"
              className="fill-slate-500 text-[11px] font-semibold"
            >
              {formatShortDate(point.date)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function DashboardCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md hover:shadow-slate-200/60 ${className}`}>
      {children}
    </section>
  );
}

function CardHeader({
  title,
  action,
}: {
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-14 items-center justify-between gap-4 border-b border-slate-100 px-5 py-3">
      <h2 className="text-[15px] font-semibold text-slate-950">
        {title}
      </h2>
      {action}
    </div>
  );
}

function KpiCard({
  title,
  value,
  caption,
  icon: Icon,
  tone,
}: {
  title: string;
  value: React.ReactNode;
  caption: string;
  icon: typeof FileText;
  tone: "violet" | "emerald" | "blue" | "amber";
}) {
  const toneClass = {
    violet: "bg-violet-100 text-violet-700 border-violet-200",
    emerald: "bg-emerald-100 text-emerald-700 border-emerald-200",
    blue: "bg-blue-100 text-blue-700 border-blue-200",
    amber: "bg-amber-100 text-amber-700 border-amber-200",
  }[tone];

  const cardToneClass = {
    violet: "border-violet-100 bg-violet-50/35",
    emerald: "border-emerald-100 bg-emerald-50/35",
    blue: "border-blue-100 bg-blue-50/35",
    amber: "border-amber-100 bg-amber-50/40",
  }[tone];

  return (
    <DashboardCard className={`p-4 ${cardToneClass}`}>
      <div className="flex items-center gap-3.5">
        <div className={`flex h-13 w-13 shrink-0 items-center justify-center rounded-full border shadow-sm shadow-white ${toneClass}`}>
          <Icon size={23} />
        </div>

        <div className="min-w-0">
          <p className="text-sm font-semibold leading-5 text-slate-600">
            {title}
          </p>
          <p className="mt-0.5 text-2xl font-bold leading-8 text-slate-950">
            {value}
          </p>
          <p className="mt-0.5 truncate text-xs font-semibold text-slate-500">
            {caption}
          </p>
        </div>
      </div>
    </DashboardCard>
  );
}

function QuickAction({
  label,
  icon: Icon,
  tone,
  onClick,
}: {
  label: string;
  icon: typeof MessageSquare;
  tone: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex min-h-12 w-full items-center justify-between rounded-xl px-4 py-2.5 text-left text-sm font-semibold transition hover:shadow-sm ${tone}`}
    >
      <span className="flex items-center gap-3">
        <Icon size={18} />
        {label}
      </span>
      <ArrowRight size={17} />
    </button>
  );
}

function DashboardPage({
  user,
  isAdmin,
  isManager,
  conversations,
  onSelectPage,
  onSelectConversation,
}: DashboardPageProps) {
  const [documents, setDocuments] =
    useState<RagDocument[]>([]);
  const [systemStatus, setSystemStatus] =
    useState<SystemStatus | null>(null);
  const [activity, setActivity] =
    useState<ActivitySummary | null>(null);
  const [leaveRequests, setLeaveRequests] =
    useState<Array<LeaveRequestRecord | ManagerLeaveRequest>>([]);
  const [isLoading, setIsLoading] =
    useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadDashboard =
      async (): Promise<void> => {
        try {
          setIsLoading(true);

          const token =
            await user.getIdToken();

          const requestsPromise = isManager
            ? getManagerLeaveRequests(token)
            : getMyLeaveRequests(token);

          const [
            requestData,
            documentData,
            statusData,
            activityData,
          ] = await Promise.all([
            requestsPromise,
            isAdmin
              ? getDocuments(token)
              : Promise.resolve([]),
            isAdmin
              ? getSystemStatus(token)
              : Promise.resolve(null),
            isAdmin
              ? getAdminActivity(token, 7)
              : Promise.resolve(null),
          ]);

          if (!isMounted) {
            return;
          }

          setLeaveRequests(requestData);
          setDocuments(documentData);
          setSystemStatus(statusData);
          setActivity(activityData);
        } catch (error) {
          console.error(
            "Dashboard loading error:",
            error
          );
        } finally {
          if (isMounted) {
            setIsLoading(false);
          }
        }
      };

    void loadDashboard();

    return () => {
      isMounted = false;
    };
  }, [
    isAdmin,
    isManager,
    user,
  ]);

  const pendingLeaves = useMemo(
    () =>
      leaveRequests.filter(
        (request) => request.statut === "pending"
      ).length,
    [leaveRequests]
  );

  const recentDocuments =
    documents.slice(0, 4);

  const recentConversations =
    conversations.slice(0, 4);

  const hasActivity = Boolean(
    activity?.daily.some(
      (day) =>
        day.chat_messages > 0 ||
        day.documents > 0 ||
        day.leave_requests > 0 ||
        day.manager_actions > 0
    )
  );

  const displayName =
    user.displayName ||
    user.email?.split("@")[0] ||
    "Utilisateur";

  const quickActions = [
    {
      label: "Poser une question a l'IA",
      icon: MessageSquare,
      tone: "bg-violet-50 text-violet-700 hover:bg-violet-100",
      page: "chat" as const,
      show: true,
    },
    {
      label: "Uploader un document",
      icon: Upload,
      tone: "bg-blue-50 text-blue-700 hover:bg-blue-100",
      page: "documents" as const,
      show: isAdmin,
    },
    {
      label: "Demander un conge",
      icon: CalendarDays,
      tone: "bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
      page: "leave" as const,
      show: true,
    },
    {
      label: "Voir les demandes",
      icon: BarChart3,
      tone: "bg-amber-50 text-amber-700 hover:bg-amber-100",
      page: isManager ? "manager" as const : "requests" as const,
      show: true,
    },
  ].filter((action) => action.show);

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="mx-auto max-w-[1536px] px-6 py-5">
        <div className="mb-5">
          <h1 className="text-[28px] font-bold tracking-tight text-slate-950">
            Bienvenue, {displayName}
          </h1>
          <p className="mt-0.5 text-base font-medium text-slate-500">
            Voici un apercu de l'activite de votre systeme.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Documents"
            value={isAdmin ? (isLoading ? "..." : documents.length) : "Non disponible"}
            caption={isAdmin ? "Base documentaire RAG" : "Reserve aux administrateurs"}
            icon={FileText}
            tone="violet"
          />
          <KpiCard
            title="Demandes Conges"
            value={isLoading ? "..." : leaveRequests.length}
            caption={`${pendingLeaves} en attente`}
            icon={CalendarDays}
            tone="emerald"
          />
          <KpiCard
            title="Conversations"
            value={conversations.length}
            caption="Historique local de session"
            icon={MessageSquare}
            tone="blue"
          />
          <KpiCard
            title="Systeme"
            value={
              isAdmin
                ? systemIsOnline(systemStatus)
                  ? (
                      <span className="text-emerald-600">
                        En ligne
                      </span>
                    )
                  : systemStatus
                    ? "A verifier"
                    : "Non disponible"
                : "Non disponible"
            }
            caption={isAdmin ? "Ollama, RAG et n8n" : "Reserve aux administrateurs"}
            icon={Server}
            tone="amber"
          />
        </div>

        <div className="mt-3.5 grid grid-cols-1 gap-3.5 xl:grid-cols-12">
          <DashboardCard className="xl:col-span-8">
            <CardHeader
              title="Activite (7 derniers jours)"
              action={
                <span className="rounded-xl border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-600">
                  7 jours
                </span>
              }
            />
            {!isAdmin ? (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 py-7 text-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                  <BarChart3 size={22} />
                </div>
                <p className="mt-3 font-semibold text-slate-800">
                  Reserve aux administrateurs
                </p>
                <p className="mt-1.5 max-w-md text-sm leading-6 text-slate-500">
                  La telemetrie applicative est accessible depuis un compte admin.
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex min-h-44 items-center justify-center px-6 py-7 text-sm font-semibold text-slate-500">
                Chargement de l'activite...
              </div>
            ) : activity && hasActivity ? (
              <ActivityChart daily={activity.daily} />
            ) : (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 py-7 text-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                  <BarChart3 size={22} />
                </div>
                <p className="mt-3 font-semibold text-slate-800">
                  Aucune activite enregistree
                </p>
                <p className="mt-1.5 max-w-md text-sm leading-6 text-slate-500">
                  Les evenements apparaitront ici apres une action reussie dans l'application.
                </p>
              </div>
            )}
          </DashboardCard>

          <DashboardCard className="xl:col-span-4">
            <CardHeader title="Activite recente" />
            {!isAdmin ? (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 py-7 text-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                  <Clock size={21} />
                </div>
                <p className="mt-3 font-semibold text-slate-800">
                  Reserve aux administrateurs
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex min-h-44 items-center justify-center px-6 py-7 text-sm font-semibold text-slate-500">
                Chargement des evenements...
              </div>
            ) : activity && activity.recent.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {activity.recent.map((item) => {
                  const label = activityLabel(item);

                  return (
                    <div
                      key={`${item.action}-${item.created_at}`}
                      className="flex items-start gap-3 px-5 py-3.5"
                    >
                      <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${label.tone}`}>
                        <Clock size={16} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-slate-900">
                            {label.title}
                          </p>
                          <span className="shrink-0 text-xs font-medium text-slate-400">
                            {formatRelativeTime(item.created_at)}
                          </span>
                        </div>
                        <p className="mt-0.5 truncate text-xs text-slate-500">
                          {label.subtitle}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 py-7 text-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                  <Clock size={21} />
                </div>
                <p className="mt-3 font-semibold text-slate-800">
                  Aucun evenement recent
                </p>
                <p className="mt-1.5 text-sm leading-6 text-slate-500">
                  Les uploads, suppressions et validations apparaitront ici.
                </p>
              </div>
            )}
          </DashboardCard>
        </div>

        <div className="mt-3.5 grid grid-cols-1 gap-3.5 xl:grid-cols-12">
          <DashboardCard className="xl:col-span-5">
            <CardHeader
              title="Documents recents"
              action={
                isAdmin ? (
                  <button
                    type="button"
                    onClick={() => onSelectPage("documents")}
                    className="text-sm font-semibold text-blue-600 hover:text-blue-700"
                  >
                    Voir tous
                  </button>
                ) : null
              }
            />
            <div className="divide-y divide-slate-100">
              {!isAdmin ? (
                <div className="px-5 py-6 text-sm text-slate-500">
                  Les documents sont reserves aux administrateurs.
                </div>
              ) : recentDocuments.length === 0 ? (
                <div className="px-5 py-6 text-sm text-slate-500">
                  Aucun document disponible.
                </div>
              ) : (
                recentDocuments.map((document) => (
                  <div
                    key={document.name}
                    className="flex items-center gap-3.5 px-5 py-3.5 transition hover:bg-slate-50"
                  >
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[9px] font-bold uppercase ${fileTone(document.type)}`}>
                      {document.type}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {document.name}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {document.type.toUpperCase()} - {formatFileSize(document.size)}
                      </p>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-600">
                      Actif
                    </span>
                  </div>
                ))
              )}
            </div>
          </DashboardCard>

          <DashboardCard className="xl:col-span-3">
            <CardHeader title="Actions rapides" />
            <div className="space-y-2.5 p-4">
              {quickActions.map((action) => (
                <QuickAction
                  key={action.label}
                  label={action.label}
                  icon={action.icon}
                  tone={action.tone}
                  onClick={() => onSelectPage(action.page)}
                />
              ))}
            </div>
          </DashboardCard>

          <DashboardCard className="xl:col-span-4">
            <CardHeader title="Conversations recentes" />
            <div className="divide-y divide-slate-100">
              {recentConversations.length === 0 ? (
                <div className="px-5 py-6 text-sm text-slate-500">
                  Aucune conversation recente.
                </div>
              ) : (
                recentConversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    type="button"
                    onClick={() => onSelectConversation(conversation.id)}
                    className="flex w-full items-center gap-3 px-5 py-3.5 text-left transition hover:bg-slate-50"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-100 text-violet-700">
                      <Bot size={17} />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {conversation.title}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {conversation.messages.length} message(s)
                      </p>
                    </div>
                  </button>
                ))
              )}
            </div>
          </DashboardCard>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
