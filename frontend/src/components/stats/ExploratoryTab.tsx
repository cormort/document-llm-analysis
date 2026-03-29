"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DescriptiveTab } from "./DescriptiveTab";
import { CorrelationTab } from "./CorrelationTab";
import { GroupByTab } from "./GroupByTab";
import { Ruler, Link, Boxes } from "lucide-react";
import { DiagnosticResponse, EDAResponse, LLMConfig } from "@/lib/api";

interface ExploratoryTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    config: LLMConfig;
    processing: boolean;
    diagnostics: DiagnosticResponse | null;
    edaResults: EDAResponse | null;
    onRunEDA: (type: "correlation" | "groupby", params?: Record<string, unknown>) => void;
    onInterpret: (type: "eda") => void;
    isInterpreting: boolean;
}

export function ExploratoryTab({
    selectedDoc,
    filePath,
    config,
    processing,
    diagnostics,
    edaResults,
    onRunEDA,
    onInterpret,
    isInterpreting
}: ExploratoryTabProps) {
    const [subTab, setSubTab] = useState("descriptive");

    return (
        <div className="space-y-4">
            <Tabs value={subTab} onValueChange={setSubTab} className="w-full">
                <div className="border-b mb-4 pb-1">
                    <TabsList className="bg-transparent border-b-0 p-0 h-auto gap-4">
                        <TabsTrigger 
                            value="descriptive" 
                            className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none px-2 pb-2 pt-1"
                        >
                            <Ruler size={14} className="mr-2"/> 敘述性統計
                        </TabsTrigger>
                        <TabsTrigger 
                            value="correlation" 
                            className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none px-2 pb-2 pt-1"
                        >
                            <Link size={14} className="mr-2"/> 相關性分析
                        </TabsTrigger>
                         <TabsTrigger 
                            value="groupby" 
                            className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none px-2 pb-2 pt-1"
                        >
                            <Boxes size={14} className="mr-2"/> 分組/交叉分析
                        </TabsTrigger>
                    </TabsList>
                </div>

                <TabsContent value="descriptive" className="mt-0">
                    <DescriptiveTab 
                        selectedDoc={selectedDoc}
                        filePath={filePath}
                        config={config}
                    />
                </TabsContent>

                <TabsContent value="correlation" className="mt-0">
                    <CorrelationTab 
                        selectedDoc={selectedDoc}
                        processing={processing}
                        edaResults={edaResults}
                        onRunCorrelation={() => onRunEDA("correlation")}
                        onInterpret={() => onInterpret("eda")}
                        isInterpreting={isInterpreting}
                    />
                </TabsContent>
                
                <TabsContent value="groupby" className="mt-0">
                    <GroupByTab 
                        selectedDoc={selectedDoc}
                        processing={processing}
                        edaResults={edaResults}
                        diagnostics={diagnostics}
                        onRunGroupBy={(params) => onRunEDA("groupby", params)}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}
