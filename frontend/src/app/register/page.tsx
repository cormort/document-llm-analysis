"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { register as apiRegister } from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAnalytics } from "@/hooks/useAnalytics";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);
  const { trackClick } = useAnalytics();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("密碼不一致");
      return;
    }

    if (password.length < 6) {
      setError("密碼長度至少 6 個字元");
      return;
    }

    setIsLoading(true);
    trackClick("register_submit");

    try {
      const { user, access_token } = await apiRegister(username, email, password);
      setToken(access_token);
      setUser(user);
      trackClick("register_success");
      router.push("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "註冊失敗";
      setError(message);
      trackClick("register_error", { error: message });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50/50 px-4">
      <Card className="w-full max-w-md p-8 shadow-xl border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900 mb-2 text-center">註冊</h1>
        <p className="text-slate-500 text-sm text-center mb-6">
          建立帳號以使用文件分析系統
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              用戶名
            </label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="輸入用戶名"
              required
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="輸入 Email"
              required
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              密碼
            </label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="輸入密碼"
              required
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              確認密碼
            </label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="再次輸入密碼"
              required
              disabled={isLoading}
            />
          </div>

          <Button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700"
            disabled={isLoading}
          >
            {isLoading ? "註冊中..." : "註冊"}
          </Button>

          <p className="text-center text-sm text-slate-500">
            已有帳號？{" "}
            <a
              href="/login"
              className="text-blue-600 hover:underline"
              onClick={() => trackClick("go_to_login")}
            >
              登入
            </a>
          </p>
        </form>
      </Card>
    </div>
  );
}
