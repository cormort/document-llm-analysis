"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Lightbulb, FileText, Activity, Loader2, CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";


interface Document {
  file_name: string;
  indexed_at: string;
  chunk_count: number;
}

export function RightPanel() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const { selectedDocuments, toggleDocumentSelection } = useAppStore();

  useEffect(() => {
    async function fetchDocuments() {
      try {
        const response = await fetch("/api/rag/documents");
        if (response.ok) {
          const data = await response.json();
          // Assuming the API returns a list of strings or objects. ADJUST based on actual API response.
          // If API returns strings: data.map((name, i) => ({ id: i, filename: name }))
          // If API returns { documents: [...] }: data.documents
          
          // Based on previous knowledge of rag.py, likely returns list of objects or strings.
          // Let's assume list of objects with 'filename' or similar for safety, or handle both.
          
          if (Array.isArray(data)) {
             setDocuments(data);
          }
        }
      } catch (error) {
        console.error("Failed to fetch documents", error);
      } finally {
        setLoading(false);
      }
    }
    fetchDocuments();
  }, []);
  return (
    <div className="flex flex-col h-full bg-slate-50 border-l border-slate-200 overflow-hidden">
      <div className="p-3 font-medium text-sm text-slate-500 uppercase tracking-wider border-b border-slate-200">
        Context & Analysis
      </div>
      
      <ScrollArea className="flex-1">
        <div className="space-y-4 p-4 pr-6 pb-8">
          <Card className="p-4 bg-white/50 border-slate-200">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
              <Lightbulb size={16} className="text-amber-500" />
              Active Context
            </h3>
            <p className="text-xs text-slate-500">
              {selectedDocuments.length === 0 
                ? "No active documents selected. Click files below to select." 
                : `${selectedDocuments.length} document(s) selected.`
              }
            </p>
            {selectedDocuments.length > 0 && (
               <div className="mt-2 space-y-1">
                 {selectedDocuments.map(doc => (
                    <div key={doc} className="text-[10px] bg-indigo-50 text-indigo-700 px-2 py-1 rounded truncate">
                       {doc}
                    </div>
                 ))}
               </div>
            )}
          </Card>

          <Card className="p-4 bg-white/50 border-slate-200">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
              <FileText size={16} className="text-blue-500" />
              Recent Files
            </h3>
            <div className="text-xs text-slate-500 space-y-2 max-h-[150px] overflow-y-auto">
               {loading ? (
                  <div className="flex items-center gap-2"><Loader2 className="animate-spin w-3 h-3"/> Loading...</div>
               ) : documents.length === 0 ? (
                  <div className="italic text-slate-400">No recent files found.</div>
               ) : (
                  documents.map((doc, index) => {
                    const isSelected = selectedDocuments.includes(doc.file_name);
                    return (
                      <div 
                        key={index} 
                        className={`flex items-center gap-2 truncate cursor-pointer p-1.5 rounded transition-colors ${isSelected ? 'bg-indigo-50 text-indigo-700 font-medium' : 'hover:bg-slate-100'}`}
                        onClick={() => toggleDocumentSelection(doc.file_name)}
                      >
                         {isSelected ? (
                            <CheckCircle2 size={12} className="shrink-0 text-indigo-600" />
                         ) : (
                            <FileText size={12} className="shrink-0 text-slate-400" />
                         )}
                         <span title={doc.file_name}>{doc.file_name}</span>
                      </div>
                    );
                  })
               )}
            </div>
          </Card>
          
           <Card className="p-4 bg-white/50 border-slate-200">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
              <Activity size={16} className="text-green-500" />
              System Status
            </h3>
            <div className="flex flex-col gap-2 mt-2">
                <div className="bg-green-100 text-green-700 text-[10px] px-2 py-1.5 rounded text-center w-full">Backend: Online</div>
                <div className="bg-blue-100 text-blue-700 text-[10px] px-2 py-1.5 rounded text-center w-full">RAG: Ready</div>
            </div>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
}
