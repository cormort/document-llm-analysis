"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { useAnalytics } from "@/hooks/useAnalytics";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export default function UsersManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const { user: currentUser } = useAuthStore();
  const { trackClick } = useAnalytics();

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setIsLoading(true);
    const token = localStorage.getItem("auth_token");
    try {
      const res = await fetch(`${API_BASE}/api/users`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        throw new Error("載入用戶失敗");
      }
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "載入用戶失敗";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  async function toggleUserStatus(userId: number, isActive: boolean) {
    trackClick("toggle_user_status", { userId, isActive });
    const token = localStorage.getItem("auth_token");
    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !isActive }),
      });
      if (!res.ok) {
        throw new Error("更新失敗");
      }
      loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "更新失敗");
    }
  }

  async function toggleAdmin(userId: number, is_admin: boolean) {
    trackClick("toggle_admin", { userId, is_admin });
    const token = localStorage.getItem("auth_token");
    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_admin: !is_admin }),
      });
      if (!res.ok) {
        throw new Error("更新失敗");
      }
      loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "更新失敗");
    }
  }

  async function deleteUser(userId: number, username: string) {
    trackClick("delete_user", { userId });
    if (!confirm(`確定要刪除用戶 ${username} 嗎？`)) return;

    const token = localStorage.getItem("auth_token");
    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        throw new Error("刪除失敗");
      }
      loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "刪除失敗");
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

  return (
    <div className="min-h-screen bg-slate-50/50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">用戶管理</h1>
          <p className="text-slate-500 mt-1">管理系統用戶帳號</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg mb-4">
            {error}
          </div>
        )}

        <Card className="overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500">載入中...</div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">
                    用戶名
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">
                    狀態
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">
                    權限
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">
                    註冊時間
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-700">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-900">{user.username}</td>
                    <td className="px-4 py-3 text-slate-600">{user.email}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          user.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {user.is_active ? "啟用" : "停用"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          user.is_admin
                            ? "bg-purple-100 text-purple-700"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {user.is_admin ? "管理員" : "一般用戶"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-sm">
                      {new Date(user.created_at).toLocaleDateString("zh-TW")}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => toggleUserStatus(user.id, user.is_active)}
                      >
                        {user.is_active ? "停用" : "啟用"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => toggleAdmin(user.id, user.is_admin)}
                      >
                        {user.is_admin ? "取消管理員" : "設為管理員"}
                      </Button>
                      {user.id !== currentUser.id && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => deleteUser(user.id, user.username)}
                        >
                          刪除
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
