"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth-store";
import { Users, Clock, AlertCircle, CheckCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface QueueStatus {
  queue_length: number;
  active_count: number;
  your_position: number | null;
  is_available: boolean;
}

interface LLMQueueStatusProps {
  onStatusChange?: (isAvailable: boolean) => void;
}

export function LLMQueueStatus({ onStatusChange }: LLMQueueStatusProps) {
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchStatus = async () => {
      const token = localStorage.getItem("auth_token");
      if (!token) return;

      try {
        const res = await fetch(`${API_BASE}/api/llm/queue/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          const data = await res.json();
          setStatus(data);
          onStatusChange?.(data.is_available);
        }
      } catch (err) {
        console.error("無法取得佇列狀態:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);

    return () => clearInterval(interval);
  }, [isAuthenticated, onStatusChange]);

  if (!isAuthenticated || isLoading) {
    return null;
  }

  if (!status) {
    return null;
  }

  const isWaiting = status.your_position !== null && status.your_position > 0;

  return (
    <Card className="p-4 mb-4">
      {status.is_available ? (
        <div className="flex items-center gap-3 text-green-600">
          <CheckCircle className="w-5 h-5" />
          <div>
            <div className="font-medium">LLM 可使用</div>
            <div className="text-sm text-slate-500">
              目前沒有人在等待，可以直接使用
            </div>
          </div>
        </div>
      ) : isWaiting ? (
        <div className="flex items-center gap-3 text-amber-600">
          <Clock className="w-5 h-5 animate-pulse" />
          <div>
            <div className="font-medium">
              正在排隊中... (第 {status.your_position} 位)
            </div>
            <div className="text-sm text-slate-500">
              前方還有 {status.queue_length} 個請求等待中
            </div>
          </div>
        </div>
      ) : status.active_count > 0 ? (
        <div className="flex items-center gap-3 text-blue-600">
          <Users className="w-5 h-5" />
          <div>
            <div className="font-medium">LLM 使用中</div>
            <div className="text-sm text-slate-500">
              目前有 {status.active_count} 個請求正在處理
              {status.queue_length > 0 && `，${status.queue_length} 個等待中`}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 text-slate-500">
          <AlertCircle className="w-5 h-5" />
          <div>
            <div className="font-medium">檢查狀態中...</div>
          </div>
        </div>
      )}
    </Card>
  );
}

export function LLMQueueBanner() {
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchStatus = async () => {
      const token = localStorage.getItem("auth_token");
      if (!token) return;

      try {
        const res = await fetch(`${API_BASE}/api/llm/queue/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          setStatus(await res.json());
        }
      } catch (err) {
        console.error("無法取得佇列狀態:", err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  if (!isAuthenticated || !status || status.is_available) {
    return null;
  }

  const isWaiting = status.your_position !== null && status.your_position > 0;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <Card className={`p-4 shadow-lg ${isWaiting ? "border-amber-500" : "border-blue-500"}`}>
        <div className="flex items-center gap-3">
          {isWaiting ? (
            <>
              <Clock className="w-5 h-5 text-amber-600 animate-pulse" />
              <div>
                <div className="font-medium text-amber-600">
                  排隊中：第 {status.your_position} 位
                </div>
                <div className="text-xs text-slate-500">
                  預計等待 {status.your_position * 30} 秒
                </div>
              </div>
            </>
          ) : (
            <>
              <Users className="w-5 h-5 text-blue-600" />
              <div>
                <div className="font-medium text-blue-600">LLM 使用中</div>
                <div className="text-xs text-slate-500">
                  {status.queue_length} 人等待中
                </div>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}
