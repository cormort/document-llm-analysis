import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

import requests
import structlog
from app.services.llm_service import llm_service

logger = structlog.get_logger()

# Define data directory for backend
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CACHE_DIR = os.path.join(DATA_DIR, "web_cache")
SNAPSHOT_DIR = os.path.join(DATA_DIR, "web_snapshots")

# Credibility Rules
CREDIBILITY_RULES = {
    "gov.tw": 95, "edu.tw": 90, "org.tw": 85, "arxiv.org": 90,
    "scholar.google": 90, "wikipedia.org": 75, "reuters.com": 80,
    "bbc.com": 80, "nytimes.com": 80, "cna.com.tw": 85,
    "udn.com": 70, "ltn.com.tw": 70, "chinatimes.com": 70,
}

class SearXNGService:
    """
    SearXNG Search Service (Full Backend Port)
    """

    def __init__(self, base_url: str = "http://localhost:4000"):
        self.base_url = base_url
        self._is_available = None
        self._cache_ttl = 600  # 10 minutes
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    def is_available(self) -> bool:
        """Check SearXNG availability"""
        if self._is_available is None:
            try:
                response = requests.get(f"{self.base_url}/healthz", timeout=3)
                self._is_available = response.status_code < 500
            except Exception:
                try:
                    requests.get(self.base_url, timeout=3)
                    self._is_available = True
                except Exception:
                    self._is_available = False
        return self._is_available

    def score_credibility(self, url: str) -> int:
        """Score URL credibility"""
        url_lower = url.lower()
        for domain, score in CREDIBILITY_RULES.items():
            if domain in url_lower:
                return score
        return 50

    def _get_credibility_label(self, score: int) -> str:
        if score >= 90: return "🟢"
        elif score >= 70: return "🟡"
        else: return "🔴"

    def search(
        self,
        query: str,
        categories: str = "general",
        language: str = "zh-TW",
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Execute web search"""
        if not self.is_available():
            return {"success": False, "results": [], "error": "SearXNG Service unavailable"}

        try:
            params = {
                "q": query,
                "format": "json",
                "categories": categories,
                "language": language,
            }
            response = requests.get(f"{self.base_url}/search", params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                results = []
                for r in data.get("results", [])[:max_results]:
                    result_item = {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:300] if r.get("content") else "",
                        "publish_date": r.get("publishedDate") # Try to get if available
                    }
                    result_item["credibility_score"] = self.score_credibility(result_item["url"])
                    results.append(result_item)
                return {"success": True, "results": results, "error": None}
            else:
                return {"success": False, "results": [], "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error("Search failed", error=str(e))
            return {"success": False, "results": [], "error": str(e)}

    def search_with_cache(
        self, query: str, categories: str = "general", max_results: int = 5
    ) -> dict[str, Any]:
        """Search with file-based cache"""
        cache_key = hashlib.md5(f"{query}:{categories}:{max_results}".encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                    cached_time = datetime.fromisoformat(cached["cached_at"])
                    if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                        cached["from_cache"] = True
                        return cached
            except Exception:
                pass

        result = self.search(query, categories, max_results=max_results)
        result["cached_at"] = datetime.now().isoformat()
        result["from_cache"] = False

        if result["success"]:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to cache search result: {e}")

        return result

    def multi_source_search(
        self, query: str, sources: list[str] = None, max_results_per_source: int = 3
    ) -> dict[str, Any]:
        """Parallel multi-source search"""
        if sources is None:
            sources = ["general", "news", "science"]

        all_results = []
        seen_urls = set()

        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            futures = {
                executor.submit(
                    self.search, query, cat, "zh-TW", max_results_per_source
                ): cat
                for cat in sources
            }

            for future in futures:
                cat = futures[future]
                try:
                    result = future.result(timeout=20)
                    if result["success"]:
                        for r in result["results"]:
                            if r["url"] not in seen_urls:
                                seen_urls.add(r["url"])
                                r["source_category"] = cat
                                all_results.append(r)
                except Exception as e:
                    logger.warning(f"Multi-source search failed for {cat}: {e}")

        for r in all_results:
            r["credibility_score"] = self.score_credibility(r["url"])

        all_results.sort(key=lambda x: x["credibility_score"], reverse=True)

        return {
            "success": len(all_results) > 0,
            "results": all_results,
            "sources_searched": sources,
            "error": None if all_results else "No results found",
        }

    async def expand_keywords(self, query: str) -> list[str]:
        """Expand keywords using LLM (Async)"""
        try:
            prompt = f"""Generate 3 related search keywords for: '{query}'. 
            Output ONLY a JSON array of strings. Example: ["keyword1", "keyword2"]
            Do not include markdown formatting like ```json.
            """
            response = await llm_service.generate_text(prompt)
            # Basic cleanup
            cleaned = response.strip().replace("```json", "").replace("```", "").strip()
            keywords = json.loads(cleaned)
            if isinstance(keywords, list):
                return [query] + keywords[:3]
            return [query]
        except Exception as e:
            logger.warning("Keyword expansion failed", error=str(e))
            return [query]

    def save_snapshot(self, url: str, content: str, title: str) -> str | None:
        """Save snapshot of search result"""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{url_hash}.json"
            filepath = os.path.join(SNAPSHOT_DIR, filename)

            snapshot = {
                "url": url,
                "title": title,
                "content": content,
                "captured_at": datetime.now().isoformat(),
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)

            return filepath
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    def format_citation(self, result: dict, style: str = "APA") -> str:
        title = result.get("title", "No Title")
        url = result.get("url", "")
        date = result.get("publish_date", "No Date")
        access_date = datetime.now().strftime("%Y-%m-%d")
        
        if style == "APA":
            return f"{title}. ({date}). Retrieved from {url} (Access: {access_date})"
        return f"{title}. {url}."

    async def summarize_results(self, results: list[dict]) -> str:
        """Summarize results using LLM (Async)"""
        if not results: return "No results to summarize."
        
        contents = "\n---\n".join([
            f"Source {i+1}: {r.get('title', '')}\n{r.get('content', '')}"
            for i, r in enumerate(results[:5])
        ])
        
        prompt = f"Please summarize the following search results into a concise structured summary:\n\n{contents}"
        return await llm_service.generate_text(prompt)

    async def enhanced_search_for_context(
        self,
        query: str,
        use_multi_source: bool = True,
        use_cache: bool = True,
        expand_keywords: bool = False,
        save_snapshots: bool = False,
        # Legacy args ignored or handled internally
        llm_service=None, provider=None, model_name=None, local_url=None 
    ) -> dict[str, Any]:
        """
        Enhanced Search Orchestrator (Async)
        """
        # 1. Expand Keywords
        queries = [query]
        if expand_keywords:
            queries = await self.expand_keywords(query)
            
        all_results = []
        sources_searched = []
        from_cache = False
        
        # 2. Search
        # Note: We run search synchronously in threads or directly, but wrapped in async function
        # For simplicity, we just call the sync methods here.
        
        for q in queries[:3]:
            if use_multi_source:
                result = self.multi_source_search(q, max_results_per_source=2)
                if result['success']:
                    all_results.extend(result["results"])
                    sources_searched.extend(result.get("sources_searched", []))
            elif use_cache:
                result = self.search_with_cache(q)
                if result.get("from_cache"): from_cache = True
                if result['success']:
                    all_results.extend(result["results"])
            else:
                result = self.search(q)
                if result['success']:
                    all_results.extend(result["results"])
                    
        # 3. Dedup & Sort
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)
        
        unique_results.sort(key=lambda x: x.get("credibility_score", 50), reverse=True)
        unique_results = unique_results[:8]
        
        # 4. Snapshots
        if save_snapshots:
            for r in unique_results:
                self.save_snapshot(r["url"], r.get("content", ""), r.get("title", ""))
                
        # 5. Citations
        citations = [self.format_citation(r) for r in unique_results]
        
        # 6. Context String
        context = f"### Web Search Results: {query}\n\n"
        for i, r in enumerate(unique_results, 1):
            cred = self._get_credibility_label(r.get("credibility_score", 50))
            context += f"**{i}. {r['title']}** {cred}\n"
            context += f"   Source: {r['url']}\n"
            if r.get("content"):
                context += f"   > {r['content']}\n"
            context += "\n"
            
        # 7. Summary
        summary = ""
        if unique_results:
            summary = await self.summarize_results(unique_results)
            
        return {
            "context": context,
            "results": unique_results,
            "citations": citations,
            "summary": summary,
            "sources_searched": list(set(sources_searched)),
            "from_cache": from_cache,
            "query": query,
            "expanded_queries": queries,
        }

searxng_service = SearXNGService()
