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
    appendToLastMessage: (delta: string) => void;
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

    // 注意：不可直接改動 state 內的既有物件（會破壞 selector 相等性/ memo）
    updateLastMessage: (content) =>
        set((state) => {
            if (state.messages.length === 0) return state;
            const messages = state.messages.slice();
            const last = messages[messages.length - 1];
            messages[messages.length - 1] = { ...last, content };
            return { messages };
        }),

    appendToLastMessage: (delta) =>
        set((state) => {
            if (state.messages.length === 0 || !delta) return state;
            const messages = state.messages.slice();
            const last = messages[messages.length - 1];
            messages[messages.length - 1] = {
                ...last,
                content: last.content + delta,
            };
            return { messages };
        }),

    setStreaming: (isStreaming) => set({ isStreaming }),

    setSelectedDocuments: (docs) => set({ selectedDocuments: docs }),

    clearMessages: () => set({ messages: [] }),
}));
