# Astute RAG 優化計畫

> **基於 Astute RAG 論文概念優化現有 RAG 系統**  
> **創建日期**: 2026-01-24  
> **實作完成日期**: 2026-01-24  
> **狀態**: ✅ 已實作

---

## 📦 實作成果

### 新增檔案

| 檔案                                             | 說明                           |
| ------------------------------------------------ | ------------------------------ |
| `backend/app/services/reliability_scorer.py`     | 可靠性評分器 (Phase 3)         |
| `backend/app/services/knowledge_consolidator.py` | 知識整合器 (Phase 2)           |
| `backend/app/services/astute_rag_service.py`     | Astute RAG 主服務 (All Phases) |

### 修改檔案

| 檔案                        | 變更                          |
| --------------------------- | ----------------------------- |
| `backend/app/models/rag.py` | 新增 Astute RAG 請求/回應模型 |
| `backend/app/api/rag.py`    | 新增 3 個 API Endpoints       |

### 新增 API Endpoints

| Endpoint                      | 功能                 |
| ----------------------------- | -------------------- |
| `POST /api/rag/astute/query`  | 完整 Astute RAG 查詢 |
| `POST /api/rag/astute/elicit` | 內部知識抽取         |
| `POST /api/rag/astute/verify` | 答案驗證             |

---

## 📚 Astute RAG 核心概念

Astute RAG (Wang et al.) 針對傳統 RAG 的兩大問題提出解決方案：

1. **不完美的檢索 (Imperfect Retrieval)**: 檢索結果可能不相關、不完整或有噪音
2. **知識衝突 (Knowledge Conflicts)**: LLM 內部知識與外部檢索知識之間的矛盾

### Astute RAG 三大核心機制

| 機制                               | 說明                                | 目的               |
| ---------------------------------- | ----------------------------------- | ------------------ |
| **Adaptive Elicitation**           | 自適應地從 LLM 內部知識抽取相關資訊 | 補充檢索結果的不足 |
| **Source-Aware Consolidation**     | 迭代式整合內外部知識，識別矛盾      | 解決知識衝突       |
| **Reliability-Based Finalization** | 根據資訊可靠性評估最終答案          | 確保輸出準確性     |

---

## 🔍 現有系統分析

### 現有 RAG Pipeline (`rag_service.py`)

```
當前流程：
Query → Query Expansion → Hybrid/Vector Search → Rerank → (Graph Enhancement) → Context Compression → LLM Answer
```

**現有功能**：

- ✅ 向量語意搜尋 (BGE-M3)
- ✅ 混合搜尋 (Vector + Keyword)
- ✅ 查詢擴展 (LLM-based)
- ✅ Cross-Encoder Reranking (BGE-reranker-base)
- ✅ 語意分塊 (Semantic Chunker)
- ✅ 上下文壓縮 (Extractive/Summary)
- ✅ 知識圖譜增強 (Graph RAG)
- ✅ 多文件搜尋

**缺失的關鍵能力**：

- ❌ LLM 內部知識抽取
- ❌ 內外部知識一致性驗證
- ❌ 知識衝突檢測與解決
- ❌ 資訊可靠性評估
- ❌ 自適應決策：何時使用 RAG vs 純 LLM

---

## 📋 改進計畫

### Phase 1: Internal Knowledge Elicitation (內部知識抽取)

**目標**: 在檢索前/後，從 LLM 抽取其內部相關知識

#### 1.1 新增 `elicit_internal_knowledge` 方法

```python
async def elicit_internal_knowledge(
    self,
    query: str,
    provider: str = None,
    model_name: str = None,
) -> dict:
    """
    從 LLM 內部知識抽取與查詢相關的資訊。

    Returns:
        {
            "internal_answer": str,       # LLM 的初步回答
            "confidence": float,          # 自我評估的信心度 (0-1)
            "key_facts": list[str],       # 提取的關鍵事實
            "knowledge_gaps": list[str],  # 識別的知識盲區
        }
    """
```

**提示設計**:

