"use client";

import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from "react-resizable-panels";
import { ThreadSidebar } from "./ThreadSidebar";
import { TabbedPanel } from "./TabbedPanel";
import { RightPanel } from "./RightPanel";
import { LLMQueueBanner } from "@/components/llm-queue-status";
import { useEffect, useState } from "react";


export function AppLayout() {
const [isMounted, setIsMounted] = useState(false);

useEffect(() => {
// eslint-disable-next-line react-hooks/set-state-in-effect
setIsMounted(true);
}, []);

if (!isMounted) return null;

return (
<div className="h-screen flex flex-col bg-background overflow-hidden">
{/* New Header Style */}
<div className="h-14 border-b border-slate-200 flex items-center px-4 bg-white shrink-0 z-10">
<div className="font-bold text-xl bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
OpenWork
</div>
<div className="ml-4 text-xs text-slate-400 border px-1.5 py-0.5 rounded border-slate-200">
v2.0 Beta
</div>
</div>

<PanelGroup orientation="horizontal" className="flex-1">
{/* Left Sidebar: Thread List */}
<Panel defaultSize="20" minSize="15" maxSize="30" className="min-w-[200px]">
<ThreadSidebar />
</Panel>

<PanelResizeHandle className="w-[1px] bg-slate-200 hover:bg-blue-400 transition-colors" />

{/* Center: Main Chat/Tabs */}
<Panel defaultSize="55" minSize="30">
<TabbedPanel />
</Panel>

<PanelResizeHandle className="w-[1px] bg-slate-200 hover:bg-blue-400 transition-colors" />

{/* Right: Context/Info */}
<Panel defaultSize="25" minSize="20" maxSize="40" className="min-w-[250px]">
<RightPanel />
</Panel>
</PanelGroup>

{/* LLM Queue Status Banner */}
<LLMQueueBanner />
</div>
);
}
