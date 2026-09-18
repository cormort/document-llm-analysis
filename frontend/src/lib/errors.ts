"use client";

import { create } from "zustand";

export interface AppError {
  id: string;
  message: string;
  detail?: string;
  /** 自動消失時間（毫秒）；0 代表需手動關閉 */
  ttl: number;
  createdAt: number;
}

interface ErrorState {
  errors: AppError[];
  pushError: (message: string, options?: { detail?: string; ttl?: number }) => void;
  dismissError: (id: string) => void;
  clearErrors: () => void;
}

const DEFAULT_TTL = 8000;
const MAX_ERRORS = 3;

/**
 * 全域錯誤提示。
 *
 * 這個專案先前有 40+ 處錯誤只寫進 `console.error`，使用者看到的是「按了沒反應」。
 * `apiFetch` / `apiStream` 會自動把 API 失敗推進來，因此不需要逐一改動呼叫端。
 */
export const useErrorStore = create<ErrorState>((set) => ({
  errors: [],

  pushError: (message, options) =>
    set((state) => {
      const trimmed = (message || "").trim();
      if (!trimmed) return state;

      // 同樣的訊息短時間內重複發生時，只保留一則（例如輪詢一直失敗）
      const now = Date.now();
      const duplicate = state.errors.find(
        (e) => e.message === trimmed && now - e.createdAt < 3000
      );
      if (duplicate) return state;

      const error: AppError = {
        id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
        message: trimmed,
        detail: options?.detail,
        ttl: options?.ttl ?? DEFAULT_TTL,
        createdAt: now,
      };
      const errors = [...state.errors, error].slice(-MAX_ERRORS);
      return { errors };
    }),

  dismissError: (id) =>
    set((state) => ({ errors: state.errors.filter((e) => e.id !== id) })),

  clearErrors: () => set({ errors: [] }),
}));

/** 給非 React 程式碼（例如 lib/api.ts）使用的捷徑。 */
export function reportError(
  message: string,
  options?: { detail?: string; ttl?: number }
): void {
  useErrorStore.getState().pushError(message, options);
}
