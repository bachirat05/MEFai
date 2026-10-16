import {
  Copy,
  FileText,
  Sparkles,
  User,
} from "lucide-react";

import type { Message } from "../../types";

type ChatMessageProps = {
  message: Message;
  onCopy: (content: string) => void;
};

function ChatMessage({
  message,
  onCopy,
}: ChatMessageProps) {
  const isUser =
    message.role === "user";

  return (
    <div
      className={`flex gap-4 ${
        isUser
          ? "justify-end"
          : "justify-start"
      }`}
    >
      {!isUser ? (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
          <Sparkles size={17} />
        </div>
      ) : null}

      <div
        className={`max-w-[82%] ${
          isUser
            ? "rounded-2xl rounded-br-md bg-violet-600 px-5 py-3 text-white shadow-sm"
            : "min-w-0 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm"
        }`}
      >
        <div className="whitespace-pre-wrap text-sm leading-7">
          {message.content}
        </div>

        {!isUser && message.source ? (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
              <FileText
                size={14}
                className="text-violet-600"
              />

              <span className="text-xs font-medium text-slate-500">
                Source
              </span>

              <span className="text-xs font-semibold text-slate-700">
                {message.source}
              </span>
            </div>

            {message.category ? (
              <div className="rounded-xl border border-violet-100 bg-violet-50 px-3 py-2">
                <span className="text-xs font-medium text-violet-500">
                  Categorie
                </span>

                <span className="ml-2 text-xs font-semibold text-violet-700">
                  {message.category}
                </span>
              </div>
            ) : null}
          </div>
        ) : null}

        {!isUser ? (
          <div className="mt-3 flex items-center gap-1">
            <button
              type="button"
              onClick={() => onCopy(message.content)}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              title="Copier"
            >
              <Copy size={15} />
            </button>
          </div>
        ) : null}
      </div>

      {isUser ? (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm">
          <User size={16} />
        </div>
      ) : null}
    </div>
  );
}

export default ChatMessage;
