import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type { User } from "firebase/auth";

import {
  ChevronDown,
  Menu,
  Search,
} from "lucide-react";

import {
  getDocuments,
  type RagDocument,
} from "../services/api";

import type {
  AppPage,
  Conversation,
  UserRole,
} from "../types";

type HeaderProps = {
  user: User;
  role: UserRole;
  isAdmin: boolean;
  activePage: AppPage;
  conversations: Conversation[];
  onToggleSidebar: () => void;
  onSelectPage: (page: AppPage) => void;
  onSelectConversation: (id: number) => void;
};

const pageCopy: Record<
  AppPage,
  {
    title: string;
    description: string;
  }
> = {
  dashboard: {
    title: "Tableau de bord",
    description: "Vue d'ensemble de Cortex AI",
  },
  chat: {
    title: "Chat IA",
    description: "Assistant RH connecte aux documents internes",
  },
  leave: {
    title: "Demande de conge",
    description: "Soumission et suivi des demandes",
  },
  requests: {
    title: "Mes demandes",
    description: "Historique personnel des conges",
  },
  manager: {
    title: "Conges (Gestion)",
    description: "Validation des demandes de conge",
  },
  admin: {
    title: "Administration",
    description: "Supervision de Cortex AI",
  },
  documents: {
    title: "Documents",
    description: "Base documentaire RAG",
  },
  audit: {
    title: "Audit Logs",
    description: "Journal des evenements systeme",
  },
  settings: {
    title: "Parametres",
    description: "Compte, securite et systeme",
  },
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

function Header({
  user,
  role,
  isAdmin,
  activePage,
  conversations,
  onToggleSidebar,
  onSelectPage,
  onSelectConversation,
}: HeaderProps) {
  const [query, setQuery] =
    useState("");

  const [documents, setDocuments] =
    useState<RagDocument[]>([]);

  const [isSearchFocused, setIsSearchFocused] =
    useState(false);

  useEffect(() => {
    if (!isAdmin) {
      setDocuments([]);
      return;
    }

    let isMounted = true;

    const loadDocuments =
      async (): Promise<void> => {
        try {
          const token =
            await user.getIdToken();

          const result =
            await getDocuments(token);

          if (isMounted) {
            setDocuments(result);
          }
        } catch {
          if (isMounted) {
            setDocuments([]);
          }
        }
      };

    void loadDocuments();

    return () => {
      isMounted = false;
    };
  }, [isAdmin, user]);

  const page = pageCopy[activePage];

  const searchResults = useMemo(() => {
    const normalizedQuery =
      query.trim().toLowerCase();

    if (!normalizedQuery) {
      return {
        conversations: [],
        documents: [],
      };
    }

    return {
      conversations: conversations
        .filter((conversation) =>
          conversation.title
            .toLowerCase()
            .includes(normalizedQuery)
        )
        .slice(0, 4),
      documents: documents
        .filter((document) =>
          document.name
            .toLowerCase()
            .includes(normalizedQuery)
        )
        .slice(0, 4),
    };
  }, [
    conversations,
    documents,
    query,
  ]);

  const hasResults =
    searchResults.conversations.length > 0 ||
    searchResults.documents.length > 0;

  return (
    <header className="flex h-[74px] shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div className="flex min-w-0 flex-1 items-center gap-4">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
          title="Menu"
        >
          <Menu size={22} />
        </button>

        <div className="relative hidden w-full max-w-[430px] lg:block">
          <div className="flex h-11 items-center gap-3 rounded-2xl bg-slate-100 px-4 text-slate-500 ring-1 ring-transparent transition focus-within:bg-white focus-within:ring-violet-200">
            <Search size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => {
                window.setTimeout(
                  () => setIsSearchFocused(false),
                  150
                );
              }}
              placeholder="Rechercher documents ou conversations..."
              className="min-w-0 flex-1 bg-transparent text-sm font-medium text-slate-700 outline-none placeholder:text-slate-400"
            />
          </div>

          {isSearchFocused && query.trim() ? (
            <div className="absolute left-0 right-0 top-14 z-40 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
              {hasResults ? (
                <div className="max-h-80 overflow-y-auto py-2">
                  {searchResults.conversations.map((conversation) => (
                    <button
                      key={`conversation-${conversation.id}`}
                      type="button"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => {
                        onSelectConversation(conversation.id);
                        setQuery("");
                      }}
                      className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50"
                    >
                      <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-50 text-violet-700">
                        C
                      </span>
                      <span className="truncate font-medium text-slate-700">
                        {conversation.title}
                      </span>
                    </button>
                  ))}

                  {searchResults.documents.map((document) => (
                    <button
                      key={`document-${document.name}`}
                      type="button"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => {
                        onSelectPage("documents");
                        setQuery("");
                      }}
                      className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50"
                    >
                      <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-xs font-bold uppercase text-blue-700">
                        {document.type}
                      </span>
                      <span className="truncate font-medium text-slate-700">
                        {document.name}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="px-4 py-4 text-sm text-slate-500">
                  Aucun resultat.
                </p>
              )}
            </div>
          ) : null}
        </div>

        <div className="min-w-0 lg:hidden">
          <h2 className="truncate text-lg font-semibold text-slate-950">
            {page.title}
          </h2>
          <p className="mt-0.5 truncate text-xs font-medium text-slate-500">
            {page.description}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-500 text-sm font-semibold text-white shadow-sm">
          {getInitials(user)}
        </div>

        <div className="hidden min-w-0 text-left sm:block">
          <p className="max-w-40 truncate text-sm font-bold leading-5 text-slate-950">
            {user.displayName || "Utilisateur"}
          </p>
          <p className="max-w-44 truncate text-xs leading-4 text-slate-500">
            {user.email || "Compte Firebase"}
          </p>
        </div>

        <span className="hidden rounded-full bg-violet-50 px-2.5 py-1 text-[11px] font-semibold capitalize text-violet-700 ring-1 ring-violet-100 sm:inline-flex">
          {role}
        </span>

        <ChevronDown
          size={18}
          className="hidden text-slate-500 sm:block"
        />
      </div>
    </header>
  );
}

export default Header;
