/**
 * 後端 API 客戶端（原本不在版控中，此檔依 `frontend/src/**` 的實際呼叫點重建）。
 *
 * 提供：
 *  - `apiFetch`：統一注入 Authorization、統一錯誤處理、支援 AbortSignal
 *  - `apiStream`：解析 SSE（event: message / data:）的 async generator
 *  - 各端點的具名函式與型別（與 backend/app/models 的 Pydantic 模型對齊）
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const TOKEN_STORAGE_KEY = "auth_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function buildHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

async function extractError(res: Response): Promise<ApiError> {
  let detail: unknown;
  let message = `請求失敗 (${res.status})`;
  try {
    const data = await res.json();
    detail = data;
    if (typeof data?.detail === "string") message = data.detail;
    else if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      message = data.detail.map((d: { msg: string }) => d.msg).join("; ");
    }
  } catch {
    // 非 JSON 回應（例如 500 HTML）就沿用預設訊息
  }
  return new ApiError(message, res.status, detail);
}

/** 送出 JSON 請求並解析回應。 */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const { json, ...rest } = init ?? {};
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: buildHeaders(rest),
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  if (!res.ok) throw await extractError(res);
  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

/** 送出請求並回傳 Blob（用於檔案下載）。 */
export async function apiDownload(path: string, json: unknown): Promise<Blob> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: buildHeaders({ body: "{}" }),
    body: JSON.stringify(json),
  });
  if (!res.ok) throw await extractError(res);
  return res.blob();
}

/**
 * 解析 SSE 串流。
 *
 * 後端使用 sse-starlette，事件格式為：
 *   event: message
 *   data: <chunk>
 *
 * 只 yield data 內容；`event: done` 或 `[DONE]` 代表結束。
 */
async function* apiStream(
  path: string,
  json: unknown,
  signal?: AbortSignal
): AsyncGenerator<string, void, unknown> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: buildHeaders({ body: "{}" }),
    body: JSON.stringify(json),
    signal,
  });

  if (!res.ok) throw await extractError(res);
  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 事件以空行分隔
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        let eventName = "message";
        const dataLines: string[] = [];
        for (const line of rawEvent.split("\n")) {
          if (line.startsWith("event:")) eventName = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
        }

        const data = dataLines.join("\n");
        if (eventName === "error") throw new ApiError(data || "串流發生錯誤", 500);
        if (data && data !== "[DONE]") yield data;
        if (eventName === "done") return;

        boundary = buffer.indexOf("\n\n");
      }
    }
    // 收尾：處理沒有以空行結尾的最後一段
    const tail = buffer.trim();
    if (tail.startsWith("data:")) {
      const data = tail.slice(5).trim();
      if (data && data !== "[DONE]") yield data;
    }
  } finally {
    reader.releaseLock();
  }
}

/* ------------------------------------------------------------------ */
/* 共用型別（對應 backend/app/models/*）                                */
/* ------------------------------------------------------------------ */

export interface LLMConfig {
  provider: string;
  model_name?: string;
  local_url?: string;
  api_key?: string;
  context_window?: number;
}

/* -------------------------- 統計 / 診斷 --------------------------- */

export interface DataQualityItem {
  column: string;
  dtype: string;
  missing_count: number;
  missing_percentage: number;
  unique_count: number;
  sample_values: unknown[];
}

export interface DiagnosticResponse {
  summary_stats: Record<string, unknown>;
  quality_report: DataQualityItem[];
  interpretation?: string | null;
}

export interface DescriptiveStatRow {
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
  stats: DescriptiveStatRow[];
  error?: string;
}

export interface EDAResponse {
  result_data: unknown;
  interpretation?: string | null;
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
  /** 前端畫圖時需要知道用了幾個主成分（後端會原樣帶回） */
  n_components?: number;
  n_clusters?: number;
  data: Record<string, unknown>[];
  components_variance?: number[] | null;
  feature_weights?: Record<string, number[]> | null;
  cluster_centers?: Record<string, Record<string, number>> | null;
  interpretation?: string | null;
}

