import { create } from "zustand";

export interface SliceFilter {
    column: string;
    values: (string | number | boolean)[];
}

interface SliceState {
    filters: SliceFilter[];
    setFilters: (filters: SliceFilter[]) => void;
    clearFilters: () => void;
}

// Global data slicing: filters here are auto-attached to all stats/modeling API requests (see lib/api.ts)
export const useSliceStore = create<SliceState>((set) => ({
    filters: [],
    setFilters: (filters) => set({ filters }),
    clearFilters: () => set({ filters: [] }),
}));
