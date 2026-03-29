"use client";

import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, MessageSquare, Trash2 } from "lucide-react";

export function ThreadSidebar() {
  const { threads, currentThreadId, createThread, selectThread, deleteThread } = useAppStore();

  return (
    <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200">
      <div className="p-4 border-b border-slate-200">
        <Button 
          onClick={() => createThread()} 
          className="w-full justify-start gap-2 bg-blue-600 hover:bg-blue-700 text-white"
        >
          <Plus size={16} />
          New Chat
        </Button>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1">
          {threads.map((thread) => (
            <div 
              key={thread.id}
              className={`group flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer ${
                thread.id === currentThreadId 
                  ? "bg-white shadow-sm font-medium text-slate-900 border border-slate-200" 
                  : "text-slate-600 hover:bg-slate-200/50"
              }`}
              onClick={() => selectThread(thread.id)}
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <MessageSquare size={14} className={thread.id === currentThreadId ? "text-blue-500" : "text-slate-400"} />
                <span className="truncate">{thread.title || "New Conversation"}</span>
              </div>
              
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  deleteThread(thread.id);
                }}
                className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity p-1"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
