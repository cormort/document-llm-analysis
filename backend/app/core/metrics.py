from prometheus_client import Counter, Histogram

# LLM Token Usage Counter
LLM_TOKEN_USAGE_TOTAL = Counter(
    "llm_token_usage_total",
    "Total LLM tokens used",
    ["provider", "model"]
)

# ChromaDB Query Latency Histogram
CHROMADB_QUERY_LATENCY_SECONDS = Histogram(
    "chromadb_query_latency_seconds",
    "Latency of ChromaDB queries in seconds",
    ["collection"]
)
