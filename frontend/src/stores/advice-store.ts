import { create } from "zustand";

// 相關性分析的 AI 變數選擇建議 → 建模分頁顯示
interface AdviceState {
    regressionAdvice: string | null;
    setRegressionAdvice: (advice: string | null) => void;
}

export const useAdviceStore = create<AdviceState>((set) => ({
    regressionAdvice: null,
    setRegressionAdvice: (regressionAdvice) => set({ regressionAdvice }),
}));
