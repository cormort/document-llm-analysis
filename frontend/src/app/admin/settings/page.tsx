"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { apiFetch } from "@/lib/api";
import {
  Settings,
  Shield,
  Lock,
  RefreshCw,
  Server,
  Gauge,
  Database,
} from "lucide-react";

interface SystemInfo {
  environment: string;
  auth: {
    anonymous_access: boolean;
    jwt_algorithm: string;
    jwt_expire_hours: number;
    jwt_secret_configured: boolean;
    jwt_secret_source: string;
    jwt_secret_fingerprint: string | null;
  };
  security: {
    metrics_require_auth: boolean;
    allow_private_llm_urls: boolean;
    allow_client_api_keys: boolean;
    cors_origins: string[] | string;
  };
  limits: {
    rate_limit_default: string;
    max_upload_size_mb: number;
  };
  llm_defaults: {
    fast_provider: string;
    fast_model: string;
    smart_provider: string;
    smart_model: string;
    google_api_key_configured: boolean;
    omlx_api_key_configured: boolean;
  };
  database: { url: string };
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-2 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-right text-sm font-medium text-slate-800 break-all">
        {value}
      </span>
    </div>
  );
}

function Flag({ on, label }: { on: boolean; label: string }) {
  return (
    <span
      className={`rounded-md px-2 py-0.5 text-xs font-bold ${
        on ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
      }`}
    >
      {label}
    </span>
  );
}

export default function SystemSettingsPage() {
  const user = useAuthStore((s) => s.user);
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setInfo(await apiFetch<SystemInfo>("/api/admin/system-info"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法取得系統資訊");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50/50">
        <Card className="p-8">
          <h1 className="text-xl font-bold text-red-600">權限不足</h1>
          <p className="text-slate-500 mt-2">您需要管理員權限才能訪問此頁面</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/50 p-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Settings className="h-7 w-7" />
              系統資訊
            </h1>
            <p className="mt-1 text-slate-500">
              目前實際生效的後端設定（唯讀、不含金鑰內容）。這些值來自環境變數 /{" "}
              <code className="rounded bg-slate-100 px-1">.env</code>，修改後需重啟後端。
            </p>
          </div>
          <Button variant="outline" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            重新整理
          </Button>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </Card>
        )}

        {info && (
          <>
            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Server className="h-5 w-5 text-blue-600" />
                執行環境
              </h2>
              <InfoRow label="ENVIRONMENT" value={info.environment} />
              <InfoRow label="資料庫" value={info.database.url} />
            </Card>

            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Shield className="h-5 w-5 text-emerald-600" />
                認證與金鑰
              </h2>
              <InfoRow
                label="允許匿名存取 API"
                value={
                  <Flag
                    on={!info.auth.anonymous_access}
                    label={info.auth.anonymous_access ? "是（不建議）" : "否"}
                  />
                }
              />
              <InfoRow
                label="JWT 演算法 / 有效時數"
                value={`${info.auth.jwt_algorithm} / ${info.auth.jwt_expire_hours} 小時`}
              />
              <InfoRow
                label="JWT 金鑰來源"
                value={
                  info.auth.jwt_secret_source === "env"
                    ? "環境變數 JWT_SECRET_KEY"
                    : "自動產生（開發用，存於 data/.jwt_secret）"
                }
              />
              <InfoRow
                label="JWT 金鑰指紋"
                value={info.auth.jwt_secret_fingerprint ?? "（未設定）"}
              />
              <InfoRow
                label="接受前端傳入的 API Key"
                value={
                  <Flag
                    on={info.security.allow_client_api_keys}
                    label={info.security.allow_client_api_keys ? "開啟" : "關閉（僅用伺服器金鑰）"}
                  />
                }
              />
            </Card>

            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Lock className="h-5 w-5 text-amber-600" />
                安全邊界
              </h2>
              <InfoRow
                label="/metrics 需要認證"
                value={
                  <Flag
                    on={!info.security.metrics_require_auth}
                    label={info.security.metrics_require_auth ? "需要" : "公開"}
                  />
                }
              />
              <InfoRow
                label="允許 LLM URL 指向私有網段"
                value={
                  <Flag
                    on={info.security.allow_private_llm_urls}
                    label={
                      info.security.allow_private_llm_urls
                        ? "允許（本機 Ollama / LM Studio）"
                        : "禁止"
                    }
                  />
                }
              />
              <InfoRow
                label="CORS 允許來源"
                value={
                  Array.isArray(info.security.cors_origins)
                    ? info.security.cors_origins.join(", ") || "（未設定）"
                    : info.security.cors_origins
                }
              />
              <InfoRow
                label="速率限制 / 上傳上限"
                value={`${info.limits.rate_limit_default} · ${info.limits.max_upload_size_mb} MB`}
              />
            </Card>

            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Gauge className="h-5 w-5 text-purple-600" />
                LLM 預設路由
              </h2>
              <InfoRow
                label="Fast 層"
                value={`${info.llm_defaults.fast_provider} / ${info.llm_defaults.fast_model}`}
              />
              <InfoRow
                label="Smart 層"
                value={`${info.llm_defaults.smart_provider} / ${info.llm_defaults.smart_model}`}
              />
              <InfoRow
                label="伺服器端金鑰"
                value={
                  <span className="inline-flex gap-3 text-xs">
                    <span
                      className={
                        info.llm_defaults.google_api_key_configured
                          ? "text-emerald-600"
                          : "text-slate-400"
                      }
                    >
                      GOOGLE_API_KEY{" "}
                      {info.llm_defaults.google_api_key_configured ? "✓" : "✗"}
                    </span>
                    <span
                      className={
                        info.llm_defaults.omlx_api_key_configured
                          ? "text-emerald-600"
                          : "text-slate-400"
                      }
                    >
                      OMLX_API_KEY{" "}
                      {info.llm_defaults.omlx_api_key_configured ? "✓" : "✗"}
                    </span>
                  </span>
                }
              />
            </Card>

            <Card className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Database className="h-5 w-5 text-slate-600" />
                其他管理功能
              </h2>
              <div className="flex flex-wrap gap-3">
                <Link href="/admin/users">
                  <Button variant="outline">使用者管理</Button>
                </Link>
                <Link href="/admin/ip">
                  <Button variant="outline">IP 白名單 / 黑名單</Button>
                </Link>
                <Link href="/admin/analytics">
                  <Button variant="outline">使用分析</Button>
                </Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                註：本頁先前顯示的 HS256 / bcrypt / SQLite 是硬編碼示範文字，儲存按鈕只做了{" "}
                <code>setTimeout</code> 與 <code>alert</code>。現在改為顯示後端實際回報的設定。
              </p>
            </Card>
          </>
        )}

        {!info && !error && (
          <Card className="p-6 text-sm text-slate-500">載入中…</Card>
        )}
      </div>
    </div>
  );
}
