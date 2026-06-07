/**
 * API client for backend communication with SSE streaming support.
 */

const API_BASE = typeof window === "undefined" 
    ? (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8080")
    : ""; // Client side: use relative path to leverage Next.js proxy

export interface LLMConfig {
    provider?: string;
    model_name?: string;
    local_url?: string;
    api_key?: string | null;
    context_window?: number;
}

export interface DocumentInfo {
    collection_name: string;
    file_name: string;
    chunk_count: number;
    indexed_at: string;
}

export interface RAGQueryRequest {
    question: string;
    collection_names: string[];
    n_results?: number;
    use_rerank?: boolean;
    use_hybrid?: boolean;
    use_query_expansion?: boolean;
    use_compression?: boolean;
    compression_method?: "extractive" | "summary";
    use_web_search?: boolean;
    use_strategy?: boolean;
    config?: LLMConfig;
    fast_config?: LLMConfig;
}

export interface SkillInfo {
    id: string;
    name: string;
    description: string;
    category: string;
    prompt_fragment: string;
}

export interface ReportGenerateRequest {
    template_name: string;
    selected_skills: string[];
    file_path?: string | null;
    user_instruction?: string;
    config?: LLMConfig;
    use_fact_checker?: boolean;
}

export interface ReportResponse {
    report_id: string;
    content: string;
    docx_path?: string | null;
    fact_check_results?: object[] | null;
}

export interface QueryExecuteRequest {
    file_path: string;
    pandas_code: string;
}

export interface QueryExecuteResponse {
    success: boolean;
    data?: Record<string, string | number | boolean | null>[] | null;
    summary?: string | null;
    error?: string | null;
}

export interface QueryFixRequest {
    file_path: string;
    original_question: string;
    failed_code: string;
    error_message: string;
}

export interface BatchAnalyzeRequest {
    file_path: string;
    group_by_cols: string[];
    metric_cols: string[];
    analysis_mode?: "pairwise" | "consolidated";
    currency_unit?: string;
    config?: LLMConfig;
}

export interface BatchAnalyzeResult {
    group_value: string;
    analysis_text: string;
    data_summary?: Record<string, unknown> | null;
}

export interface BatchAnalyzeResponse {
    results: BatchAnalyzeResult[];
    consolidated_report?: string | null;
    execution_time: number;
}

// Statistics API
export interface DiagnosticRequest {
    file_path: string;
    config?: LLMConfig;
}

export interface DataQualityItem {
    column: string;
    dtype: string;
    missing_count: number;
    missing_percentage: number;
    unique_count: number;
    sample_values: (string | number | boolean | null)[];
}

export interface DiagnosticResponse {
    summary_stats: Record<string, unknown>;
    quality_report: DataQualityItem[];
    interpretation?: string | null;
}

export interface EDARequest {
    file_path: string;
    analysis_type: "correlation" | "groupby" | "trend" | "pivot";
    params?: Record<string, unknown>;
    config?: LLMConfig;
    skip_interpretation?: boolean;
}

export interface EDAResponse {
    result_data: unknown;
    interpretation?: string | null;
}

export interface StatTestRequest {
    file_path: string;
    test_type: "ttest" | "anova" | "shapiro" | "outliers" | "chi_square" | "mann_whitney" | "kruskal" | "wilcoxon";
    target_columns: string[];
    group_column?: string;
    config?: LLMConfig;
}

export interface StatTestResponse {
    test_results: Record<string, unknown>;
    interpretation?: string | null;
    suggestion?: Record<string, unknown> | null;
}

export interface MultivariateRequest {
    file_path: string;
    analysis_type: "pca" | "kmeans";
    features: string[];
    n_components?: number;
    n_clusters?: number;
    config?: LLMConfig;
}

export interface MultivariateResponse {
    analysis_type: string;
    data: any[];
    components_variance?: number[] | null;
    feature_weights?: Record<string, number[]> | null;
    cluster_centers?: Record<string, Record<string, number>> | null;
    interpretation?: string | null;
}

export interface InterpretStatsRequest {
    context: string;
    data_summary: string;
    test_type: string;
    config?: LLMConfig;
}

export interface InterpretStatsResponse {
    interpretation: string;
}

/**
 * Fetch with error handling and optional timeout.
 */
async function fetchAPI<T>(
    endpoint: string,
    options?: RequestInit & { timeoutMs?: number }
): Promise<T> {
    const { timeoutMs, ...fetchOptions } = options || {};
    
    // Use AbortController for timeout (default: 5 minutes for LLM requests)
    const controller = new AbortController();
    const timeout = timeoutMs || 300000; // 5 minutes default
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const fullUrl = `${API_BASE}${endpoint}`;
        console.log(`[API] Fetching: ${fullUrl}`);
        
        const response = await fetch(fullUrl, {
            ...fetchOptions,
            signal: controller.signal,
            headers: {
                "Content-Type": "application/json",
                ...fetchOptions?.headers,
            },
        });

        if (!response.ok) {
            let errorDetail = "Unknown error";
            try {
                const errorText = await response.text();
                try {
                    const errorJson = JSON.parse(errorText);
                    if (errorJson.message) {
                        errorDetail = errorJson.message;
                        if (errorJson.detail && (typeof errorJson.detail === 'string' || Object.keys(errorJson.detail).length > 0)) {
                            errorDetail += `: ${typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail)}`;
                        }
                    } else if (errorJson.detail) {
                        errorDetail = typeof errorJson.detail === 'string' && errorJson.detail
                            ? errorJson.detail 
                            : JSON.stringify(errorJson.detail);
                    } else {
                        errorDetail = JSON.stringify(errorJson);
                    }
                } catch {
                    // Not a valid JSON, use text directly
                    errorDetail = errorText || `API Error: ${response.status} ${response.statusText}`;
                }
            } catch {
                // Failed to read text (e.g. network error during read)
                errorDetail = `API Error: ${response.status} ${response.statusText}`;
            }
            throw new Error(errorDetail);
        }

        return response.json();
    } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
            throw new Error('請求超時，請稍後再試或縮短文件長度');
        }
        throw error;
    } finally {
        clearTimeout(timeoutId);
    }
}

