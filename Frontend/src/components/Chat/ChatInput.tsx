import type { KeyboardEvent } from "react";

import {
  Paperclip,
  Send,
} from "lucide-react";

type ChatInputProps = {
  message: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (
    event: KeyboardEvent<HTMLTextAreaElement>
  ) => void;
};

function ChatInput({
  message,
  isLoading,
  onChange,
  onSend,
  onKeyDown,
}: ChatInputProps) {
  return (
    <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-5 md:px-8">
      <div className="mx-auto max-w-4xl">

        <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2 shadow-sm transition focus-within:border-violet-400 focus-within:ring-2 focus-within:ring-violet-100">

          <button
            type="button"
            className="rounded-xl p-3 text-slate-400 transition hover:bg-white hover:text-violet-600"
            title="Ajouter un fichier"
          >
            <Paperclip size={19} />
          </button>

          <textarea
            value={message}
            onChange={(event) =>
              onChange(event.target.value)
            }
            onKeyDown={onKeyDown}
            placeholder="Posez votre question..."
            rows={1}
            className="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-2 py-3 text-sm outline-none placeholder:text-slate-400"
          />

          <button
            type="button"
            onClick={onSend}
            disabled={
              !message.trim() ||
              isLoading
            }
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
            title="Envoyer"
          >
            <Send size={18} />
          </button>

        </div>

        <p className="mt-3 text-center text-xs text-slate-400">
          L'assistant peut utiliser les documents internes pour répondre à vos questions.
        </p>

      </div>
    </div>
  );
}

export default ChatInput;