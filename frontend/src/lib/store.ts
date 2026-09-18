import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Thread {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
}

interface AppState {
  threads: Thread[];
  currentThreadId: string | null;
  /** Collection names selected for RAG / report generation. */
  selectedDocuments: string[];

  createThread: () => string;
  selectThread: (id: string) => void;
  deleteThread: (id: string) => void;
  renameThread: (id: string, title: string) => void;
  getCurrentThread: () => Thread | null;

  toggleDocumentSelection: (collectionName: string) => void;
  setSelectedDocuments: (collectionNames: string[]) => void;
  clearSelectedDocuments: () => void;
}

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `t_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * 全域 UI 狀態（側邊欄對話串 + 已選文件）。
 *
 * 這個檔案原本不在版控中（被 .gitignore 的 `lib/` 規則排除），
 * 由 `@/lib/store` 的重建契約還原。
 */
export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      threads: [],
      currentThreadId: null,
      selectedDocuments: [],

      createThread: () => {
        const id = newId();
        const now = Date.now();
        const thread: Thread = {
          id,
          title: "New Conversation",
          createdAt: now,
          updatedAt: now,
        };
        set((state) => ({
          threads: [thread, ...state.threads],
          currentThreadId: id,
        }));
        return id;
      },

      selectThread: (id) => set({ currentThreadId: id }),

      deleteThread: (id) =>
        set((state) => {
          const threads = state.threads.filter((t) => t.id !== id);
          const currentThreadId =
            state.currentThreadId === id
              ? (threads[0]?.id ?? null)
              : state.currentThreadId;
          return { threads, currentThreadId };
        }),

      renameThread: (id, title) =>
        set((state) => ({
          threads: state.threads.map((t) =>
            t.id === id ? { ...t, title, updatedAt: Date.now() } : t
          ),
        })),

      getCurrentThread: () => {
        const { threads, currentThreadId } = get();
        return threads.find((t) => t.id === currentThreadId) ?? null;
      },

      toggleDocumentSelection: (collectionName) =>
        set((state) => ({
          selectedDocuments: state.selectedDocuments.includes(collectionName)
            ? state.selectedDocuments.filter((c) => c !== collectionName)
            : [...state.selectedDocuments, collectionName],
        })),

      setSelectedDocuments: (collectionNames) =>
        set({ selectedDocuments: collectionNames }),

      clearSelectedDocuments: () => set({ selectedDocuments: [] }),
    }),
    {
      name: "app-store",
      // 只持久化資料，不持久化 action
      partialize: (state) => ({
        threads: state.threads,
        currentThreadId: state.currentThreadId,
        selectedDocuments: state.selectedDocuments,
      }),
    }
  )
);
