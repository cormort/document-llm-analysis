"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth-store";
import { useAnalytics } from "@/hooks/useAnalytics";
import {
  Users,
  BarChart3,
  Shield,
  Settings,
  Globe,
  Activity,
  Lock,
  Clock,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DashboardStats {
  total_users: number;
  active_users: number;
  total_events: number;
  unique_visitors: number;
  whitelist_count: number;
  blacklist_count: number;
  blocked_attempts: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAuthStore();
  const { trackClick } = useAnalytics();

  useEffect(() => {
    loadDashboardStats();
  }, []);

  async function loadDashboardStats() {
    setIsLoading(true);
    const token = localStorage.getItem("auth_token");
    try {
      const [usersRes, analyticsRes, ipRes] = await Promise.all([
        fetch(`${API_BASE}/api/users`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/analytics/stats?days=7`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/admin/ip/stats?days=7`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      const users = usersRes.ok ? await usersRes.json() : [];
      const analytics = analyticsRes.ok ? await analyticsRes.json() : [];
      const ip = ipRes.ok ? await ipRes.json() : {};

      const totalEvents = analytics.reduce(
        (sum: number, a: { total_count: number }) => sum + a.total_count,
        0
      );
      const uniqueVisitors = analytics.reduce(
        (sum: number, a: { unique_users: number }) => sum + a.unique_users,
        0
      );

      setStats({
        total_users: users.length,
        active_users: users.filter(
          (u: { is_active: boolean }) => u.is_active
        ).length,
        total_events: totalEvents,
        unique_visitors: uniqueVisitors,
        whitelist_count: ip.whitelist_count || 0,
        blacklist_count: ip.blacklist_count || 0,
        blocked_attempts: ip.blocked_attempts || 0,
      });
    } catch (err) {
      console.error("載入統計失敗:", err);
    } finally {
      setIsLoading(false);
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

  const quickLinks = [
    {
      title: "用戶管理",
      description: "管理用戶帳號、權限設定",
      href: "/admin/users",
      icon: Users,
      color: "bg-blue-500",
    },
    {
      title: "行為報表",
      description: "查看使用者行為追蹤統計",
      href: "/admin/analytics",
      icon: BarChart3,
      color: "bg-green-500",
    },
    {
      title: "IP 管理",
      description: "設定 IP 白名單與黑名單",
      href: "/admin/ip",
      icon: Globe,
      color: "bg-purple-500",
    },
    {
      title: "系統設定",
      description: "JWT、Session、安全設定",
      href: "/admin/settings",
      icon: Settings,
      color: "bg-amber-500",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50/50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">管理後台</h1>
          <p className="text-slate-500 mt-2">歡迎回來，{user.username}</p>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-slate-500">載入中...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <Card className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Users className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-slate-900">
                      {stats?.total_users || 0}
                    </div>
                    <div className="text-sm text-slate-500">總用戶數</div>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-green-100 rounded-lg">
                    <Activity className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-slate-900">
                      {stats?.total_events || 0}
                    </div>
                    <div className="text-sm text-slate-500">本週事件數</div>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Shield className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-slate-900">
                      {stats?.whitelist_count || 0}
                    </div>
                    <div className="text-sm text-slate-500">IP 白名單</div>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-red-100 rounded-lg">
                    <Lock className="w-6 h-6 text-red-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-slate-900">
                      {stats?.blocked_attempts || 0}
                    </div>
                    <div className="text-sm text-slate-500">封鎖次數</div>
                  </div>
                </div>
              </Card>
            </div>

            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              快速操作
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {quickLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => trackClick(`admin_quick_link_${link.title}`)}
                  className="block"
                >
                  <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer h-full">
                    <div className="flex items-start gap-4">
                      <div className={`p-3 ${link.color} rounded-lg`}>
                        <link.icon className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-900">
                          {link.title}
                        </h3>
                        <p className="text-sm text-slate-500 mt-1">
                          {link.description}
                        </p>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>

            <div className="mt-8">
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">
                  系統資訊
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-slate-500">認證方式：</span>
                    <span className="ml-2 font-medium">JWT Token</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Token 有效期：</span>
                    <span className="ml-2 font-medium">24 小時</span>
                  </div>
                  <div>
                    <span className="text-slate-500">資料庫：</span>
                    <span className="ml-2 font-medium">SQLite</span>
                  </div>
                  <div>
                    <span className="text-slate-500">SSO 支援：</span>
                    <span className="ml-2 font-medium text-amber-600">
                      未啟用
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">IP 管制：</span>
                    <span className="ml-2 font-medium text-amber-600">
                      未啟用
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">最後更新：</span>
                    <span className="ml-2 font-medium">
                      {new Date().toLocaleDateString("zh-TW")}
                    </span>
                  </div>
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
