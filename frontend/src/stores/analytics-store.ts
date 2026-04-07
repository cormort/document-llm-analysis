import { create } from "zustand";

export interface AnalyticsEvent {
  id: number;
  event_type: string;
  event_name: string;
  event_data: Record<string, unknown> | null;
  page_url: string | null;
  created_at: string;
}

interface AnalyticsState {
  sessionId: string;
  pendingEvents: Array<{
    event_type: string;
    event_name: string;
    event_data?: Record<string, unknown>;
    page_url?: string;
    session_id: string;
    timestamp: number;
  }>;
  trackClick: (buttonName: string, additionalData?: Record<string, unknown>) => void;
  flushEvents: () => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  sessionId: typeof window !== "undefined" ? generateSessionId() : "",
  pendingEvents: [],

  trackClick: (buttonName, additionalData = {}) => {
    const event = {
      event_type: "click",
      event_name: buttonName,
      event_data: additionalData,
      page_url: typeof window !== "undefined" ? window.location.href : undefined,
      session_id: get().sessionId,
      timestamp: Date.now(),
    };

    set((state) => ({
      pendingEvents: [...state.pendingEvents, event],
    }));

    get().flushEvents();
  },

  flushEvents: async () => {
    const { pendingEvents } = get();
    if (pendingEvents.length === 0) return;

    const eventsToSend = [...pendingEvents];
    set({ pendingEvents: [] });

    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    for (const event of eventsToSend) {
      try {
        await fetch(`${API_BASE}/api/analytics/track`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            event_type: event.event_type,
            event_name: event.event_name,
            event_data: event.event_data,
            page_url: event.page_url,
            session_id: event.session_id,
          }),
        });
      } catch (error) {
        console.error("Analytics tracking error:", error);
      }
    }
  },
}));
