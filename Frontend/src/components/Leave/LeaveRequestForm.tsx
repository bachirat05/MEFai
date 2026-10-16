import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import type { User } from "firebase/auth";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileText,
  HelpCircle,
  Hourglass,
  MessageSquare,
  RotateCcw,
  Send,
  XCircle,
} from "lucide-react";

import type {
  AppPage,
  LeaveApiResponse,
  LeaveRequest,
  LeaveRequestRecord,
} from "../../types";

import {
  getMyLeaveRequests,
  submitLeaveRequest,
} from "../../services/api";

type LeaveRequestFormProps = {
  user: User;
  onSelectPage: (page: AppPage) => void;
};

type FieldErrors = Partial<
  Record<keyof LeaveRequest, string>
>;

const initialForm: LeaveRequest = {
  employe_id: "",
  date_debut: "",
  date_fin: "",
  type_conge: "conge_annuel",
  motif: "",
};

const leaveTypeLabels: Record<
  LeaveRequest["type_conge"],
  string
> = {
  conge_annuel: "Conge annuel",
  conge_maladie: "Conge maladie",
  conge_maternite: "Conge maternite",
  conge_paternite: "Conge paternite",
  conge_sans_solde: "Conge sans solde",
  conge_formation: "Conge formation",
  autre: "Autre",
};

function countByStatus(
  requests: LeaveRequestRecord[],
  status: LeaveRequestRecord["statut"],
): number {
  return requests.filter(
    (request) => request.statut === status
  ).length;
}

function estimateDuration(
  start: string,
  end: string,
): number | null {
  if (!start || !end || end < start) {
    return null;
  }

  const startDate = new Date(`${start}T00:00:00`);
  const endDate = new Date(`${end}T00:00:00`);
  const diff =
    endDate.getTime() -
    startDate.getTime();

  return Math.floor(diff / 86400000) + 1;
}

function formatDate(value: string): string {
  if (!value) {
    return "Non renseigne";
  }

  return new Intl.DateTimeFormat(
    "fr-FR",
    {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }
  ).format(new Date(`${value}T00:00:00`));
}

function SummaryCard({
  label,
  value,
  caption,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string | number;
  caption: string;
  icon: typeof ClipboardList;
  tone: "violet" | "emerald" | "amber" | "red";
}) {
  const tones = {
    violet: "border-violet-100 bg-violet-50/40 text-violet-700",
    emerald: "border-emerald-100 bg-emerald-50/40 text-emerald-700",
    amber: "border-amber-100 bg-amber-50/45 text-amber-700",
    red: "border-red-100 bg-red-50/40 text-red-700",
  };

  return (
    <div className={`rounded-2xl border bg-white p-4 shadow-sm ${tones[tone]}`}>
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/75 shadow-sm">
          <Icon size={21} />
        </div>

        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-600">
            {label}
          </p>
          <p className="mt-0.5 text-2xl font-bold leading-8 text-slate-950">
            {value}
          </p>
          <p className="truncate text-xs font-medium text-slate-500">
            {caption}
          </p>
        </div>
      </div>
    </div>
  );
}

function FieldError({
  children,
}: {
  children?: string;
}) {
  if (!children) {
    return null;
  }

  return (
    <p className="mt-1.5 text-xs font-medium text-red-600">
      {children}
    </p>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0">
      <span className="text-sm font-medium text-slate-500">
        {label}
      </span>
      <span className="text-right text-sm font-semibold text-slate-900">
        {value}
      </span>
    </div>
  );
}