```
你是專業助手。請根據你的知識回答以下問題。

問題：{query}

請提供：
1. 你的初步回答
2. 你對這個回答的信心程度 (0-1)
3. 你確定的關鍵事實 (列表)
4. 你不確定或需要查證的部分 (列表)

以 JSON 格式輸出。
```

#### 1.2 修改 Pipeline 入口

```python
async def get_astute_context(
    self,
    query: str,
    ...
    use_internal_knowledge: bool = True,  # 新增參數
) -> dict:
    # Step 0: 抽取內部知識
    internal_knowledge = None
    if use_internal_knowledge:
        internal_knowledge = await self.elicit_internal_knowledge(query)

    # Step 1-N: 現有檢索流程...
```

---

### Phase 2: Source-Aware Knowledge Consolidation (來源感知整合)

**目標**: 比對內部知識與檢索結果，識別一致與衝突

#### 2.1 新增 `consolidate_knowledge` 方法

```python
async def consolidate_knowledge(
    self,
    query: str,
    internal_knowledge: dict,
    retrieved_passages: list[dict],
) -> dict:
    """
    整合內部與外部知識，識別一致性。

    Returns:
        {
            "consistent_facts": list[dict],   # 內外一致的事實
            "conflicts": list[dict],          # 衝突點
            "external_only": list[dict],      # 僅外部有的資訊
            "internal_only": list[dict],      # 僅內部有的資訊
            "consolidation_summary": str,     # 整合摘要
        }
    """
```

#### 2.2 衝突檢測邏輯

```python
衝突類型：
1. 事實性衝突 (Factual): 數字、日期、名稱不一致
2. 語意衝突 (Semantic): 相同概念的描述矛盾
3. 範圍衝突 (Scope): 資訊涵蓋範圍不同
```

**LLM 提示設計**:

```
分析以下資訊來源：

【LLM 內部知識】
{internal_knowledge}

【檢索文件】
{retrieved_passages}

請識別：
1. 兩者一致的事實
2. 明顯衝突的地方（標注衝突類型）
3. 僅在一方出現的資訊
```

---

### Phase 3: Reliability Assessment (可靠性評估)

**目標**: 為每項資訊評估可靠性分數

#### 3.1 新增資訊可靠性評分機制

```python
def compute_reliability_score(
    self,
    fact: dict,
    source_type: str,  # "internal" | "external" | "both"
    consistency_check: dict,
) -> float:
    """
    計算資訊可靠性分數 (0-1)

    評分因素：
    - 來源一致性 (+0.3 if 內外一致)
    - 文件來源可信度 (+0.2 for 官方文件)
    - Rerank 分數權重 (+0.2)
    - LLM 信心度 (+0.2)
    - 資訊時效性 (+0.1)
    """
```

#### 3.2 可靠性驅動的上下文過濾

```python
async def filter_by_reliability(
    self,
    consolidated: dict,
    min_reliability: float = 0.5,
) -> list[dict]:
    # 只保留可靠性分數高於閾值的資訊
    # 衝突資訊需特別標注
```

---

### Phase 4: Adaptive RAG Decision (自適應決策)

**目標**: 根據查詢類型和內部知識信心度，決定是否需要 RAG

#### 4.1 新增查詢分類器

```python
async def classify_query_need(
    self,
    query: str,
    internal_confidence: float,
) -> str:
    """
    判斷查詢類型：
    - "internal_sufficient": LLM 內部知識足夠，不需 RAG
    - "retrieval_required": 需要外部檢索
    - "verification_needed": 內部有答案但需驗證
    """
```

#### 4.2 決策規則

| 內部信心度 | 查詢類型      | 決策                  |
| ---------- | ------------- | --------------------- |
| > 0.8      | 常識/基礎知識 | `internal_sufficient` |
| 0.5-0.8    | 專業/時效性   | `verification_needed` |
| < 0.5      | 特定文件內容  | `retrieval_required`  |

---

### Phase 5: Final Answer Generation (最終答案生成)

