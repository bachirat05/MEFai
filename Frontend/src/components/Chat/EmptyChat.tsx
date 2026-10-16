import {
  FileSearch,
  MessageSquare,
  Sparkles,
} from "lucide-react";

type EmptyChatProps = {
  onSelectPrompt: (prompt: string) => void;
};

function EmptyChat({
  onSelectPrompt,
}: EmptyChatProps) {
  return (
    <div className="flex min-h-full items-center justify-center px-6 py-10">
      <div className="w-full max-w-3xl text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 text-white shadow-sm shadow-violet-200">
          <Sparkles size={28} />
        </div>

        <h1 className="text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
          Bonjour
        </h1>

        <p className="mt-3 text-slate-500">
          Posez une question RH ou recherchez une information dans les documents internes.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() =>
              onSelectPrompt(
                "Quelles sont les regles concernant les conges annuels ?"
              )
            }
            className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-violet-200 hover:bg-violet-50"
          >
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
              <MessageSquare size={19} />
            </div>

            <p className="font-semibold text-slate-900">
              Consulter les conges
            </p>

            <p className="mt-1 text-sm text-slate-500">
              Comprendre les regles et procedures internes.
            </p>
          </button>

          <button
            type="button"
            onClick={() =>
              onSelectPrompt(
                "Rechercher les documents disponibles concernant les ressources humaines."
              )
            }
            className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-blue-200 hover:bg-blue-50"
          >
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
              <FileSearch size={19} />
            </div>

            <p className="font-semibold text-slate-900">
              Rechercher un document
            </p>

            <p className="mt-1 text-sm text-slate-500">
              Trouver une information dans la base RAG.
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}

export default EmptyChat;
