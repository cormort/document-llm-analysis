"use client";

import { useRef, useState, FormEvent } from "react";
import { 
    Send, 
    Bot, 
    Loader2, 
    AlertTriangle,
    Search,
    MessageSquare,
    Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore, ChatMessage } from "@/stores/chat-store";
import { useSettingsStore } from "@/stores/settings-store";
import { queryAgentStream } from "@/lib/api";
import { MarkdownRenderer } from "./markdown-renderer";

interface ChatInterfaceProps {
    selectedDocuments: string[];
}

function MessageBubble({ message }: { message: ChatMessage }) {
    const isUser = message.role === "user";

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6 group`}>
            {!isUser && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white mr-3 shadow-lg flex-shrink-0 mt-1">
                    <Bot size={16} />
                </div>
            )}
            
            <div
                className={`max-w-[80%] rounded-2xl px-5 py-3.5 shadow-sm transition-all duration-200 ${isUser
                    ? "bg-blue-600/90 text-white shadow-blue-500/20"
                    : "bg-white text-slate-900 border border-slate-100 shadow-slate-200/50"
                    }`}
            >
                {isUser ? (
                    <div className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</div>
                ) : (
                    <MarkdownRenderer content={message.content} />
                )}
                <div
                    className={`text-[10px] mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 ${isUser ? "text-blue-100 justify-end" : "text-slate-400"
                        }`}
                >
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
            </div>
        </div>
    );
}

function StreamingIndicator() {
    return (
        <div className="flex justify-start mb-6">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white mr-3 shadow-lg flex-shrink-0 mt-1 animate-pulse">
                <Sparkles size={16} />
            </div>
            <div className="bg-white rounded-2xl px-5 py-3.5 border border-slate-100 shadow-md flex items-center gap-3">
                <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                <span className="text-sm text-slate-500 font-medium bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                    AI 正在思考中...
                </span>
            </div>
        </div>
    );
}

export function ChatInterface({ selectedDocuments }: ChatInterfaceProps) {
    const [input, setInput] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);
    const {
        messages,
        isStreaming,
        addMessage,
        updateLastMessage,
        setStreaming,
    } = useChatStore();
    const { provider, model_name, local_url, api_key } = useSettingsStore();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isStreaming || selectedDocuments.length === 0) return;

        const question = input.trim();
        setInput("");

        // Add user message
        addMessage({ role: "user", content: question });

        // Start streaming
        setStreaming(true);
        addMessage({ role: "assistant", content: "" });

        try {
            // Switch to Agent Stream
            const stream = queryAgentStream({
                message: question,
                llm_config: {
                    provider, 
                    model_name,
                    local_url,
                    api_key
                }
            });

            let fullContent = "";
            for await (const chunk of stream) {
                fullContent += chunk;
                updateLastMessage(fullContent);
            }
        } catch (error) {
            updateLastMessage(`❌ 發生錯誤: ${error instanceof Error ? error.message : "Unknown error"}`);
        } finally {
            setStreaming(false);
        }
    };

    return (
        <Card className="flex flex-col h-full border-0 shadow-none bg-transparent overflow-hidden rounded-none">
            {/* Messages Area */}
            <ScrollArea className="flex-1 p-6" ref={scrollRef}>
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-8">
                        <div className="w-20 h-20 bg-blue-50 rounded-2xl flex items-center justify-center mb-6 group transition-transform hover:scale-105">
                            <Search className="w-10 h-10 text-blue-500/80" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800">開始智能問答</h3>
                        <p className="text-sm text-slate-500 mt-2 max-w-sm leading-relaxed">
                            已選擇 <span className="font-semibold text-blue-600">{selectedDocuments.length}</span> 份文件。
                            <br/>
                            請在下方輸入問題，AI 將為您分析內容。
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2 pb-4">
                        {messages.map((message) => (
                            <MessageBubble key={message.id} message={message} />
                        ))}
                        {isStreaming && messages[messages.length - 1]?.content === "" && (
                            <StreamingIndicator />
                        )}
                    </div>
                )}
            </ScrollArea>

            {/* Input Area */}
            <div className="border-t border-slate-100 p-4 bg-white/80 backdrop-blur-md">
                <form onSubmit={handleSubmit} className="flex gap-3 relative">
                    <div className="flex-1 relative">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={
                                selectedDocuments.length === 0
                                    ? "請先在左側選擇文件..."
                                    : "詢問關於文件的任何問題..."
                            }
                            disabled={isStreaming || selectedDocuments.length === 0}
                            className={`pr-10 h-12 rounded-xl border-slate-200 bg-white shadow-sm transition-all focus:ring-2 focus:ring-blue-100 focus:border-blue-300 text-[15px] ${
                                selectedDocuments.length === 0 ? "opacity-60 cursor-not-allowed bg-slate-50" : ""
                            }`}
                        />
                        <div className="absolute right-3 top-3 text-slate-400">
                             <MessageSquare size={18} className="opacity-50" />
                        </div>
                    </div>
                    
                    <Button
                        type="submit"
                        disabled={isStreaming || !input.trim() || selectedDocuments.length === 0}
                        className={`h-12 w-12 rounded-xl p-0 transition-all duration-300 shadow-md ${
                            !input.trim() || isStreaming
                                ? "bg-slate-100 text-slate-400 shadow-none" 
                                : "bg-gradient-to-r from-blue-600 to-purple-600 hover:shadow-lg hover:scale-105 active:scale-95"
                        }`}
                    >
                        {isStreaming ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Send className="w-5 h-5 ml-0.5" />
                        )}
                    </Button>
                </form>
                
                {selectedDocuments.length === 0 && (
                    <div className="flex items-center justify-center gap-2 mt-3 text-xs text-amber-600 animate-in fade-in slide-in-from-bottom-2">
                        <AlertTriangle size={14} />
                        <span className="font-medium">請先選擇至少一個文件以開始對話</span>
                    </div>
                )}
            </div>
        </Card>
    );
}
