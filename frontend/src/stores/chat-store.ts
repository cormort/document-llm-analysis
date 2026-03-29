/**
 * Chat store using Zustand for state management.
 */

import { create } from "zustand";

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: object[];
    timestamp: Date;
}

interface ChatState {
    messages: ChatMessage[];
    isStreaming: boolean;
    selectedDocuments: string[];
    addMessage: (message: Omit<ChatMessage, "id" | "timestamp">) => void;
    updateLastMessage: (content: string) => void;
    setStreaming: (isStreaming: boolean) => void;
    setSelectedDocuments: (docs: string[]) => void;
    clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
    messages: [],
    isStreaming: false,
    selectedDocuments: [],

    addMessage: (message) =>
        set((state) => ({
            messages: [
                ...state.messages,
                {
                    ...message,
                    id: crypto.randomUUID(),
                    timestamp: new Date(),
                },
            ],
        })),

    updateLastMessage: (content) =>
        set((state) => {
            const messages = [...state.messages];
            if (messages.length > 0) {
                messages[messages.length - 1].content = content;
            }
            return { messages };
        }),

    setStreaming: (isStreaming) => set({ isStreaming }),

    setSelectedDocuments: (docs) => set({ selectedDocuments: docs }),

    clearMessages: () => set({ messages: [] }),
}));
