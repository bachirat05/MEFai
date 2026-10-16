import type {
  KeyboardEvent,
  RefObject,
} from "react";

import { Sparkles } from "lucide-react";

import type { Message } from "../../types";

import ChatInput from "./ChatInput";
import ChatMessage from "./ChatMessage";
import EmptyChat from "./EmptyChat";

type ChatPanelProps = {
  messages: Message[];

  message: string;

  isLoading: boolean;

  messagesEndRef: RefObject<HTMLDivElement | null>;

  onMessageChange: (value: string) => void;

  onSend: () => void;

  onKeyDown: (
    event: KeyboardEvent<HTMLTextAreaElement>
  ) => void;

  onCopy: (content: string) => void;
};

function ChatPanel({
  messages,
  message,
  isLoading,
  messagesEndRef,
  onMessageChange,
  onSend,
  onKeyDown,
  onCopy,
}: ChatPanelProps) {
  return (
    <section className="flex min-h-0 flex-1 flex-col">

      {/* MESSAGES */}

      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (

          <EmptyChat
            onSelectPrompt={onMessageChange}
          />

        ) : (

          <div className="mx-auto w-full max-w-4xl px-5 py-8 md:px-8">
            <div className="space-y-8">

              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onCopy={onCopy}
                />
              ))}

              {/* LOADING */}

              {isLoading && (
                <div className="flex gap-4">

                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
                    <Sparkles size={17} />
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-1">

                    <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400" />

                    <span
                      className="h-2 w-2 animate-bounce rounded-full bg-violet-400"
                      style={{
                        animationDelay: "150ms",
                      }}
                    />

                    <span
                      className="h-2 w-2 animate-bounce rounded-full bg-violet-400"
                      style={{
                        animationDelay: "300ms",
                      }}
                    />

                    </div>
                  </div>

                </div>
              )}

              <div ref={messagesEndRef} />

            </div>
          </div>

        )}
      </div>

      {/* INPUT */}

      <ChatInput
        message={message}
        isLoading={isLoading}
        onChange={onMessageChange}
        onSend={onSend}
        onKeyDown={onKeyDown}
      />

    </section>
  );
}

export default ChatPanel;
