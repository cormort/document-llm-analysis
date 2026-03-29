import { useAnalyticsStore } from "@/stores/analytics-store";

export function useAnalytics() {
  const trackClick = useAnalyticsStore((state) => state.trackClick);

  const trackButtonClick = (buttonName: string, additionalData?: Record<string, unknown>) => {
    trackClick(buttonName, {
      ...additionalData,
      path: typeof window !== "undefined" ? window.location.pathname : undefined,
    });
  };

  return { trackClick: trackButtonClick };
}
