/**
 * Settings store for managing LLM configuration.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { LLMConfig } from "@/lib/api";

interface SettingsState extends LLMConfig {
    setProvider: (provider: string) => void;
    setModel: (model: string) => void;
    setLocalUrl: (url: string) => void;
    setApiKey: (key: string) => void;
    setContextWindow: (window: number) => void;
    
    // Fast Tier Config
    fastProvider: string;
    fastModel: string;
    fastUrl: string;
    setFastProvider: (provider: string) => void;
    setFastModel: (model: string) => void;
    setFastUrl: (url: string) => void;
}

export const useSettingsStore = create<SettingsState>()(
    persist(
        (set) => ({
            provider: "Local (LM Studio)",
            model_name: "qwen2.5-7b-instruct",
            local_url: "http://localhost:1234/v1",
            api_key: "",
            context_window: 32768,

            setProvider: (provider) => set({ provider }),
            setModel: (model) => set({ model_name: model }),
            setLocalUrl: (url) => set({ local_url: url }),
            setApiKey: (key) => set({ api_key: key }),
            setContextWindow: (window) => set({ context_window: window }),

            // Fast Tier Defaults
            fastProvider: "Gemini",
            fastModel: "gemini-1.5-flash",
            fastUrl: "http://localhost:11434/v1",
            
            setFastProvider: (p) => set({ fastProvider: p }),
            setFastModel: (m) => set({ fastModel: m }),
            setFastUrl: (u) => set({ fastUrl: u }),
        }),
        {
            name: "llm-settings",
            // 安全：API Key 不落地到 localStorage（任何 XSS 都能直接讀走）。
            // 只保留非敏感設定，金鑰改為每個 session 重新輸入。
            partialize: (state) => ({
                provider: state.provider,
                model_name: state.model_name,
                local_url: state.local_url,
                context_window: state.context_window,
                fastProvider: state.fastProvider,
                fastModel: state.fastModel,
                fastUrl: state.fastUrl,
            }),
        }
    )
);
