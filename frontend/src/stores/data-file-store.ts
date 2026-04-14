import { create } from "zustand";
import { DataFileInfo, listDataFiles } from "@/lib/api";

interface DataFileState {
    files: DataFileInfo[];
    loading: boolean;
    error: string | null;
    fetchFiles: () => Promise<void>;
}

export const useDataFileStore = create<DataFileState>((set) => ({
    files: [],
    loading: false,
    error: null,

    fetchFiles: async () => {
        set({ loading: true, error: null });
        try {
            const files = await listDataFiles();
            set({ files, loading: false });
        } catch (err) {
            set({
                error: err instanceof Error ? err.message : "載入失敗",
                loading: false,
            });
        }
    },
}));
