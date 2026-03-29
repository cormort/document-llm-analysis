"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { useAnalytics } from "@/hooks/useAnalytics";
import {
  Settings,
  Key,
  Clock,
  Shield,
  Globe,
  Lock,
  Save,
  RefreshCw,
} from "lucide-react";

export default function SystemSettingsPage() {
  const [jwtExpiry, setJwtExpiry] = useState("24");
  const [sessionTimeout, setSessionTimeout] = useState("60");
  const [ipWhitelistEnabled, setIpWhitelistEnabled] = useState(false);
  const [ipBlacklistEnabled, setIpBlacklistEnabled] = useState(true);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { user } = useAuthStore();
  const { trackClick } = useAnalytics();

  async function handleSave() {
    trackClick("save_system_settings");
    setIsSaving(true);
    
    setTimeout(() => {
      setIsSaving(false);
      alert("設定已儲存（此為示範，實際需連接後端 API）");
    }, 1000);
  }

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
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Settings className="w-7 h-7" />
            系統設定
          </h1>
          <p className="text-slate-500 mt-1">管理認證、安全與系統設定</p>
        </div>

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Key className="w-5 h-5" />
              JWT 認證設定
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Token 有效期（小時）
                </label>
                <input
                  type="number"
                  value={jwtExpiry}
                  onChange={(e) => setJwtExpiry(e.target.value)}
                  className="w-32 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
                <p className="text-xs text-slate-500 mt-1">
                  建議值：12-24 小時。過長會降低安全性，過短會影響使用者體驗。
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Session 閒置逾時（分鐘）
                </label>
                <input
                  type="number"
                  value={sessionTimeout}
                  onChange={(e) => setSessionTimeout(e.target.value)}
                  className="w-32 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
                <p className="text-xs text-slate-500 mt-1">
                  使用者閒置超過此時間後，需重新驗證。
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5" />
              IP 存取控制
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-slate-900">啟用 IP 白名單</div>
                  <div className="text-sm text-slate-500">
                    只允許白名單中的 IP 存取系統
                  </div>
                </div>
                <button
                  onClick={() => {
                    trackClick("toggle_ip_whitelist");
                    setIpWhitelistEnabled(!ipWhitelistEnabled);
                  }}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    ipWhitelistEnabled ? "bg-blue-600" : "bg-slate-300"
                  }`}
                >
                  <div
                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      ipWhitelistEnabled ? "translate-x-7" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-slate-900">啟用 IP 黑名單</div>
                  <div className="text-sm text-slate-500">
                    封鎖黑名單中的 IP 存取系統
                  </div>
                </div>
                <button
                  onClick={() => {
                    trackClick("toggle_ip_blacklist");
                    setIpBlacklistEnabled(!ipBlacklistEnabled);
                  }}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    ipBlacklistEnabled ? "bg-blue-600" : "bg-slate-300"
                  }`}
                >
                  <div
                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      ipBlacklistEnabled ? "translate-x-7" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-start gap-2">
                  <Lock className="w-5 h-5 text-amber-600 mt-0.5" />
                  <div className="text-sm">
                    <div className="font-medium text-amber-800">注意</div>
                    <div className="text-amber-700">
                      啟用白名單後，只有白名單中的 IP 能存取系統。
                      請確保您的 IP 已加入白名單，否則將無法登入。
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5" />
              SSO 整合（預覽）
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-slate-900">啟用 SSO</div>
                  <div className="text-sm text-slate-500">
                    允許使用者透過外部身份提供商登入
                  </div>
                </div>
                <button
                  onClick={() => {
                    trackClick("toggle_sso");
                    setSsoEnabled(!ssoEnabled);
                  }}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    ssoEnabled ? "bg-blue-600" : "bg-slate-300"
                  }`}
                >
                  <div
                    className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      ssoEnabled ? "translate-x-7" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              {ssoEnabled && (
                <div className="space-y-3 pt-4 border-t border-slate-200">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        OAuth2 Provider
                      </label>
                      <select className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
                        <option>Google</option>
                        <option>GitHub</option>
                        <option>Microsoft</option>
                        <option>自訂</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Client ID
                      </label>
                      <input
                        type="text"
                        placeholder="輸入 Client ID"
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Client Secret
                    </label>
                    <input
                      type="password"
                      placeholder="輸入 Client Secret"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    />
                  </div>
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="text-sm text-blue-700">
                      <div className="font-medium">Callback URL</div>
                      <code className="text-xs mt-1 block">
                        {window.location.origin}/api/auth/sso/callback
                      </code>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5" />
              系統資訊
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-slate-500">認證方式</div>
                <div className="font-medium">JWT Token</div>
              </div>
              <div>
                <div className="text-slate-500">加密演算法</div>
                <div className="font-medium">HS256</div>
              </div>
              <div>
                <div className="text-slate-500">密碼雜湊</div>
                <div className="font-medium">bcrypt</div>
              </div>
              <div>
                <div className="text-slate-500">資料庫</div>
                <div className="font-medium">SQLite</div>
              </div>
            </div>
          </Card>

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => {
                trackClick("reset_settings");
                setJwtExpiry("24");
                setSessionTimeout("60");
                setIpWhitelistEnabled(false);
                setIpBlacklistEnabled(true);
                setSsoEnabled(false);
              }}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              重設預設值
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? "儲存中..." : "儲存設定"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
