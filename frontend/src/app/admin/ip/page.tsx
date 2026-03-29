"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { useAnalytics } from "@/hooks/useAnalytics";
import {
  Globe,
  Plus,
  Trash2,
  Shield,
  Lock,
  Clock,
  AlertCircle,
  Activity,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface IPEntry {
  id: number;
  ip_address: string;
  description?: string;
  reason?: string;
  created_at: string;
  expires_at?: string;
  is_active: boolean;
}

interface IPStats {
  whitelist_count: number;
  blacklist_count: number;
  blocked_attempts: number;
  unique_ips: number;
}

export default function IPManagementPage() {
  const [whitelist, setWhitelist] = useState<IPEntry[]>([]);
  const [blacklist, setBlacklist] = useState<IPEntry[]>([]);
  const [stats, setStats] = useState<IPStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"whitelist" | "blacklist" | "logs">("whitelist");
  const [newIP, setNewIP] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newReason, setNewReason] = useState("");
  const [expiresDays, setExpiresDays] = useState("");
  const { user } = useAuthStore();
  const { trackClick } = useAnalytics();

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    const token = localStorage.getItem("auth_token");
    try {
      const [wlRes, blRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/admin/ip/whitelist`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/admin/ip/blacklist`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/admin/ip/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (wlRes.ok) setWhitelist(await wlRes.json());
      if (blRes.ok) setBlacklist(await blRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      console.error("載入資料失敗:", err);
    } finally {
      setIsLoading(false);
    }
  }

  async function addToWhitelist() {
    if (!newIP.trim()) return;
    trackClick("add_ip_whitelist", { ip: newIP });

    const token = localStorage.getItem("auth_token");
    try {
      const res = await fetch(`${API_BASE}/api/admin/ip/whitelist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ip_address: newIP,
          description: newDescription,
        }),
      });

      if (res.ok) {
        setNewIP("");
        setNewDescription("");
        loadData();
      } else {
        const data = await res.json();
        alert(data.detail || "新增失敗");
      }
    } catch (err) {
      alert("新增失敗");
    }
  }

  async function addToBlacklist() {
    if (!newIP.trim()) return;
    trackClick("add_ip_blacklist", { ip: newIP });

    const token = localStorage.getItem("auth_token");
    try {
      const res = await fetch(`${API_BASE}/api/admin/ip/blacklist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ip_address: newIP,
          reason: newReason,
          expires_days: expiresDays ? parseInt(expiresDays) : null,
        }),
      });

      if (res.ok) {
        setNewIP("");
        setNewReason("");
        setExpiresDays("");
        loadData();
      } else {
        const data = await res.json();
        alert(data.detail || "新增失敗");
      }
    } catch (err) {
      alert("新增失敗");
    }
  }

  async function removeFromWhitelist(id: number) {
    trackClick("remove_ip_whitelist", { id });
    const token = localStorage.getItem("auth_token");
    try {
      await fetch(`${API_BASE}/api/admin/ip/whitelist/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      loadData();
    } catch (err) {
      alert("移除失敗");
    }
  }

  async function removeFromBlacklist(id: number) {
    trackClick("remove_ip_blacklist", { id });
    const token = localStorage.getItem("auth_token");
    try {
      await fetch(`${API_BASE}/api/admin/ip/blacklist/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      loadData();
    } catch (err) {
      alert("移除失敗");
    }
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
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Globe className="w-7 h-7" />
            IP 存取管理
          </h1>
          <p className="text-slate-500 mt-1">
            管理 IP 白名單與黑名單，控制系統存取權限
          </p>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-slate-500">載入中...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <Card className="p-4">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-green-600" />
                  <div>
                    <div className="text-xl font-bold">{stats?.whitelist_count || 0}</div>
                    <div className="text-xs text-slate-500">白名單數量</div>
                  </div>
                </div>
              </Card>
              <Card className="p-4">
                <div className="flex items-center gap-3">
                  <Lock className="w-5 h-5 text-red-600" />
                  <div>
                    <div className="text-xl font-bold">{stats?.blacklist_count || 0}</div>
                    <div className="text-xs text-slate-500">黑名單數量</div>
                  </div>
                </div>
              </Card>
              <Card className="p-4">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                  <div>
                    <div className="text-xl font-bold">{stats?.blocked_attempts || 0}</div>
                    <div className="text-xs text-slate-500">封鎖次數</div>
                  </div>
                </div>
              </Card>
              <Card className="p-4">
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-blue-600" />
                  <div>
                    <div className="text-xl font-bold">{stats?.unique_ips || 0}</div>
                    <div className="text-xs text-slate-500">獨立 IP 數</div>
                  </div>
                </div>
              </Card>
            </div>

            <div className="flex gap-2 mb-4">
              <Button
                variant={activeTab === "whitelist" ? "default" : "outline"}
                onClick={() => {
                  trackClick("ip_tab_whitelist");
                  setActiveTab("whitelist");
                }}
              >
                白名單
              </Button>
              <Button
                variant={activeTab === "blacklist" ? "default" : "outline"}
                onClick={() => {
                  trackClick("ip_tab_blacklist");
                  setActiveTab("blacklist");
                }}
              >
                黑名單
              </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">
                  {activeTab === "whitelist" ? "新增 IP 到白名單" : "新增 IP 到黑名單"}
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      IP 位址
                    </label>
                    <input
                      type="text"
                      value={newIP}
                      onChange={(e) => setNewIP(e.target.value)}
                      placeholder="例如：192.168.1.100"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    />
                  </div>

                  {activeTab === "whitelist" ? (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        描述
                      </label>
                      <input
                        type="text"
                        value={newDescription}
                        onChange={(e) => setNewDescription(e.target.value)}
                        placeholder="例如：公司辦公室"
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                    </div>
                  ) : (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                          封鎖原因
                        </label>
                        <input
                          type="text"
                          value={newReason}
                          onChange={(e) => setNewReason(e.target.value)}
                          placeholder="例如：惡意攻擊"
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                          封鎖天數（選填，空白則永久）
                        </label>
                        <input
                          type="number"
                          value={expiresDays}
                          onChange={(e) => setExpiresDays(e.target.value)}
                          placeholder="例如：30"
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                      </div>
                    </>
                  )}

                  <Button
                    onClick={activeTab === "whitelist" ? addToWhitelist : addToBlacklist}
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    新增
                  </Button>
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">
                  {activeTab === "whitelist" ? "白名單列表" : "黑名單列表"}
                </h3>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {(activeTab === "whitelist" ? whitelist : blacklist).length === 0 ? (
                    <p className="text-slate-500 text-sm text-center py-4">
                      尚無資料
                    </p>
                  ) : (
                    (activeTab === "whitelist" ? whitelist : blacklist).map((entry) => (
                      <div
                        key={entry.id}
                        className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                      >
                        <div>
                          <div className="font-mono text-sm">{entry.ip_address}</div>
                          <div className="text-xs text-slate-500">
                            {entry.description || entry.reason || "無描述"}
                            {entry.expires_at && (
                              <span className="ml-2">
                                • 到期：{new Date(entry.expires_at).toLocaleDateString("zh-TW")}
                              </span>
                            )}
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            activeTab === "whitelist"
                              ? removeFromWhitelist(entry.id)
                              : removeFromBlacklist(entry.id)
                          }
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