export interface TransformResponse {
  success: boolean;
  new_column: string;
  values: unknown[];
  preview: Record<string, unknown>[];
}

export interface DataPrepResponse {
  success: boolean;
  message: string;
  new_columns: string[];
  preview: Record<string, unknown>[];
}

export interface FieldAnalysisResponse {
  interpretation: string;
}

export interface FeatureSuggestionsResponse {
  suggestions: string;
}

export interface DatasetAnalysisResponse {
  interpretation: string;
}

export interface QueryExecuteResponse {
  success: boolean;
  data?: Record<string, unknown>[] | null;
  summary?: string | null;
  error?: string | null;
}

export interface NLToSQLResponse {
  sql: string;
  success: boolean;
  data?: Record<string, unknown>[] | null;
  summary?: string | null;
  interpretation?: string | null;
  error?: string | null;
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

/* ---------------------------- 建模 -------------------------------- */

export interface FeatureImportanceItem {
  feature: string;
  importance: number;
}

export interface RegressionResponse {
  coefficients: Record<string, number>;
  intercept: number;
  r2_score: number;
  rmse: number;
  predictions: number[];
  actual: number[];
  feature_importance?: FeatureImportanceItem[] | null;
  interpretation?: string | null;
}

export interface ROCCurve {
  fpr: number[];
  tpr: number[];
  auc: number;
}

export interface ClassificationResponse {
  model_type: string;
  classes: unknown[];
  coefficients: Record<string, number>;
  /** accuracy / precision / recall / f1 */
  metrics: Record<string, number>;
  confusion_matrix: number[][];
  roc_curve?: ROCCurve | null;
  predictions: unknown[];
  actual: unknown[];
  feature_importance?: FeatureImportanceItem[] | null;
  interpretation?: string | null;
}

export interface TimeSeriesResponse {
  trend: (number | null)[];
  seasonal: (number | null)[];
  residual: (number | null)[];
  dates: string[];
  values: number[];
  forecast?: number[] | null;
  forecast_dates?: string[] | null;
  interpretation?: string | null;
}

/* ------------------------ 檔案 / 文件 ----------------------------- */

export interface DataFileInfo {
  file_name: string;
  file_path: string;
  size_bytes: number;
  modified_at: string;
}

export interface DocumentInfo {
  collection_name: string;
  file_name: string;
  chunk_count: number;
  indexed_at: string;
}

export interface ReindexDetail {
  status: "success" | "skipped" | "error";
  file_name?: string;
  collection?: string;
  chunks?: number;
  error?: string;
}

export interface ReindexAllResult {
  success: boolean;
  message?: string;
  error?: string;
  total?: number;
  reindexed?: number;
  failed?: number;
  details?: ReindexDetail[];
}

export interface UploadResponse {
  success: boolean;
  file_path: string;
  message: string;
}

export interface IndexResponse {
  success: boolean;
  collection_name?: string;
  chunk_count?: number;
  message?: string;
}

/* ---------------------------- 報告 -------------------------------- */

export interface SkillInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  prompt_fragment: string;
}

export interface TemplateInfo {
  id: string;
  name: string;
  description: string;
  recommended_skills: string[];
}

export interface ReportResponse {
  report_id: string;
  content: string;
  docx_path?: string | null;
  fact_check_results?: Record<string, unknown>[] | null;
}

/* ------------------------------------------------------------------ */
/* 統計 / 診斷端點                                                      */
/* ------------------------------------------------------------------ */

export async function getDiagnostic(
  request: { file_path: string; config: LLMConfig },
  signal?: AbortSignal
): Promise<DiagnosticResponse> {
  return apiFetch<DiagnosticResponse>("/api/stats/diagnostic", {
    method: "POST",
    json: request,
    signal,
  });
}

export async function getDescriptiveStats(
  request: { file_path: string; config: LLMConfig },
  signal?: AbortSignal
): Promise<DescriptiveStatsResponse> {
  return apiFetch<DescriptiveStatsResponse>("/api/stats/descriptive", {
    method: "POST",
    json: request,
    signal,
  });
}

