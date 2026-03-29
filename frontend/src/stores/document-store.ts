/**
 * Global Document Store using Zustand.
 *
 * This store manages all uploaded documents across the application,
 * eliminating the need for individual pages to manage their own document state.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { DocumentInfo, listDocuments } from "@/lib/api";

interface DocumentState {
    documents: DocumentInfo[];
    selectedDocId: string | null;
    loading: boolean;
    error: string | null;

    // Actions
    fetchDocuments: () => Promise<void>;
    selectDocument: (id: string | null) => void;
    getSelectedDocument: () => DocumentInfo | null;
    getTabularDocuments: () => DocumentInfo[];
}

export const useDocumentStore = create<DocumentState>()(
    persist(
        (set, get) => ({
            documents: [],
            selectedDocId: null,
            loading: false,
            error: null,

            fetchDocuments: async () => {
                set({ loading: true, error: null });
                try {
                    const docs = await listDocuments();
                    set({ documents: docs, loading: false });
                } catch (err) {
                    set({
                        error: err instanceof Error ? err.message : "Failed to load documents",
                        loading: false,
                    });
                }
            },

            selectDocument: (id) => set({ selectedDocId: id }),

            getSelectedDocument: () => {
                const { documents, selectedDocId } = get();
                return documents.find((d) => d.collection_name === selectedDocId) || null;
            },

            getTabularDocuments: () => {
                const { documents } = get();
                return documents.filter((d) =>
                    d.file_name.match(/\.(csv|xlsx|xls|json)$/i)
                );
            },
        }),
        {
            name: "document-store",
            partialize: (state) => ({ selectedDocId: state.selectedDocId }),
        }
    )
);
