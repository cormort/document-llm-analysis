"use client";

import { useState } from "react";
import { ChatInterface } from "@/components/chat/chat-interface";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText } from "lucide-react";
import { useAppStore } from "@/lib/store";

type Tab = 'chat' | 'artifacts';

export function TabbedPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const { selectedDocuments } = useAppStore();
  
  return (
    <div className="h-full flex flex-col bg-white">
      {/* Tab Navigation */}
      <div className="h-10 border-b border-slate-200 flex items-center px-4 gap-4 bg-slate-50/50 shrink-0">
        <button 
          onClick={() => setActiveTab('chat')}
          className={`text-sm font-medium h-full flex items-center px-2 border-b-2 transition-colors ${
            activeTab === 'chat' 
              ? "text-blue-600 border-blue-600" 
              : "text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300"
          }`}
        >
          Chat
        </button>
        <button 
          onClick={() => setActiveTab('artifacts')}
          className={`text-sm font-medium h-full flex items-center px-2 border-b-2 transition-colors ${
            activeTab === 'artifacts' 
              ? "text-blue-600 border-blue-600" 
              : "text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300"
          }`}
        >
          Artifacts
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'chat' ? (
           <ChatInterface 
             selectedDocuments={selectedDocuments} 
             useHybrid={true}
             mode="rag"
           />
        ) : (
          <div className="h-full w-full">
            <ScrollArea className="h-full">
               <div className="flex flex-col items-center justify-center p-12 text-center text-slate-500">
                  <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
                     <FileText className="w-8 h-8 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-medium text-slate-900">No Artifacts Yet</h3>
                  <p className="max-w-xs mt-2 text-sm">
                    Generated files, reports, and diagrams will appear here during your analysis session.
                  </p>
               </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  );
}
