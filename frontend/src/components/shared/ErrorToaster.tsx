"use client";

import { useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";
import { useErrorStore, AppError } from "@/lib/errors";

function ErrorCard({ error }: { error: AppError }) {
  const dismissError = useErrorStore((s) => s.dismissError);

  useEffect(() => {
    if (!error.ttl) return;
    const timer = setTimeout(() => dismissError(error.id), error.ttl);
    return () => clearTimeout(timer);
  }, [error.id, error.ttl, dismissError]);

  return (
    <div
      role="alert"
      className="pointer-events-auto flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/95 px-4 py-3 shadow-lg backdrop-blur"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-600" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-red-800 break-words">
          {error.message}
        </p>
        {error.detail && (
          <p className="mt-1 text-xs text-red-700/80 break-words">
            {error.detail}
          </p>
        )}
      </div>
      <button
        type="button"
        aria-label="關閉錯誤訊息"
        onClick={() => dismissError(error.id)}
        className="rounded p-1 text-red-500 transition-colors hover:bg-red-100 hover:text-red-700"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

/**
 * 全域錯誤提示容器（掛在 Providers 內）。
 *
 * API 失敗會由 `apiFetch` / `apiStream` 自動推送，因此使用者不會再遇到
 * 「按了沒反應、只有 console 有錯」的情況。
 */
export function ErrorToaster() {
  const errors = useErrorStore((s) => s.errors);

  if (errors.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2">
      {errors.map((error) => (
        <ErrorCard key={error.id} error={error} />
      ))}
    </div>
  );
}
