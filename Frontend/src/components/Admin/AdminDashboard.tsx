import {
  useEffect,
  useState,
} from "react";

import type { User } from "firebase/auth";

import {
  Bot,
  Database,
  FileText,
  LockKeyhole,
  Server,
  Settings,
  ShieldCheck,
  Workflow,
} from "lucide-react";

import {
  getSystemStatus,
  type SystemStatus,
} from "../../services/api";

import {
  PageHeader,
  SectionCard,
  StatCard,
  StatusBadge,
} from "../ui";

type AdminDashboardProps = {
  user: User;
};

function serviceLabel(
  key: keyof Pick<SystemStatus, "ollama" | "rag" | "n8n">,
  value: SystemStatus[keyof Pick<SystemStatus, "ollama" | "rag" | "n8n">],
) {
  if (key === "ollama") {
    return value === "online" ? "En ligne" : "Hors ligne";
  }

  if (key === "rag") {
    return value === "ready" ? "Pret" : "Indisponible";
  }

  return value === "configured" ? "Configure" : "Non configure";
}

function statusTone(value: string) {
  return value === "online" ||
    value === "ready" ||
    value === "configured"
    ? "emerald"
    : "red";
}

function AdminDashboard({
  user,
}: AdminDashboardProps) {
  const [systemStatus, setSystemStatus] =
    useState<SystemStatus | null>(null);

  const [isLoading, setIsLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadStatus =
      async (): Promise<void> => {
        try {
          setIsLoading(true);
          setError(null);

          const token =
            await user.getIdToken();

          const data =
            await getSystemStatus(token);

          if (isMounted) {
            setSystemStatus(data);
          }
        } catch (loadError) {
          console.error(
            "Admin status loading error:",
            loadError
          );

          if (isMounted) {
            setError(
              "Impossible de charger le statut du systeme."
            );
          }
        } finally {
          if (isMounted) {
            setIsLoading(false);
          }
        }
      };

    void loadStatus();

    return () => {
      isMounted = false;
    };
  }, [user]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl px-5 py-8 md:px-8">
        <PageHeader
          title={`Bienvenue, ${user.displayName || user.email || "Administrateur"}`}
          description="Vue de supervision des services et de la base documentaire."
          icon={ShieldCheck}
          eyebrow="Administration"
        />

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label="Documents"
            value={
              isLoading
                ? "..."
                : systemStatus?.documents ?? "Non disponible"
            }
            caption="Fichiers indexes dans la base RAG"
            icon={FileText}
            tone="violet"
          />

          <StatCard
            label="Services systeme"
            value={
              isLoading
                ? "..."
                : systemStatus
                  ? "3 suivis"
                  : "Non disponible"
            }
            caption="Ollama, RAG et n8n"
            icon={Server}
            tone="emerald"
          />

          <StatCard
            label="Controle d'acces"
            value="RBAC"
            caption="Firebase Custom Claims"
            icon={LockKeyhole}
            tone="amber"
          />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <SectionCard
            title="Statut du systeme"
            description="Etat technique expose par le backend."
            icon={Server}
          >
            {isLoading ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {[0, 1, 2, 3].map((item) => (
                  <div
                    key={item}
                    className="h-24 animate-pulse rounded-xl bg-slate-100"
                  />
                ))}
              </div>
            ) : systemStatus ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  {
                    label: "Ollama",
                    value: systemStatus.ollama,
                    icon: Bot,
                  },
                  {
                    label: "RAG",
                    value: systemStatus.rag,
                    icon: Database,
                  },
                  {
                    label: "n8n",
                    value: systemStatus.n8n,
                    icon: Workflow,
                  },
                ].map((service) => {
                  const Icon = service.icon;
                  return (
                    <div
                      key={service.label}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-violet-600">
                            <Icon size={18} />
                          </div>
                          <p className="font-semibold text-slate-800">
                            {service.label}
                          </p>
                        </div>
                        <StatusBadge tone={statusTone(service.value)}>
                          {serviceLabel(
                            service.label.toLowerCase() as keyof Pick<SystemStatus, "ollama" | "rag" | "n8n">,
                            service.value
                          )}
                        </StatusBadge>
                      </div>
                    </div>
                  );
                })}

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-violet-600">
                        <FileText size={18} />
                      </div>
                      <p className="font-semibold text-slate-800">
                        Documents
                      </p>
                    </div>
                    <StatusBadge tone="blue">
                      {systemStatus.documents}
                    </StatusBadge>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                Statut systeme non disponible.
              </p>
            )}
          </SectionCard>

          <SectionCard
            title="Compte administrateur"
            description="Identite connectee via Firebase."
            icon={ShieldCheck}
          >
            <div className="space-y-4">
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Email
                </p>
                <p className="mt-1 truncate text-sm font-semibold text-slate-800">
                  {user.email || "Non disponible"}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Role
                </p>
                <div className="mt-2">
                  <StatusBadge tone="violet">
                    Admin
                  </StatusBadge>
                </div>
              </div>

              {systemStatus ? (
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Collection RAG
                  </p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-800">
                    {systemStatus.rag_collection}
                  </p>
                </div>
              ) : null}
            </div>
          </SectionCard>
        </div>

        <SectionCard
          title="Parametres techniques"
          description="Informations exposees par le backend."
          icon={Settings}
          className="mt-6"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Modele d'embeddings
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-800">
                {systemStatus?.embedding_model || "Non disponible"}
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Utilisateurs
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-800">
                Non disponible
              </p>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

export default AdminDashboard;
