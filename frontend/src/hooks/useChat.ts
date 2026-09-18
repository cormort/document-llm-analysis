"use client";

import { useCallback } from "react";
import { useChatStore } from "@/stores/chat-store";
import { useSettingsStore } from "@/stores/settings-store";
import { queryAgentStream, queryRAGStream } from "@/lib/api";

export interface UseChatOptions {
    /** RAG: collection names to query. Agent: leave empty or omit. */
    selectedDocuments?: string[];
    useHybrid?: boolean;
    useQueryExpansion?: boolean;
    useCompression?: boolean;
    useRerank?: boolean;
    /** Force a specific mode. Defaults to "rag" when documents are selected. */
    mode?: "agent" | "rag";
}

/**
 * Unified chat hook that abstracts RAG vs Agent stream selection.
 *
 * Fixes:
 *  - Routing logic was duplicated across TabbedPanel, ChatInterface, and rag/page.tsx
 *  - String concatenation in streaming loop was O(n²); replaced with array buffer
 */
export function useChat(options: UseChatOptions = {}) {
    const {
        selectedDocuments = [],
        useHybrid,
        useQueryExpansion,
        useCompression,
        useRerank,
        mode,
    } = options;

    const { addMessage, updateLastMessage, appendToLastMessage, setStreaming, isStreaming } =
        useChatStore();
    const provider = useSettingsStore((s) => s.provider);
    const model_name = useSettingsStore((s) => s.model_name);
    const local_url = useSettingsStore((s) => s.local_url);
    const api_key = useSettingsStore((s) => s.api_key);

    const sendMessage = useCallback(
        async (question: string) => {
            if (!question.trim() || isStreaming) return;

            addMessage({ role: "user", content: question });
            setStreaming(true);
            addMessage({ role: "assistant", content: "" });

            try {
                // Determine which API to use
                const useRAG =
                    mode === "rag" ||
                    (selectedDocuments.length > 0 && mode !== "agent");

                const stream = useRAG
                    ? queryRAGStream({
                          question,
                          collection_names: selectedDocuments,
                          use_hybrid: useHybrid,
                          use_query_expansion: useQueryExpansion,
                          use_compression: useCompression,
                          use_rerank: useRerank ?? true,
                          config: { provider, model_name, local_url, api_key },
                      })
                    : queryAgentStream({
                          message: question,
                          llm_config: {
                              provider,
                              model_name,
                              local_url,
                              api_key,
                          },
                      });

                // 逐 chunk 重新 join 整個陣列是 O(n²)；改成累積待寫入內容，
                // 每個動畫幀最多更新一次 state。
                let pending = "";
                let scheduled = false;
                const flush = () => {
                    scheduled = false;
                    if (pending) {
                        appendToLastMessage(pending);
                        pending = "";
                    }
                };
                const scheduleFlush = () => {
                    if (scheduled) return;
                    scheduled = true;
                    if (typeof requestAnimationFrame === "function") {
                        requestAnimationFrame(flush);
                    } else {
                        flush();
                    }
                };

                try {
                    for await (const chunk of stream) {
                        pending += chunk;
                        scheduleFlush();
                    }
                } finally {
                    // 收尾時務必把剩下的內容寫進 state
                    if (typeof requestAnimationFrame === "function" && scheduled) {
                        await new Promise((resolve) =>
                            requestAnimationFrame(() => resolve(null))
                        );
                    }
                    flush();
                }
            } catch (error) {
                updateLastMessage(
                    `❌ 發生錯誤: ${
                        error instanceof Error ? error.message : "Unknown error"
                    }`
                );
            } finally {
                setStreaming(false);
            }
        },
        [
            isStreaming,
            selectedDocuments,
            useHybrid,
            useQueryExpansion,
            useCompression,
            useRerank,
            mode,
            provider,
            model_name,
            local_url,
            api_key,
            addMessage,
            updateLastMessage,
            appendToLastMessage,
            setStreaming,
        ]
    );

    return { sendMessage, isStreaming };
}
