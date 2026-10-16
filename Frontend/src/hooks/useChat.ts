import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import type { User } from "firebase/auth";

import {
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
  sendChatMessage,
} from "../services/api";

import type {
  ChatApiResponse,
  Conversation,
  Message,
} from "../types";

type UseChatProps = {
  user: User | null;
};

function extractDisplayMessage(
  message: Message
): Message {
  const sourceMatch =
    message.content.match(
      /\[Source:\s*([^|]+)\s*\|\s*Category:\s*([^\]]+)\]/i
    );

  const source =
    sourceMatch?.[1]?.trim();

  const category =
    sourceMatch?.[2]?.trim();

  const cleanContent =
    message.content
      .replace(
        /\[Source:\s*[^|]+\s*\|\s*Category:\s*[^\]]+\]/gi,
        ""
      )
      .trim();

  return {
    ...message,
    content:
      cleanContent || message.content,
    source,
    category,
  };
}

function withDisplayMessages(
  conversation: Conversation
): Conversation {
  return {
    ...conversation,
    messages:
      conversation.messages.map(
        extractDisplayMessage
      ),
  };
}

export function useChat({
  user,
}: UseChatProps) {
  const [message, setMessage] =
    useState<string>("");

  const [isLoading, setIsLoading] =
    useState<boolean>(false);

  const [isHistoryLoading, setIsHistoryLoading] =
    useState<boolean>(false);

  const [conversations, setConversations] =
    useState<Conversation[]>([]);

  const [activeConversationId, setActiveConversationId] =
    useState<number | null>(null);

  const messagesEndRef =
    useRef<HTMLDivElement | null>(null);

  const activeUserUidRef =
    useRef<string | null>(null);

  const activeConversation =
    conversations.find(
      (conversation) =>
        conversation.id ===
        activeConversationId
    );

  const messages: Message[] =
    activeConversation?.messages ?? [];

  const loadConversation = useCallback(
    async (
      conversationId: number
    ): Promise<void> => {
      if (!user) {
        return;
      }

      const currentUid = user.uid;

      const token =
        await user.getIdToken();

      const loaded =
        withDisplayMessages(
          await getConversation(
            token,
            conversationId
          )
        );

      if (
        activeUserUidRef.current !==
        currentUid
      ) {
        return;
      }

      setConversations(
        (previousConversations) => {
          const exists =
            previousConversations.some(
              (conversation) =>
                conversation.id === loaded.id
            );

          if (!exists) {
            return [
              loaded,
              ...previousConversations,
            ];
          }

          return previousConversations.map(
            (conversation) =>
              conversation.id === loaded.id
                ? loaded
                : conversation
          );
        }
      );
    },
    [user]
  );

  useEffect(() => {
    let isCurrent = true;
    activeUserUidRef.current =
      user?.uid ?? null;

    setMessage("");
    setIsLoading(false);
    setConversations([]);
    setActiveConversationId(null);

    if (!user) {
      setIsHistoryLoading(false);
      return () => {
        isCurrent = false;
      };
    }

    setIsHistoryLoading(true);

    const loadHistory =
      async (): Promise<void> => {
        try {
          const currentUid = user.uid;

          const token =
            await user.getIdToken();

          const loadedConversations =
            await getConversations(token);

          if (
            !isCurrent ||
            activeUserUidRef.current !==
              currentUid
          ) {
            return;
          }

          setConversations(
            loadedConversations
          );

          const firstConversation =
            loadedConversations[0];

          if (firstConversation) {
            setActiveConversationId(
              firstConversation.id
            );

            void loadConversation(
              firstConversation.id
            );
          }
        } catch (error) {
          if (isCurrent) {
            console.error(
              "Impossible de charger l'historique du chat:",
              error
            );

            setConversations([]);
            setActiveConversationId(null);
          }
        } finally {
          if (isCurrent) {
            setIsHistoryLoading(false);
          }
        }
      };

    void loadHistory();

    return () => {
      isCurrent = false;
    };
  }, [
    user,
    loadConversation,
  ]);

  const selectConversation =
    async (
      conversationId: number
    ): Promise<void> => {
      setActiveConversationId(
        conversationId
      );

      try {
        await loadConversation(
          conversationId
        );
      } catch (error) {
        console.error(
          "Impossible de charger la conversation:",
          error
        );
      }
    };

  const createNewConversation =
    async (): Promise<void> => {
      if (!user) {
        return;
      }

      try {
        const token =
          await user.getIdToken();

        const newConversation =
          withDisplayMessages(
            await createConversation(token)
          );

        setConversations(
          (previousConversations) => [
            newConversation,
            ...previousConversations,
          ]
        );

        setActiveConversationId(
          newConversation.id
        );

        setMessage("");
      } catch (error) {
        console.error(
          "Impossible de créer une conversation:",
          error
        );
      }
    };

  const deleteExistingConversation =
    async (
      conversationId: number
    ): Promise<void> => {
      if (!user) {
        return;
      }

      const currentUid = user.uid;

      try {
        const token =
          await user.getIdToken();

        await deleteConversation(
          token,
          conversationId
        );

        if (
          activeUserUidRef.current !==
          currentUid
        ) {
          return;
        }

        setConversations(
          (previousConversations) => {
            const remaining =
              previousConversations.filter(
                (conversation) =>
                  conversation.id !==
                  conversationId
              );

            if (
              activeConversationId ===
              conversationId
            ) {
              setActiveConversationId(
                remaining[0]?.id ?? null
              );
            }

            return remaining;
          }
        );
      } catch (error) {
        console.error(
          "Impossible de supprimer la conversation:",
          error
        );
      }
    };

  const sendMessage =
    async (): Promise<void> => {
      const text = message.trim();

      if (!text || isLoading || !user) {
        return;
      }

      const localConversationId =
        activeConversationId;

      const optimisticUserMessage: Message = {
        id: Date.now(),
        role: "user",
        content: text,
      };

      setMessage("");
      setIsLoading(true);

      if (localConversationId !== null) {
        setConversations(
          (previousConversations) =>
            previousConversations.map(
              (conversation) =>
                conversation.id ===
                localConversationId
                  ? {
                      ...conversation,
                      messages: [
                        ...conversation.messages,
                        optimisticUserMessage,
                      ],
                    }
                  : conversation
            )
        );
      }

      try {
        const token =
          await user.getIdToken();

        const data: ChatApiResponse =
          await sendChatMessage(
            token,
            text,
            localConversationId
          );

        const conversationId =
          data.conversation_id;

        if (localConversationId === null) {
          setActiveConversationId(
            conversationId
          );
        }

        await loadConversation(
          conversationId
        );
      } catch (error: unknown) {
        console.error(
          "Chat API error:",
          error
        );

        const errorMessage: Message = {
          id: Date.now() + 1,
          role: "assistant",
          content:
            error instanceof Error
              ? `Erreur serveur : ${error.message}`
              : "Une erreur est survenue lors de la communication avec le serveur.",
        };

        if (localConversationId !== null) {
          setConversations(
            (previousConversations) =>
              previousConversations.map(
                (conversation) =>
                  conversation.id ===
                  localConversationId
                    ? {
                        ...conversation,
                        messages: [
                          ...conversation.messages,
                          errorMessage,
                        ],
                      }
                    : conversation
              )
          );
        }
      } finally {
        setIsLoading(false);
      }
    };

  const handleKeyDown = (
    event: KeyboardEvent<HTMLTextAreaElement>
  ): void => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      void sendMessage();
    }
  };

  const copyMessage = async (
    content: string
  ): Promise<void> => {
    try {
      await navigator.clipboard.writeText(
        content
      );
    } catch (error) {
      console.error(
        "Copy error:",
        error
      );
    }
  };

  return {
    message,
    setMessage,

    isLoading,
    isHistoryLoading,

    conversations,

    activeConversationId,
    setActiveConversationId:
      selectConversation,

    messages,

    messagesEndRef,

    createNewConversation,
    deleteExistingConversation,
    sendMessage,
    handleKeyDown,
    copyMessage,
  };
}
