import type { User } from "firebase/auth";

import {
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
  CalendarDays,
  ClipboardList,
  FileClock,
  FileText,
  House,
  LogOut,
  MessageSquare,
  Plus,
  Settings,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import type {
  AppPage,
  Conversation,
} from "../types";

type SidebarProps = {
  user: User;
  isAdmin: boolean;
  isManager: boolean;
  activePage: AppPage;
  conversations: Conversation[];
  activeConversationId: number | null;
  isCollapsed: boolean;
  onNewConversation: () => void;
  onDeleteConversation: (id: number) => void;
  onSelectPage: (page: AppPage) => void;
  onSelectConversation: (id: number) => void;
  onLogout: () => void;
};

type NavigationItem = {
  label: string;
  page: AppPage;
  icon: typeof MessageSquare;
};

function getInitials(user: User): string {
  const source =
    user.displayName ||
    user.email ||
    "Utilisateur";

  return source
    .split(/[ .@_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";
}

function Sidebar({
  user,
  isAdmin,
  isManager,
  activePage,
  conversations,
  activeConversationId,
  isCollapsed,
  onNewConversation,
  onDeleteConversation,
  onSelectPage,
  onSelectConversation,
  onLogout,
}: SidebarProps) {
  const generalItems: NavigationItem[] = [
    {
      label: "Chat IA",
      page: "chat",
      icon: MessageSquare,
    },
     ...(!isAdmin && !isManager
    ? [
        {
          label: "Demande de congé",
          page: "leave" as const,
          icon: CalendarDays,
        },
        {
          label: "Mes demandes",
          page: "requests" as const,
          icon: ClipboardList,
        },
      ]
    : []),
];
      

  const managementItems: NavigationItem[] = [
    ...(isManager
      ? [
          {
            label: "Espace Manager",
            page: "manager" as const,
            icon: BriefcaseBusiness,
          },
        ]
      : []),
    ...(isAdmin
      ? [
          {
            label: "Administration",
            page: "admin" as const,
            icon: ShieldCheck,
          },
          {
            label: "Documents",
            page: "documents" as const,
            icon: FileText,
          },
          {
            label: "Audit Logs",
            page: "audit" as const,
            icon: FileClock,
          },
        ]
      : []),
  ];

  const systemItems: NavigationItem[] = [
    {
      label: "Parametres",
      page: "settings",
      icon: Settings,
    },
  ];

  const renderItem = (item: NavigationItem) => {
    const Icon = item.icon;
    const isActive = activePage === item.page;

    return (
      <button
        key={item.page}
        type="button"
        onClick={() => onSelectPage(item.page)}
        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition ${
          isActive
            ? "bg-violet-50 text-violet-700 shadow-sm shadow-violet-100/70"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
        }`}
      >
        <Icon size={18} />
        {!isCollapsed ? (
          <span className="truncate">
            {item.label}
          </span>
        ) : null}
      </button>
    );
  };

  const renderSection = (
    title: string,
    items: NavigationItem[],
  ) => {
    if (items.length === 0) {
      return null;
    }

    return (
      <div className="space-y-1">
        {!isCollapsed ? (
          <p className="px-3 pb-1.5 pt-4 text-[11px] font-bold uppercase tracking-wide text-slate-400">
            {title}
          </p>
        ) : (
          <div className="pt-5" />
        )}
        {items.map(renderItem)}
      </div>
    );
  };

  return (
    <aside className={`hidden shrink-0 flex-col border-r border-slate-200 bg-white/95 transition-all duration-200 md:flex ${isCollapsed ? "w-24" : "w-72"}`}>
      <div className={`flex h-[74px] items-center ${isCollapsed ? "justify-center px-3" : "px-5"}`}>
        <div className="flex items-center gap-3">
          <img
            src="/MEFai.png"
            alt="Logo MEFai"
            className="h-11 w-11 shrink-0 object-contain"
          />

          {!isCollapsed ? (
          <div>
            <h1 className="text-lg font-semibold leading-tight text-slate-950">

              MEFai

            </h1>
            <p className="text-xs font-medium text-slate-500">
              Ministere
            </p>
          </div>
          ) : null}
        </div>
      </div>

      <div className="px-4">
        <button
          type="button"
          onClick={onNewConversation}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700"
        >
          <Plus size={18} />
          {!isCollapsed ? "Nouvelle conversation" : null}
        </button>
      </div>

      <nav className="sidebar-scroll flex-1 overflow-y-auto px-4 pb-3">
        {isAdmin ? (
          <div className="pt-4">
            {renderItem({
              label: "Tableau de bord",
              page: "dashboard",
              icon: House,
            })}
          </div>
        ) : null}

        {renderSection("General", generalItems)}
        {renderSection("Gestion", managementItems)}
        {renderSection("Systeme", systemItems)}

        {!isCollapsed ? (
        <div className="mt-5 border-t border-slate-100 pt-4">
          <p className="px-3 pb-2 text-[11px] font-bold uppercase tracking-wide text-slate-400">
            Historique
          </p>

          <div className="space-y-1">
            {conversations.length === 0 ? (
              <p className="px-3 py-2 text-xs text-slate-400">
                Aucune conversation.
              </p>
            ) : (
              conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`group flex items-center gap-1 rounded-xl pr-1 transition ${
                    conversation.id === activeConversationId
                      ? "bg-slate-100 text-slate-900"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelectConversation(conversation.id)}
                    className="flex min-w-0 flex-1 items-center gap-3 rounded-xl px-3 py-2 text-left text-sm"
                  >
                    <Bot
                      size={16}
                      className="shrink-0"
                    />
                    <span className="truncate">
                      {conversation.title}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();

                      if (
                        window.confirm(
                          `Supprimer "${conversation.title}" ?`
                        )
                      ) {
                        onDeleteConversation(
                          conversation.id
                        );
                      }
                    }}
                    className="rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 focus:opacity-100"
                    title="Supprimer la conversation"
                    aria-label={`Supprimer ${conversation.title}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
        ) : null}
      </nav>

      <div className="border-t border-slate-200 p-4">
        {!isCollapsed ? (
        <div className="mb-3 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
          <div>
            <p className="text-xs font-semibold text-slate-700">

              MEFai v1.2.0

            </p>
            <p className="mt-0.5 text-xs text-slate-400">
              Statut operationnel
            </p>
          </div>
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </div>
        ) : null}

        <div className={`flex items-center gap-3 ${isCollapsed ? "justify-center" : ""}`}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-semibold text-violet-700">
            {getInitials(user)}
          </div>

          {!isCollapsed ? (
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-900">
              {user.displayName || "Utilisateur"}
            </p>
            <p className="truncate text-xs text-slate-500">
              {user.email || "Compte Firebase"}
            </p>
          </div>
          ) : null}

          {!isCollapsed ? (
          <button
            type="button"
            onClick={onLogout}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
            title="Se deconnecter"
          >
            <LogOut size={17} />
          </button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
