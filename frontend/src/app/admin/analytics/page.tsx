"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth-store";
import { useAnalytics } from "@/hooks/useAnalytics";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface EventStats {
  event_name: string;
  total_count: number;
  unique_users: number;
}

interface EventDetail {
  id: number;
  user_id: number | null;
  event_type: string;
  event_name: string;
  event_data: Record<string, unknown> | null;
  page_url: string | null;
  ip_address: string | null;
  session_id: string | null;
  created_at: string;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<EventStats[]>([]);
  const [events, setEvents] = useState<EventDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [days, setDays] = useState(7);
  const { user: currentUser } = useAuthStore();
  const { trackClick } = useAnalytics();

  useEffect(() => {
    loadData();
  }, [days]);

  async function loadData() {
    setIsLoading(true);
    const token = localStorage.getItem("auth_token");
    try {
      const [statsRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/api/analytics/stats?days=${days}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/analytics/events?days=${days}&limit=100`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
      if (eventsRes.ok) {
        setEvents(await eventsRes.json());
      }
    } catch (err) {
      console.error("載入資料失敗:", err);
    } finally {
      setIsLoading(false);
    }
  }

  if (!currentUser?.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50/50">
        <Card className="p-8">
          <h1 className="text-xl font-bold text-red-600">權限不足</h1>
          <p className="text-slate-500 mt-2">您需要管理員權限才能訪問此頁面</p>
        </Card>
      </div>
    );
  }

  const totalCount = stats.reduce((sum, s) => sum + s.total_count, 0);

  return (
    <div className="min-h-screen bg-slate-50/50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">行為追蹤報表</h1>
            <p className="text-slate-500 mt-1">查看使用者按鈕點擊統計</p>
          </div>
          <select
            value={days}
            onChange={(e) => {
              const newDays = parseInt(e.target.value);
              trackClick("analytics_days_filter", { days: newDays });
              setDays(newDays);
            }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value={1}>最近 1 天</option>
            <option value={7}>最近 7 天</option>
            <option value={30}>最近 30 天</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-slate-500">載入中...</div>
        ) : (
          <div className="grid gap-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                總覽 - 最近 {days} 天
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">{totalCount}</div>
                  <div className="text-sm text-slate-600">總事件數</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">{stats.length}</div>
                  <div className="text-sm text-slate-600">事件類型數</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-purple-600">
                    {stats.reduce((sum, s) => sum + s.unique_users, 0)}
                  </div>
                  <div className="text-sm text-slate-600">活躍用戶數</div>
                </div>
                <div className="bg-amber-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-amber-600">
                    {events.filter((e) => e.event_type === "click").length}
                  </div>
                  <div className="text-sm text-slate-600">點擊事件</div>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                事件統計
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">
                        事件名稱
                      </th>
                      <th className="px-4 py-2 text-right text-sm font-medium text-slate-700">
                        總次數
                      </th>
                      <th className="px-4 py-2 text-right text-sm font-medium text-slate-700">
                        活躍用戶數
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {stats.map((stat) => (
                      <tr key={stat.event_name} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-slate-900">{stat.event_name}</td>
                        <td className="px-4 py-3 text-right text-slate-600">
                          {stat.total_count}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-600">
                          {stat.unique_users}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card className="p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                最近事件記錄
              </h2>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full">
                  <thead className="bg-slate-100 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">
                        時間
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">
                        用戶ID
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">
                        事件
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">
                        頁面
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {events.map((event) => (
                      <tr key={event.id} className="hover:bg-slate-50">
                        <td className="px-4 py-2 text-slate-500 text-sm">
                          {new Date(event.created_at).toLocaleString("zh-TW")}
                        </td>
                        <td className="px-4 py-2 text-slate-600">
                          {event.user_id || "匿名"}
                        </td>
                        <td className="px-4 py-2">
                          <span className="inline-flex px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-700">
                            {event.event_name}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-slate-500 text-sm truncate max-w-xs">
                          {event.page_url?.split("?")[0] || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
