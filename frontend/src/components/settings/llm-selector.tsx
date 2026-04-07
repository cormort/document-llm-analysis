"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSettingsStore } from "@/stores/settings-store";
import { listModels } from "@/lib/api";
import { 
    Settings, 
    Bot, 
    RefreshCw, 
    ChevronDown, 
    ChevronUp,
    Server,
    Key
} from "lucide-react";

const PROVIDERS = [
  "Local (LM Studio)",
  "Ollama",
  "Gemini",
  "OpenAI",
  "omlx",
];

interface LLMSelectorProps {
    collapsed: boolean;
}

export function LLMSelector({ collapsed }: LLMSelectorProps) {
    const store = useSettingsStore();
    const [isOpen, setIsOpen] = useState(false);
    
    // Local state for fetched models
    const [mainModels, setMainModels] = useState<string[]>([]);
    const [fastModels, setFastModels] = useState<string[]>([]);
    
    const [loadingMain, setLoadingMain] = useState(false);
    const [loadingFast, setLoadingFast] = useState(false);

    // Generic fetcher
    const fetchModelsForTier = useCallback(async (
        tier: "main" | "fast", 
        provider: string, 
        url: string, 
        key: string,
        silent = false
    ) => {
        if (!provider) return;
        
        // Prevent sending cloud API keys (like Gemini) to local providers
        const effectiveKey = (provider.includes("Local") || provider === "Ollama" || provider === "omlx") ? "" : key;

        if (!silent) {
            if (tier === "main") setLoadingMain(true);
            else setLoadingFast(true);
        }

        try {
            const models = await listModels(provider, url, effectiveKey || undefined);
            if (models && models.length > 0) {
                if (tier === "main") setMainModels(models);
                else setFastModels(models);
                
                // Auto-select defaults
                if (tier === "main") {
                    if (!store.model_name || !models.includes(store.model_name)) store.setModel(models[0]);
                } else {
                    if (!store.fastModel || !models.includes(store.fastModel)) store.setFastModel(models[0]);
                }
            } else {
                if (tier === "main") setMainModels([]);
                else setFastModels([]);
            }
        } catch (error) {
            console.error(error);
            if (!silent) alert(`獲取 ${tier === "main" ? "主" : "快速"}模型失敗`);
        } finally {
            if (!silent) {
                if (tier === "main") setLoadingMain(false);
                else setLoadingFast(false);
            }
        }
    }, [store]);

    // Auto-detect Main
    useEffect(() => {
        const timer = setTimeout(() => {
if (store.provider?.includes("Local") || store.provider === "Ollama" || store.provider === "omlx") {
    fetchModelsForTier("main", store.provider, store.local_url || "", store.api_key || "", true);
  }
        }, 800);
        return () => clearTimeout(timer);
    }, [store.provider, store.local_url, store.api_key, fetchModelsForTier]);

    // Auto-detect Fast
    useEffect(() => {
        const timer = setTimeout(() => {
if (store.fastProvider?.includes("Local") || store.fastProvider === "Ollama" || store.fastProvider === "omlx") {
    fetchModelsForTier("fast", store.fastProvider, store.fastUrl || "", store.api_key || "", true);
  }
        }, 800);
        return () => clearTimeout(timer);
    }, [store.fastProvider, store.fastUrl, store.api_key, fetchModelsForTier]);

    // Initial load
    useEffect(() => {
        fetchModelsForTier("main", store.provider || "", store.local_url || "", store.api_key || "", true);
        fetchModelsForTier("fast", store.fastProvider || "", store.fastUrl || "", store.api_key || "", true);
    }, [fetchModelsForTier, store.provider, store.local_url, store.api_key, store.fastProvider, store.fastUrl]);

    const renderConfig = (type: "main" | "fast") => {
        const isMain = type === "main";
        const provider = isMain ? store.provider : store.fastProvider;
        const model = isMain ? store.model_name : store.fastModel;
        const url = isMain ? store.local_url : store.fastUrl;
        const setProvider = isMain ? store.setProvider : store.setFastProvider;
        const setModel = isMain ? store.setModel : store.setFastModel;
        const setUrl = isMain ? store.setLocalUrl : store.setFastUrl;
        const currentModels = isMain ? mainModels : fastModels;
        const isLoading = isMain ? loadingMain : loadingFast;
        
        return (
            <div className="space-y-3 pt-2">
                <div className="space-y-1">
                    <label className="text-xs text-slate-500 font-medium flex items-center gap-1">
                        <Server size={12} /> 提供者 (Provider)
                    </label>
                    <select
                        value={provider || ""}
                        onChange={(e) => {
                            const newProvider = e.target.value;
                            setProvider(newProvider);
                            if (newProvider === "Gemini") setModel(isMain ? "gemini-1.5-pro" : "gemini-1.5-flash");
                            else if (newProvider === "OpenAI") setModel("gpt-4o");
                            else if (newProvider === "omlx") {
                                setUrl("http://127.0.0.1:8000/v1");
                                setModel("");
                            }
                            else setModel(""); 
                        }}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                    >
                        {PROVIDERS.map((p) => (
                            <option key={p} value={p}>{p}</option>
                        ))}
                    </select>
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between items-center">
                        <label className="text-xs text-slate-500 font-medium flex items-center gap-1">
                            <Bot size={12} /> 模型名稱
                        </label>
                        <button
                            onClick={() => fetchModelsForTier(type, provider || "", url || "", store.api_key || "")}
                            disabled={isLoading}
                            className="text-[10px] text-blue-400 hover:text-blue-300 disabled:opacity-50 p-1 hover:bg-slate-800 rounded transition-all"
                            title="重新整理模型列表"
                        >
                            <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
                        </button>
                    </div>

                    {currentModels.length > 0 ? (
                        <select
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                        >
                            {currentModels.map((m) => (
                                <option key={m} value={m}>{m}</option>
                            ))}
                        </select>
                    ) : (
                        <Input
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="h-9 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-600 rounded-lg"
                            placeholder="輸入模型名稱..."
                        />
                    )}
                </div>

                {(provider?.includes("Local") || provider?.includes("Ollama") || provider === "omlx") && (
                    <div className="space-y-1">
                        <label className="text-xs text-slate-500 font-medium">API URL</label>
                        <Input
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            className="h-9 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-600 rounded-lg"
                        />
                    </div>
                )}

                {(provider === "Gemini" || provider === "OpenAI") && (
                    <div className="space-y-1 pt-2 border-t border-slate-700/50">
                        <label className="text-xs text-slate-500 flex items-center gap-1 font-medium">
                            <Key size={12} /> {provider === "OpenAI" ? "API Key" : "Google API Key"}
                        </label>
                        <Input
                            type="password"
                            value={store.api_key || ""}
                            onChange={(e) => store.setApiKey(e.target.value)}
                            className="h-9 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-600 rounded-lg"
                            placeholder="sk-..."
                        />
                    </div>
                )}
            </div>
        );
    };

    if (collapsed) {
        return (
            <div className="p-2 border-t border-slate-700/50">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsOpen(!isOpen)}
                    title="模型設定"
                    className="w-full text-slate-400 hover:text-white hover:bg-slate-800"
                >
                    <Settings size={20} />
                </Button>
            </div>
        );
    }

    return (
        <div className="p-4 border-t border-slate-700/50 bg-slate-800/30 backdrop-blur-sm">
            <div 
                className="flex items-center justify-between mb-0 cursor-pointer group"
                onClick={() => setIsOpen(!isOpen)}
            >
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2 group-hover:text-white transition-colors">
                    <Bot size={16} className="text-slate-400 group-hover:text-blue-400" /> 
                    模型設定
                </h3>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-slate-500 group-hover:text-slate-300">
                    {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                </Button>
            </div>

            {isOpen && (
                <div className="mt-3 animate-in slide-in-from-top-2 fade-in duration-200">
                     <Tabs defaultValue="main" className="w-full">
                        <TabsList className="grid w-full grid-cols-2 bg-slate-900/80 p-1 h-9 mb-3">
                            <TabsTrigger value="main" className="text-xs data-[state=active]:bg-slate-700 data-[state=active]:text-slate-100">主要模型</TabsTrigger>
                            <TabsTrigger value="fast" className="text-xs data-[state=active]:bg-slate-700 data-[state=active]:text-slate-100">快速模型</TabsTrigger>
                        </TabsList>
                        <TabsContent value="main" className="mt-0">
                            {renderConfig("main")}
                        </TabsContent>
                        <TabsContent value="fast" className="mt-0">
                            {renderConfig("fast")}
                        </TabsContent>
                    </Tabs>
                </div>
            )}

            {!isOpen && (
                <div className="text-xs text-slate-500 mt-2 truncate flex items-center gap-1.5 pl-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500/50"></div>
                    {store.provider} <span className="text-slate-600">/</span> {store.model_name}
                </div>
            )}
        </div>
    );
}