export async function performEDA(
  params: {
    file_path: string;
    analysis_type: string;
    params?: Record<string, unknown>;
    config: LLMConfig;
    skip_interpretation?: boolean;
  },
  signal?: AbortSignal
): Promise<EDAResponse> {
  return apiFetch<EDAResponse>("/api/stats/eda", {
    method: "POST",
    json: {
      ...params,
    },
    signal,
  });
}

export async function performStatTest(
  params: {
    file_path: string;
    test_type: string;
    target_columns: string[];
    group_column?: string | null;
    config: LLMConfig;
  },
  signal?: AbortSignal
): Promise<StatTestResponse> {
  return apiFetch<StatTestResponse>("/api/stats/test", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function performMultivariate(
  request: MultivariateRequest,
  signal?: AbortSignal
): Promise<MultivariateResponse> {
  return apiFetch<MultivariateResponse>("/api/stats/multivariate", {
    method: "POST",
    json: request,
    signal,
  });
}

export async function interpretStats(
  params: {
    context: string;
    data_summary: string;
    test_type: string;
    config: LLMConfig;
  },
  signal?: AbortSignal
): Promise<{ interpretation: string }> {
  return apiFetch<{ interpretation: string }>("/api/stats/interpret", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function transformVariable(
  params: {
    file_path: string;
    new_column: string;
    expression: string;
    config?: LLMConfig;
  },
  signal?: AbortSignal
): Promise<TransformResponse> {
  return apiFetch<TransformResponse>("/api/stats/transform", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function getColumnData(
  params: { file_path: string; columns: string[] },
  signal?: AbortSignal
): Promise<Record<string, unknown[]>> {
  return apiFetch<Record<string, unknown[]>>("/api/stats/data", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function getFieldAnalysis(
  params: {
    field_name: string;
    stats: Record<string, unknown>;
    sample_values: unknown[];
    config: LLMConfig;
  },
  signal?: AbortSignal
): Promise<FieldAnalysisResponse> {
  return apiFetch<FieldAnalysisResponse>("/api/stats/field-analysis", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function getFeatureSuggestions(
  request: { schema_info: string; config: LLMConfig },
  signal?: AbortSignal
): Promise<FeatureSuggestionsResponse> {
  return apiFetch<FeatureSuggestionsResponse>("/api/stats/feature-suggestions", {
    method: "POST",
    json: request,
    signal,
  });
}

export async function getDatasetAnalysis(
  request: { summary_text: string; config: LLMConfig },
  signal?: AbortSignal
): Promise<DatasetAnalysisResponse> {
  return apiFetch<DatasetAnalysisResponse>("/api/stats/dataset-analysis", {
    method: "POST",
    json: request,
    signal,
  });
}

export async function imputeMissing(
  params: {
    file_path: string;
    column: string;
    method: string;
    fill_value?: unknown;
  },
  signal?: AbortSignal
): Promise<DataPrepResponse> {
  return apiFetch<DataPrepResponse>("/api/stats/impute", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function encodeVariable(
  params: { file_path: string; column: string; method: string },
  signal?: AbortSignal
): Promise<DataPrepResponse> {
  return apiFetch<DataPrepResponse>("/api/stats/encode", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function nlToSQL(
  filePath: string,
  question: string,
  config: LLMConfig,
  signal?: AbortSignal
): Promise<NLToSQLResponse> {
  return apiFetch<NLToSQLResponse>("/api/stats/nl-to-sql", {
    method: "POST",
    json: { file_path: filePath, question, config },
    signal,
  });
}

export async function analyzeBatch(
  params: {
    file_path: string;
    group_by_cols: string[];
    metric_cols: string[];
    analysis_mode?: string;
    currency_unit?: string;
    config: LLMConfig;
  },
  signal?: AbortSignal
): Promise<BatchAnalyzeResponse> {
  return apiFetch<BatchAnalyzeResponse>("/api/batch/analyze", {
    method: "POST",
    json: params,
    signal,
  });
}

/* ------------------------- NL → Pandas ---------------------------- */

function stripCodeFences(text: string): string {
  const trimmed = text.trim();
  const fenced = trimmed.match(/^```(?:python)?\s*([\s\S]*?)```$/);
  return (fenced ? fenced[1] : trimmed).trim();
}

export async function generatePandasQuery(
  filePath: string,
  question: string,
  config: LLMConfig,
  signal?: AbortSignal
): Promise<{ pandas_code: string }> {
  const res = await apiFetch<{ content: string }>("/api/llm/query", {
    method: "POST",
    json: { file_path: filePath, question, config },
    signal,
  });
  return { pandas_code: stripCodeFences(res.content ?? "") };
}

export async function executeQuery(
  params: { file_path: string; pandas_code: string },
  signal?: AbortSignal
): Promise<QueryExecuteResponse> {
  return apiFetch<QueryExecuteResponse>("/api/query/execute", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function interpretQuery(
  question: string,
  dataSummary: string,
  dataSample: unknown,
  config: LLMConfig,
  signal?: AbortSignal
): Promise<{ interpretation: string }> {
  return apiFetch<{ interpretation: string }>("/api/query/interpret", {
    method: "POST",
    json: { question, data_summary: dataSummary, data_sample: dataSample, config },
    signal,
  });
}

/* ---------------------------- 建模 -------------------------------- */

export async function performRegression(
  params: {
    file_path: string;
    feature_cols: string[];
    target_col: string;
    test_size?: number;
    config?: LLMConfig;
  },
  signal?: AbortSignal
): Promise<RegressionResponse> {
  return apiFetch<RegressionResponse>("/api/modeling/regression", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function performClassification(
  params: {
    file_path: string;
    feature_cols: string[];
    target_col: string;
    test_size?: number;
    config?: LLMConfig;
  },
  signal?: AbortSignal
): Promise<ClassificationResponse> {
  return apiFetch<ClassificationResponse>("/api/modeling/classification", {
    method: "POST",
    json: params,
    signal,
  });
}

export async function performTimeSeries(
  params: {
    file_path: string;
    date_col: string;
    value_col: string;
    forecast_periods?: number;
    config?: LLMConfig;
  },
  signal?: AbortSignal
): Promise<TimeSeriesResponse> {
  return apiFetch<TimeSeriesResponse>("/api/modeling/timeseries", {
    method: "POST",
    json: params,
    signal,
  });
}

/* ------------------------ 檔案 / 文件 ----------------------------- */

export async function listDataFiles(signal?: AbortSignal): Promise<DataFileInfo[]> {
  const res = await apiFetch<{ files: DataFileInfo[] }>("/api/data-files", {
    signal,
  });
  return res.files ?? [];
}

export async function uploadFile(
  file: File,
  signal?: AbortSignal
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    headers: buildHeaders(),
    body: form,
    signal,
  });
  if (!res.ok) throw await extractError(res);
  return (await res.json()) as UploadResponse;
}

export async function listDocuments(signal?: AbortSignal): Promise<DocumentInfo[]> {
  return apiFetch<DocumentInfo[]>("/api/rag/documents", { signal });
}

export async function indexDocument(
  filePath: string,
  chunkingStrategy: string = "semantic",
  signal?: AbortSignal
): Promise<IndexResponse> {
  return apiFetch<IndexResponse>("/api/rag/index", {
    method: "POST",
    json: { file_path: filePath, chunking_strategy: chunkingStrategy },
    signal,
  });
}

export async function deleteDocument(
  collectionName: string,
  signal?: AbortSignal
): Promise<{ success: boolean; message: string }> {
  return apiFetch<{ success: boolean; message: string }>(
    `/api/rag/documents/${encodeURIComponent(collectionName)}`,
    { method: "DELETE", signal }
  );
}

export interface ReindexDocumentResult {
  success: boolean;
  message?: string;
  extracted_tags?: string[];
}

export async function reindexDocument(
  collectionName: string,
  signal?: AbortSignal
): Promise<ReindexDocumentResult> {
  return apiFetch<ReindexDocumentResult>(
    `/api/rag/documents/${encodeURIComponent(collectionName)}/reindex`,
    { method: "POST", signal }
  );
}

export async function reindexAllDocuments(
  signal?: AbortSignal
): Promise<ReindexAllResult> {
  return apiFetch<ReindexAllResult>("/api/rag/reindex-all", {
    method: "POST",
    signal,
  });
}

/* ---------------------------- 模型清單 ---------------------------- */

export async function listModels(
  provider: string,
  localUrl?: string,
  apiKey?: string,
  signal?: AbortSignal
): Promise<string[]> {
  return apiFetch<string[]>("/api/llm/models", {
    method: "POST",
    json: { provider, local_url: localUrl, api_key: apiKey },
    signal,
  });
}

/* ---------------------------- 報告 -------------------------------- */

export async function listSkills(signal?: AbortSignal): Promise<SkillInfo[]> {
  return apiFetch<SkillInfo[]>("/api/reports/skills", { signal });
}

export async function listTemplates(signal?: AbortSignal): Promise<TemplateInfo[]> {
  return apiFetch<TemplateInfo[]>("/api/reports/templates", { signal });
}

export async function generateReport(
  params: {
    template_name: string;
    selected_skills: string[];
    file_path?: string | null;
    user_instruction?: string;
    config: LLMConfig;
    use_fact_checker?: boolean;
  },
  signal?: AbortSignal
): Promise<ReportResponse> {
  return apiFetch<ReportResponse>("/api/reports/generate", {
    method: "POST",
    json: {
      ...params,
    },
    signal,
  });
}

export async function downloadReportDocx(
  content: string,
  title = "AI 分析報告"
): Promise<void> {
  const blob = await apiDownload("/api/reports/download", { content, title });
  if (typeof window === "undefined") return;
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title.replace(/\s+/g, "_")}.docx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

/* ----------------------------- MCP -------------------------------- */

export interface MCPServerInfo {
  name: string;
  description: string;
  enabled: boolean;
  connected: boolean;
  command: string;
}

export interface WebSearchResult {
  title: string;
  url: string;
  snippet: string;
}

export async function listMcpServers(
  signal?: AbortSignal
): Promise<MCPServerInfo[]> {
  const res = await apiFetch<{ success: boolean; servers: MCPServerInfo[] }>(
    "/api/mcp/servers",
    { signal }
  );
  return res.servers ?? [];
}

export async function mcpWebSearch(
  params: { query: string; engine?: string; limit?: number },
  signal?: AbortSignal
): Promise<WebSearchResult[]> {
  const res = await apiFetch<{ success: boolean; results: WebSearchResult[] }>(
    "/api/mcp/web-search",
    {
      method: "POST",
      json: { engine: "duckduckgo", limit: 10, ...params },
      signal,
    }
  );
  return res.results ?? [];
}

export async function mcpConvertToMarkdown(
  uri: string,
  signal?: AbortSignal
): Promise<string> {
  const res = await apiFetch<{
    success: boolean;
    markdown?: string | null;
    error?: string | null;
  }>("/api/mcp/convert-to-markdown", { method: "POST", json: { uri }, signal });

  if (!res.success) {
    throw new ApiError(res.error || "Conversion failed", 400, res);
  }
  return res.markdown ?? "";
}

/* ---------------------------- 串流 -------------------------------- */

export interface RAGStreamRequest {
  question: string;
  collection_names: string[];
  n_results?: number;
  use_rerank?: boolean;
  use_hybrid?: boolean;
  use_query_expansion?: boolean;
  use_compression?: boolean;
  config: LLMConfig;
}

export function queryRAGStream(
  params: RAGStreamRequest,
  signal?: AbortSignal
): AsyncGenerator<string, void, unknown> {
  return apiStream(
    "/api/rag/query/stream",
    {
      n_results: 5,
      use_rerank: true,
      use_hybrid: true,
      use_query_expansion: false,
      use_compression: false,
      ...params,
    },
    signal
  );
}

export function queryAgentStream(
  params: { message: string; thread_id?: string; llm_config?: LLMConfig },
  signal?: AbortSignal
): AsyncGenerator<string, void, unknown> {
  return apiStream("/api/agent/chat", params, signal);
}