**目標**: 基於可靠性評估生成標注來源的答案

#### 5.1 增強答案生成提示

```python
final_prompt = f"""
基於以下經過驗證的資訊回答問題。

【問題】
{query}

【高可靠性資訊（來源一致）】
{consistent_facts}

【需謹慎使用的資訊（存在衝突，已標注）】
{conflicts_with_notes}

【僅來自單一來源】
{single_source_facts}

請生成回答，並：
1. 優先使用高可靠性資訊
2. 對衝突資訊明確說明不同觀點
3. 標注資訊來源
"""
```

#### 5.2 回答結構

```json
{
    "answer": "...",
    "confidence": 0.85,
    "sources_used": [...],
    "conflicts_noted": [...],
    "knowledge_type": "hybrid"  // "internal" | "external" | "hybrid"
}
```

---

## 🏗️ 技術實作要點

### 新增檔案

```
backend/app/services/
├── astute_rag_service.py      # Astute RAG 主服務
├── knowledge_consolidator.py   # 知識整合器
└── reliability_scorer.py       # 可靠性評分器
```

### 修改檔案

```
backend/app/services/rag_service.py  # 整合 Astute RAG 流程
backend/app/api/rag.py               # 新增 API endpoints
backend/app/models/rag.py            # 新增資料模型
frontend/src/components/chat/        # UI 展示衝突/來源
```

### 新增 API Endpoints

```python
POST /api/rag/astute-query      # Astute RAG 查詢
POST /api/rag/verify-answer     # 驗證答案
GET  /api/rag/reliability-report # 可靠性報告
```

---

## 📊 評估指標

| 指標                        | 說明             | 目標         |
| --------------------------- | ---------------- | ------------ |
| **Answer Accuracy**         | 答案正確率       | +10% vs 現有 |
| **Conflict Detection Rate** | 衝突識別率       | > 80%        |
| **Source Attribution**      | 來源標注準確度   | > 90%        |
| **Latency**                 | 額外延遲         | < 500ms      |
| **Robustness**              | 應對噪音資料能力 | 顯著提升     |

---

## 🚧 實作優先順序

| 階段    | 功能                           | 難度 | 價值 | 優先   |
| ------- | ------------------------------ | ---- | ---- | ------ |
| Phase 1 | Internal Knowledge Elicitation | 中   | 高   | ⭐⭐⭐ |
| Phase 3 | Reliability Assessment         | 中   | 高   | ⭐⭐⭐ |
| Phase 4 | Adaptive Decision              | 低   | 中   | ⭐⭐   |
| Phase 2 | Knowledge Consolidation        | 高   | 高   | ⭐⭐   |
| Phase 5 | Enhanced Answer Gen            | 中   | 中   | ⭐     |

**建議實作順序**: Phase 1 → Phase 3 → Phase 4 → Phase 2 → Phase 5

---

## ⚠️ 風險與考量

1. **延遲增加**: 多次 LLM 呼叫會增加響應時間
   - 緩解: 並行執行、快取常見查詢

2. **成本增加**: 更多 token 消耗
   - 緩解: 使用 fast model 做初步判斷，smart model 做最終生成

3. **複雜度提升**: 系統更難除錯
   - 緩解: 詳細 logging、可觀測性工具

4. **邊界情況**: LLM 可能過度自信或過度不自信
   - 緩解: 校準機制、人工標註資料集

---

## 📅 預估時程

| 階段       | 預估工時    |
| ---------- | ----------- |
| Phase 1    | 8 小時      |
| Phase 2    | 12 小時     |
| Phase 3    | 6 小時      |
| Phase 4    | 4 小時      |
| Phase 5    | 6 小時      |
| 測試與整合 | 8 小時      |
| **總計**   | **44 小時** |

---

## 📚 參考資料

- [Astute RAG: Overcoming Imperfect Retrieval Augmentation and Knowledge Conflicts for Large Language Models](https://arxiv.org/abs/2410.07176)
- 現有實作: `backend/app/services/rag_service.py`