/**
 * Stream SSE response from an endpoint.
 */
export async function* streamSSE(
    endpoint: string,
    body: object
): AsyncGenerator<string, void, unknown> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        throw new Error(`SSE Error: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
            if (line.startsWith("data:")) {
                const data = line.slice(5).trim();
                if (data === "[DONE]") return;
                if (data) yield data;
            }
        }
    }
}

// Health check
export async function checkHealth(): Promise<{ status: string; service: string }> {
    return fetchAPI("/api/health");
}

// RAG API
export async function listDocuments(): Promise<DocumentInfo[]> {
    return fetchAPI("/api/rag/documents");
}

// Data Files API
export interface DataFileInfo {
    file_name: string;
    file_path: string;
    size_bytes: number;
    modified_at: string;
}

export async function listDataFiles(): Promise<DataFileInfo[]> {
    const res = await fetchAPI<{ files: DataFileInfo[] }>("/api/data-files");
    return res.files;
}

export async function deleteDataFile(fileName: string): Promise<void> {
    await fetchAPI(`/api/data-files/${encodeURIComponent(fileName)}`, { method: "DELETE" });
}

export async function queryRAG(request: RAGQueryRequest): Promise<{ answer: string; sources: object[] }> {
    return fetchAPI("/api/rag/query", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export function queryRAGStream(request: RAGQueryRequest): AsyncGenerator<string, void, unknown> {
    return streamSSE("/api/rag/query/stream", request);
}

export interface AgentChatRequest {
    message: string;
    thread_id?: string;
    llm_config?: LLMConfig;
}

export function queryAgentStream(request: AgentChatRequest): AsyncGenerator<string, void, unknown> {
    return streamSSE("/api/agent/chat", request);
}

export async function indexDocument(
    filePath: string,
    chunkingStrategy: string = "semantic"
): Promise<{ success: boolean; message: string }> {
    return fetchAPI("/api/rag/index", {
        method: "POST",
        body: JSON.stringify({ 
            file_path: filePath,
            chunking_strategy: chunkingStrategy
        }),
    });
}

export async function deleteDocument(collectionName: string): Promise<{ success: boolean; message: string }> {
    return fetchAPI(`/api/rag/documents/${collectionName}`, {
        method: "DELETE",
    });
}

export async function reindexDocument(
    collectionName: string
): Promise<{ success: boolean; message: string; extracted_tags?: string[] }> {
    return fetchAPI(`/api/rag/documents/${collectionName}/reindex`, {
        method: "POST",
    });
}

export interface ReindexAllResult {
    success: boolean;
    reindexed?: number;
    total?: number;
    details?: Array<{
        collection: string;
        file_name?: string;
        status: string;
        chunks?: number;
        error?: string;
    }>;
    error?: string;
}

export async function reindexAllDocuments(): Promise<ReindexAllResult> {
    return fetchAPI("/api/rag/reindex-all", {
        method: "POST",
    });
}

// Upload API
export async function uploadFile(file: File): Promise<{ success: boolean; file_path: string; message: string }> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
        // Don't set Content-Type, fetch will set it correctly with the boundary for FormData
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail || `Upload Error: ${response.status}`);
    }

    return response.json();
}

// LLM API
export async function analyzeText(
    content: string,
    instruction: string,
    config?: LLMConfig
): Promise<{ content: string }> {
    return fetchAPI("/api/llm/analyze", {
        method: "POST",
        body: JSON.stringify({ content, instruction, config }),
    });
}

export function analyzeTextStream(
    content: string,
    instruction: string,
    config?: LLMConfig
): AsyncGenerator<string, void, unknown> {
    return streamSSE("/api/llm/analyze/stream", { content, instruction, config });
}

export async function listModels(
    provider: string,
    localUrl: string,
    apiKey?: string
): Promise<string[]> {
    const params = new URLSearchParams({
        provider,
        local_url: localUrl,
    });
    if (apiKey) params.append("api_key", apiKey);

    return fetchAPI(`/api/llm/models?${params.toString()}`);
}

// Reports API
export async function listSkills(): Promise<SkillInfo[]> {
    return fetchAPI("/api/reports/skills");
}

export interface TemplateInfo {
    id: string;
    name: string;
    description: string;
    recommended_skills: string[];
}

export async function listTemplates(): Promise<TemplateInfo[]> {
    return fetchAPI("/api/reports/templates");
}

export async function generateReport(request: ReportGenerateRequest): Promise<ReportResponse> {
    return fetchAPI("/api/reports/generate", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function downloadReportDocx(content: string, title: string) {
    const response = await fetch(`${API_BASE}/api/reports/download`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ content, title }),
    });

    if (!response.ok) {
        throw new Error("下載失敗");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "_")}.docx`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Data Query API
export interface NLToSQLResponse {
    sql: string;
    success: boolean;
    data?: Record<string, unknown>[] | null;
    summary?: string | null;
    interpretation?: string | null;
    error?: string | null;
}

export async function nlToSQL(
    file_path: string,
    question: string,
    config?: LLMConfig
): Promise<NLToSQLResponse> {
    return fetchAPI("/api/stats/nl-to-sql", {
        method: "POST",
        body: JSON.stringify({ file_path, question, config }),
        timeoutMs: 600000, // 10 minutes: SQL gen + interpretation are 2 sequential LLM calls
    });
}

export async function nlToSQLInterpret(
    question: string,
    sql: string,
    data_sample: Record<string, unknown>[],
    total_rows: number,
    config?: LLMConfig
): Promise<{ interpretation: string }> {
    return fetchAPI("/api/stats/nl-to-sql/interpret", {
        method: "POST",
        body: JSON.stringify({ question, sql, data_sample, total_rows, config }),
    });
}

export async function executeQuery(request: QueryExecuteRequest): Promise<QueryExecuteResponse> {
    return fetchAPI("/api/query/execute", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function interpretQuery(
    question: string,
    summary: string,
    sample: Record<string, string | number | boolean | null>[],
    config?: LLMConfig
): Promise<{ interpretation: string }> {
    return fetchAPI("/api/query/interpret", {
        method: "POST",
        body: JSON.stringify({ question, data_summary: summary, data_sample: sample, config }),
    });
}

// Batch Analysis API
export async function analyzeBatch(request: BatchAnalyzeRequest): Promise<BatchAnalyzeResponse> {
    return fetchAPI("/api/batch/analyze", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

// Statistics API
export async function getDiagnostic(request: DiagnosticRequest): Promise<DiagnosticResponse> {
    return fetchAPI("/api/stats/diagnostic", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export interface DescriptiveStatsItem {
    column: string;
    count: number;
    mean: number;
    std: number;
    min: number;
    q25: number;
    median: number;
    q75: number;
    max: number;
    range: number;
    iqr: number;
    skewness: number;
    kurtosis: number;
}

export interface DescriptiveStatsResponse {
    total_rows: number;
    numeric_columns: number;
    stats: DescriptiveStatsItem[];
}

export async function getDescriptiveStats(request: DiagnosticRequest): Promise<DescriptiveStatsResponse> {
    return fetchAPI("/api/stats/descriptive", {
        method: "POST",
        body: JSON.stringify(request),
    });
}


export async function performEDA(request: EDARequest): Promise<EDAResponse> {
    return fetchAPI("/api/stats/eda", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function performStatTest(request: StatTestRequest): Promise<StatTestResponse> {
    return fetchAPI("/api/stats/test", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function performMultivariate(request: MultivariateRequest): Promise<MultivariateResponse> {
    return fetchAPI("/api/stats/multivariate", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function interpretStats(request: InterpretStatsRequest): Promise<InterpretStatsResponse> {
    return fetchAPI("/api/stats/interpret", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

// ============ Advanced / Synthesis API ============

export interface TransformRequest {
    file_path: string;
    new_column: string;
    expression: string;
}

export interface TransformResponse {
    success: boolean;
    new_column: string;
    values: (string | number | boolean | null)[];
    preview: { index: string | number; [key: string]: string | number | boolean | null | undefined }[];
}

export async function transformVariable(request: TransformRequest): Promise<TransformResponse> {
    return fetchAPI("/api/stats/transform", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export interface GetDataRequest {
    file_path: string;
    columns: string[];
}

export async function getColumnData(request: GetDataRequest): Promise<Record<string, (string | number | boolean | null)[]>> {
    return fetchAPI("/api/stats/data", {
        method: "POST",
        body: JSON.stringify(request),
    });
}


// ============ Modeling API ============

export interface RegressionRequest {
    file_path: string;
    feature_cols: string[];
    target_col: string;
    test_size?: number;
    config?: LLMConfig;
}

export interface RegressionResponse {
    coefficients: Record<string, number>;
    intercept: number;
    r2_score: number;
    rmse: number;
    predictions: number[];
    actual: number[];
    feature_importance?: { feature: string; importance: number }[];
    interpretation?: string | null;
}

export interface TimeSeriesRequest {
    file_path: string;
    date_col: string;
    value_col: string;
    forecast_periods?: number;
    config?: LLMConfig;
}

export interface TimeSeriesResponse {
    trend: (number | null)[];
    seasonal: (number | null)[];
    residual: (number | null)[];
    dates: string[];
    values: number[];
    forecast?: number[];
    forecast_dates?: string[];
    interpretation?: string | null;
}


export interface ClassificationRequest {
    file_path: string;
    feature_cols: string[];
    target_col: string;
    test_size?: number;
    config?: LLMConfig;
}

export interface ClassificationResponse {
    model_type: string;
    classes: (string | number | boolean)[];
    coefficients: Record<string, number>;
    metrics: Record<string, number>;
    confusion_matrix: number[][];
    roc_curve?: { fpr: number[]; tpr: number[]; auc: number } | null;
    predictions: (string | number | boolean)[];
    actual: (string | number | boolean)[];
    feature_importance?: { feature: string; importance: number }[];
    interpretation?: string | null;
}

export async function performRegression(request: RegressionRequest): Promise<RegressionResponse> {
    return fetchAPI("/api/modeling/regression", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function performClassification(request: ClassificationRequest): Promise<ClassificationResponse> {
    return fetchAPI("/api/modeling/classification", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function performTimeSeries(request: TimeSeriesRequest): Promise<TimeSeriesResponse> {
    return fetchAPI("/api/modeling/timeseries", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

// ============ Data Prep API ============

export interface ImputeRequest {
    file_path: string;
    column: string;
    method: "mean" | "median" | "mode" | "constant";
    fill_value?: string | number | boolean | null;
}

export interface EncodeRequest {
    file_path: string;
    column: string;
    method: "label" | "onehot";
}

export interface DataPrepResponse {
    success: boolean;
    message: string;
    new_columns: string[];
    preview: { index: string | number; [key: string]: string | number | boolean | null | undefined }[];
}

export async function imputeMissing(request: ImputeRequest): Promise<DataPrepResponse> {
    return fetchAPI("/api/stats/impute", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function encodeVariable(request: EncodeRequest): Promise<DataPrepResponse> {
    return fetchAPI("/api/stats/encode", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

// ============ AI Field Analysis API ============

export interface FieldAnalysisRequest {
    field_name: string;
    stats: Record<string, unknown>;
    sample_values: (string | number | boolean | null)[];
    config?: LLMConfig;
}

export interface FieldAnalysisResponse {
    interpretation: string;
}

export interface FeatureSuggestionsRequest {
    schema_info: string;
    config?: LLMConfig;
}

export interface FeatureSuggestionsResponse {
    suggestions: string;
}

export async function getFieldAnalysis(request: FieldAnalysisRequest): Promise<FieldAnalysisResponse> {
    return fetchAPI("/api/stats/field-analysis", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function getFeatureSuggestions(request: FeatureSuggestionsRequest): Promise<FeatureSuggestionsResponse> {
    return fetchAPI("/api/stats/feature-suggestions", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export interface DatasetAnalysisRequest {
    summary_text: string;
    config?: LLMConfig;
}

export interface DatasetAnalysisResponse {
    interpretation: string;
}

export async function getDatasetAnalysis(request: DatasetAnalysisRequest): Promise<DatasetAnalysisResponse> {
    return fetchAPI("/api/stats/dataset-analysis", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

// ============ DuckDB SQL Query API ============

export interface SQLQueryRequest {
    file_path: string;
    sql: string;
    config?: LLMConfig;
}

export interface SQLQueryResponse {
    success: boolean;
    data?: Record<string, string | number | boolean | null>[] | null;
    summary?: string | null;
    error?: string | null;
    execution_time_ms?: number | null;
}

export interface NLToSQLRequest {
    file_path: string;
    question: string;
    config?: LLMConfig;
}

export interface NLToSQLResponse {
    sql: string;
    success: boolean;
    data?: Record<string, string | number | boolean | null>[] | null;
    summary?: string | null;
    interpretation?: string | null;
    error?: string | null;
}

export interface SQLSchemaResponse {
    table_name: string;
    stats: {
        table_name: string;
        row_count: number;
        column_count: number;
        columns: Array<{ column_name: string; column_type: string; null: string }>;
    };
    sample: Record<string, string | number | boolean | null>[];
    schema_description: string;
}

/**
 * Execute a raw SQL query using DuckDB on a data file.
 */
export async function executeSQLQuery(request: SQLQueryRequest): Promise<SQLQueryResponse> {
    return fetchAPI("/api/stats/sql-query", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

/**
 * Convert natural language question to SQL, execute, and get interpreted results.
 */
export async function naturalLanguageToSQL(request: NLToSQLRequest): Promise<NLToSQLResponse> {
    return fetchAPI("/api/stats/nl-to-sql", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

/**
 * Get schema information for a file loaded into DuckDB.
 */
export async function getSQLSchema(file_path: string): Promise<SQLSchemaResponse> {
    const params = new URLSearchParams({ file_path });
    return fetchAPI(`/api/stats/sql-schema?${params.toString()}`);
}
