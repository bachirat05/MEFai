import {
  useEffect,
  useState,
} from "react";

import type { User } from "firebase/auth";

import {
  EmailAuthProvider,
  reauthenticateWithCredential,
  updatePassword,
} from "firebase/auth";

import {
  KeyRound,
  Settings,
  User as UserIcon,
} from "lucide-react";

import {
  getSystemStatus,
  type SystemStatus,
} from "../../services/api";

import {
  PageHeader,
  SectionCard,
  StatusBadge,
} from "../ui";

type SettingsPageProps = {
  user: User;
  isAdmin: boolean;
};

function getErrorCode(error: unknown): string | undefined {
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof (error as { code?: unknown }).code === "string"
  ) {
    return (error as { code: string }).code;
  }

  return undefined;
}

function SettingsPage({
  user,
  isAdmin,
}: SettingsPageProps) {
  const [showPasswordForm, setShowPasswordForm] =
    useState(false);
  const [currentPassword, setCurrentPassword] =
    useState("");
  const [newPassword, setNewPassword] =
    useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [isUpdatingPassword, setIsUpdatingPassword] =
    useState(false);
  const [passwordError, setPasswordError] =
    useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] =
    useState<string | null>(null);
  const [systemStatus, setSystemStatus] =
    useState<SystemStatus | null>(null);
  const [systemLoading, setSystemLoading] =
    useState(false);
  const [systemError, setSystemError] =
    useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin) {
      return;
    }

    let isMounted = true;

    const loadSystemStatus =
      async (): Promise<void> => {
        try {
          setSystemLoading(true);
          setSystemError(null);

          const token =
            await user.getIdToken();

          const data =
            await getSystemStatus(token);

          if (isMounted) {
            setSystemStatus(data);
          }
        } catch (error) {
          console.error(
            "System status error:",
            error
          );

          if (isMounted) {
            setSystemError(
              "Impossible de charger l'etat du systeme."
            );
          }
        } finally {
          if (isMounted) {
            setSystemLoading(false);
          }
        }
      };

    void loadSystemStatus();

    return () => {
      isMounted = false;
    };
  }, [isAdmin, user]);

  const handlePasswordChange =
    async (): Promise<void> => {
      setPasswordError(null);
      setPasswordSuccess(null);

      if (!user.email) {
        setPasswordError(
          "Aucune adresse email n'est associee a ce compte."
        );
        return;
      }

      if (!currentPassword) {
        setPasswordError(
          "Veuillez saisir votre mot de passe actuel."
        );
        return;
      }

      if (newPassword.length < 6) {
        setPasswordError(
          "Le nouveau mot de passe doit contenir au moins 6 caracteres."
        );
        return;
      }

      if (newPassword !== confirmPassword) {
        setPasswordError(
          "Les deux nouveaux mots de passe ne correspondent pas."
        );
        return;
      }

      if (currentPassword === newPassword) {
        setPasswordError(
          "Le nouveau mot de passe doit etre different de l'ancien."
        );
        return;
      }

      try {
        setIsUpdatingPassword(true);

        const credential =
          EmailAuthProvider.credential(
            user.email,
            currentPassword
          );

        await reauthenticateWithCredential(
          user,
          credential
        );

        await updatePassword(
          user,
          newPassword
        );

        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setPasswordSuccess(
          "Votre mot de passe a ete modifie avec succes."
        );
        setShowPasswordForm(false);
      } catch (error: unknown) {
        console.error(
          "Password update error:",
          error
        );

        const code = getErrorCode(error);

        if (
          code === "auth/invalid-credential" ||
          code === "auth/wrong-password"
        ) {
          setPasswordError(
            "Le mot de passe actuel est incorrect."
          );
          return;
        }

        if (code === "auth/weak-password") {
          setPasswordError(
            "Le nouveau mot de passe est trop faible."
          );
          return;
        }

        if (code === "auth/requires-recent-login") {
          setPasswordError(
            "Veuillez vous reconnecter avant de modifier votre mot de passe."
          );
          return;
        }

        if (code === "auth/too-many-requests") {
          setPasswordError(
            "Trop de tentatives. Veuillez reessayer plus tard."
          );
          return;
        }

        setPasswordError(
          "Impossible de modifier le mot de passe."
        );
      } finally {
        setIsUpdatingPassword(false);
      }
    };

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="mx-auto max-w-5xl">
        <PageHeader
          title="Parametres"
          description="Gerez votre compte, la securite et les informations systeme."
          icon={Settings}
        />

        <div className="space-y-6">
          <SectionCard
            title="Mon compte"
            description="Informations associees a votre compte Firebase."
            icon={UserIcon}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Nom
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-800">
                  {user.displayName || "Non renseigne"}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Email
                </p>
                <p className="mt-1 truncate text-sm font-semibold text-slate-800">
                  {user.email || "Non renseigne"}
                </p>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="Securite"
            description="Modification du mot de passe avec reauthentification Firebase."
            icon={KeyRound}
          >
            {passwordSuccess ? (
              <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {passwordSuccess}
              </div>
            ) : null}

            {passwordError ? (
              <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {passwordError}
              </div>
            ) : null}

            {!showPasswordForm ? (
              <button
                type="button"
                onClick={() => {
                  setPasswordError(null);
                  setPasswordSuccess(null);
                  setShowPasswordForm(true);
                }}
                className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
              >
                Modifier le mot de passe
              </button>
            ) : (
              <div className="max-w-xl space-y-4">
                {[
                  {
                    label: "Mot de passe actuel",
                    value: currentPassword,
                    setter: setCurrentPassword,
                    autoComplete: "current-password",
                  },
                  {
                    label: "Nouveau mot de passe",
                    value: newPassword,
                    setter: setNewPassword,
                    autoComplete: "new-password",
                  },
                  {
                    label: "Confirmer le nouveau mot de passe",
                    value: confirmPassword,
                    setter: setConfirmPassword,
                    autoComplete: "new-password",
                  },
                ].map((field) => (
                  <div key={field.label}>
                    <label className="mb-1.5 block text-sm font-medium text-slate-700">
                      {field.label}
                    </label>
                    <input
                      type="password"
                      value={field.value}
                      onChange={(event) => field.setter(event.target.value)}
                      autoComplete={field.autoComplete}
                      className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
                    />
                  </div>
                ))}

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    disabled={isUpdatingPassword}
                    onClick={() => {
                      void handlePasswordChange();
                    }}
                    className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isUpdatingPassword
                      ? "Modification..."
                      : "Enregistrer"}
                  </button>

                  <button
                    type="button"
                    disabled={isUpdatingPassword}
                    onClick={() => {
                      setShowPasswordForm(false);
                      setCurrentPassword("");
                      setNewPassword("");
                      setConfirmPassword("");
                      setPasswordError(null);
                    }}
                    className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </SectionCard>

          {isAdmin ? (
            <SectionCard
              title="Parametres systeme"
              description="Etat technique des services de l'assistant."
              icon={Settings}
            >
              {systemLoading ? (
                <div className="grid gap-4 md:grid-cols-2">
                  {[0, 1, 2, 3].map((item) => (
                    <div
                      key={item}
                      className="h-24 animate-pulse rounded-xl bg-slate-100"
                    />
                  ))}
                </div>
              ) : null}

              {systemError ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {systemError}
                </div>
              ) : null}

              {systemStatus ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Ollama
                    </p>
                    <div className="mt-2">
                      <StatusBadge tone={systemStatus.ollama === "online" ? "emerald" : "red"}>
                        {systemStatus.ollama === "online" ? "En ligne" : "Hors ligne"}
                      </StatusBadge>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      RAG
                    </p>
                    <div className="mt-2">
                      <StatusBadge tone={systemStatus.rag === "ready" ? "emerald" : "red"}>
                        {systemStatus.rag === "ready" ? "Pret" : "Indisponible"}
                      </StatusBadge>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      n8n
                    </p>
                    <div className="mt-2">
                      <StatusBadge tone={systemStatus.n8n === "configured" ? "emerald" : "amber"}>
                        {systemStatus.n8n === "configured" ? "Configure" : "Non configure"}
                      </StatusBadge>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Documents
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-800">
                      {systemStatus.documents}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Modele d'embeddings
                    </p>
                    <p className="mt-2 truncate text-sm font-semibold text-slate-800">
                      {systemStatus.embedding_model}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Collection RAG
                    </p>
                    <p className="mt-2 truncate text-sm font-semibold text-slate-800">
                      {systemStatus.rag_collection}
                    </p>
                  </div>
                </div>
              ) : null}
            </SectionCard>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