function LeaveRequestForm({
  user,
  onSelectPage,
}: LeaveRequestFormProps) {
  const [form, setForm] =
    useState<LeaveRequest>(initialForm);

  const [requests, setRequests] =
    useState<LeaveRequestRecord[]>([]);

  const [statsLoading, setStatsLoading] =
    useState(true);

  const [loading, setLoading] =
    useState<boolean>(false);

  const [error, setError] =
    useState<string>("");

  const [fieldErrors, setFieldErrors] =
    useState<FieldErrors>({});

  const [result, setResult] =
    useState<LeaveApiResponse | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadRequests = async () => {
      try {
        setStatsLoading(true);
        const token = await user.getIdToken();
        const data = await getMyLeaveRequests(token);

        if (mounted) {
          setRequests(data);
        }
      } catch (loadError) {
        console.error(
          "Unable to load leave request summary:",
          loadError
        );
      } finally {
        if (mounted) {
          setStatsLoading(false);
        }
      }
    };

    void loadRequests();

    return () => {
      mounted = false;
    };
  }, [
    user,
  ]);

  const duration = useMemo(
    () =>
      estimateDuration(
        form.date_debut,
        form.date_fin
      ),
    [
      form.date_debut,
      form.date_fin,
    ]
  );

  const stats = useMemo(
    () => ({
      total: requests.length,
      pending: countByStatus(
        requests,
        "pending"
      ),
      accepted: countByStatus(
        requests,
        "accepted"
      ),
      rejected: countByStatus(
        requests,
        "rejected"
      ),
    }),
    [
      requests,
    ]
  );

  const updateField = <
    K extends keyof LeaveRequest
  >(
    field: K,
    value: LeaveRequest[K]
  ) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
    setFieldErrors((previous) => ({
      ...previous,
      [field]: undefined,
    }));
  };

  const validateForm = (): FieldErrors => {
    const errors: FieldErrors = {};

    if (!form.employe_id.trim()) {
      errors.employe_id =
        "L'identifiant employe est obligatoire.";
    } else if (form.employe_id.trim().length > 50) {
      errors.employe_id =
        "L'identifiant employe ne doit pas depasser 50 caracteres.";
    }

    if (!form.type_conge) {
      errors.type_conge =
        "Le type de conge est obligatoire.";
    }

    if (!form.date_debut) {
      errors.date_debut =
        "La date de debut est obligatoire.";
    }

    if (!form.date_fin) {
      errors.date_fin =
        "La date de fin est obligatoire.";
    } else if (
      form.date_debut &&
      form.date_fin < form.date_debut
    ) {
      errors.date_fin =
        "La date de fin doit etre posterieure ou egale a la date de debut.";
    }

    const motif = form.motif.trim();

    if (!motif) {
      errors.motif =
        "Le motif est obligatoire.";
    } else if (motif.length < 3) {
      errors.motif =
        "Le motif doit contenir au moins 3 caracteres.";
    } else if (motif.length > 500) {
      errors.motif =
        "Le motif ne doit pas depasser 500 caracteres.";
    }

    return errors;
  };

  const resetForm = () => {
    setForm(initialForm);
    setError("");
    setFieldErrors({});
    setResult(null);
  };

  const refreshRequests = async () => {
    const token = await user.getIdToken();
    const data = await getMyLeaveRequests(token);
    setRequests(data);
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setError("");
    setResult(null);

    const errors = validateForm();
    setFieldErrors(errors);

    if (Object.keys(errors).length > 0) {
      setError(
        "Veuillez corriger les champs indiques."
      );
      return;
    }

    setLoading(true);

    try {
      const token = await user.getIdToken();

      const data = await submitLeaveRequest(
        token,
        {
          ...form,
          employe_id: form.employe_id.trim(),
          motif: form.motif.trim(),
        }
      );

      setResult(data);
      await refreshRequests();
    } catch (submitError: unknown) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Une erreur est survenue."
      );
    } finally {
      setLoading(false);
    }
  };

  const statValue = (value: number) =>
    statsLoading ? "..." : value;

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="mx-auto max-w-[1536px] px-6 py-6">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">
              Conges &gt; Nouvelle demande
            </p>
            <h1 className="mt-2 text-[28px] font-bold tracking-tight text-slate-950">
              Demande de conge
            </h1>
            <p className="mt-1 text-base font-medium text-slate-500">
              Remplissez le formulaire ci-dessous pour soumettre votre demande.
            </p>
          </div>
        </div>

        <div className="mb-5 grid grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            label="Demandes totales"
            value={statValue(stats.total)}
            caption="Depuis vos demandes enregistrees"
            icon={ClipboardList}
            tone="violet"
          />
          <SummaryCard
            label="En attente"
            value={statValue(stats.pending)}
            caption="Validation manager"
            icon={Hourglass}
            tone="amber"
          />
          <SummaryCard
            label="Acceptees"
            value={statValue(stats.accepted)}
            caption="Demandes validees"
            icon={CheckCircle2}
            tone="emerald"
          />
          <SummaryCard
            label="Refusees"
            value={statValue(stats.rejected)}
            caption="Demandes refusees"
            icon={XCircle}
            tone="red"
          />
        </div>

        {result ? (
          <div className="mb-5 rounded-2xl border border-emerald-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-950">
                    Demande transmise
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    {result.message}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                    <span className="rounded-full bg-violet-50 px-3 py-1 text-violet-700 ring-1 ring-violet-100">
                      Reference: {result.demande_id}
                    </span>
                    <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700 ring-1 ring-amber-100">
                      Statut: {result.statut}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => onSelectPage("requests")}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Mes demandes
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
                >
                  Nouvelle demande
                </button>
              </div>
            </div>
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <form
            onSubmit={handleSubmit}
            className="rounded-2xl border border-slate-200 bg-white shadow-sm xl:col-span-8"
          >
            <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-700">
                <FileText size={20} />
              </div>
              <div>
                <h2 className="font-semibold text-slate-950">
                  Informations de la demande
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Tous les champs correspondent au workflow de conge actuel.
                </p>
              </div>
            </div>

            <div className="space-y-5 p-6">
              {error ? (
                <div className="flex gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertCircle
                    size={18}
                    className="mt-0.5 shrink-0"
                  />
                  <span>{error}</span>
                </div>
              ) : null}

              <div>
                <label className="text-sm font-semibold text-slate-700">
                  Identifiant employe <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.employe_id}
                  onChange={(event) =>
                    updateField(
                      "employe_id",
                      event.target.value
                    )
                  }
                  placeholder="EMP-001"
                  maxLength={50}
                  className="mt-2 h-12 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
                />
                <FieldError>
                  {fieldErrors.employe_id}
                </FieldError>
              </div>

              <div>
                <label className="text-sm font-semibold text-slate-700">
                  Type de conge <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.type_conge}
                  onChange={(event) =>
                    updateField(
                      "type_conge",
                      event.target.value as LeaveRequest["type_conge"]
                    )
                  }
                  className="mt-2 h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
                >
                  {Object.entries(leaveTypeLabels).map(
                    ([value, label]) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {label}
                      </option>
                    )
                  )}
                </select>
                <FieldError>
                  {fieldErrors.type_conge}
                </FieldError>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm font-semibold text-slate-700">
                    Date de debut <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={form.date_debut}
                    onChange={(event) =>
                      updateField(
                        "date_debut",
                        event.target.value
                      )
                    }
                    className="mt-2 h-12 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
                  />
                  <FieldError>
                    {fieldErrors.date_debut}
                  </FieldError>
                </div>

                <div>
                  <label className="text-sm font-semibold text-slate-700">
                    Date de fin <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={form.date_fin}
                    onChange={(event) =>
                      updateField(
                        "date_fin",
                        event.target.value
                      )
                    }
                    className="mt-2 h-12 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
                  />
                  <FieldError>
                    {fieldErrors.date_fin}
                  </FieldError>
                </div>
              </div>

              <div className="rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-blue-800">
                  <Clock3 size={17} />
                  Duree estimee
                </div>
                <p className="mt-1 text-sm text-blue-700">
                  {duration === null
                    ? "Renseignez une date de debut et une date de fin."
                    : `${duration} jour(s) calendaire(s)`}
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3">
                  <label className="text-sm font-semibold text-slate-700">
                    Motif de la demande <span className="text-red-500">*</span>
                  </label>
                  <span className={`text-xs font-medium ${form.motif.length > 500 ? "text-red-600" : "text-slate-400"}`}>
                    {form.motif.length} / 500 caracteres
                  </span>
                </div>
                <textarea
                  value={form.motif}
                  onChange={(event) =>
                    updateField(
                      "motif",
                      event.target.value
                    )
                  }
                  rows={5}
                  placeholder="Expliquez brievement le motif de votre demande."
                  maxLength={500}
                  className="mt-2 w-full resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
                />
                <FieldError>
                  {fieldErrors.motif}
                </FieldError>
              </div>

              <div className="rounded-xl border border-violet-100 bg-violet-50/65 px-4 py-3">
                <div className="flex gap-3">
                  <AlertCircle
                    size={18}
                    className="mt-0.5 shrink-0 text-violet-700"
                  />
                  <p className="text-sm leading-6 text-violet-800">
                    La demande sera transmise au manager et conservee dans votre historique.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-col-reverse gap-3 border-t border-slate-100 px-6 py-5 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={resetForm}
                disabled={loading}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RotateCcw size={17} />
                Annuler
              </button>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send size={17} />
                {loading
                  ? "Transmission..."
                  : "Soumettre la demande"}
              </button>
            </div>
          </form>

          <aside className="space-y-4 xl:col-span-4">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="font-semibold text-slate-950">
                Recapitulatif de la demande
              </h2>
              <div className="mt-4">
                <DetailRow
                  label="Type de conge"
                  value={leaveTypeLabels[form.type_conge]}
                />
                <DetailRow
                  label="Du"
                  value={formatDate(form.date_debut)}
                />
                <DetailRow
                  label="Au"
                  value={formatDate(form.date_fin)}
                />
                <DetailRow
                  label="Duree estimee"
                  value={
                    duration === null
                      ? "Non renseigne"
                      : `${duration} jour(s)`
                  }
                />
                <DetailRow
                  label="Employe"
                  value={
                    form.employe_id.trim() ||
                    "Non renseigne"
                  }
                />
              </div>
            </section>

            <section className="rounded-2xl border border-emerald-100 bg-emerald-50/35 p-5 shadow-sm">
              <h2 className="font-semibold text-emerald-800">
                Processus de validation
              </h2>
              <div className="mt-5 space-y-5">
                {[
                  {
                    title: "Soumission",
                    description: "Votre demande est envoyee au workflow.",
                    active: true,
                  },
                  {
                    title: "Validation manager",
                    description: "Votre manager examine la demande.",
                    active: false,
                  },
                  {
                    title: "Notification employe",
                    description: "Vous recevez le statut de la demande.",
                    active: false,
                  },
                ].map((step, index, steps) => (
                  <div
                    key={step.title}
                    className="relative flex gap-3"
                  >
                    {index < steps.length - 1 ? (
                      <span className="absolute left-4 top-9 h-10 w-px bg-emerald-200" />
                    ) : null}
                    <div className={`z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${step.active ? "bg-emerald-600 text-white" : "bg-white text-slate-500 ring-1 ring-emerald-200"}`}>
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {step.title}
                      </p>
                      <p className="mt-0.5 text-xs leading-5 text-slate-500">
                        {step.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-amber-100 bg-amber-50/45 p-5 shadow-sm">
              <div className="flex gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-amber-700 shadow-sm">
                  <HelpCircle size={22} />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-950">
                    Besoin d'aide ?
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    Consultez les documents internes ou posez une question a l'assistant RH.
                  </p>
                  <button
                    type="button"
                    onClick={() => onSelectPage("chat")}
                    className="mt-4 inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-white px-4 py-2.5 text-sm font-semibold text-amber-700 transition hover:bg-amber-50"
                  >
                    <MessageSquare size={17} />
                    Poser une question a l'IA
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

export default LeaveRequestForm;
