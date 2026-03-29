# 專案技術棧與維護說明 (Technical Documentation & Maintenance Guide)

> **Version**: 2.0 (Refactored for Agentic Workflow)
> **Last Updated**: 2026-01-21

本文件詳述了「Document LLM Analysis Agent」的開發架構、技術棧選擇、核心邏輯及後續維護規範。

---

## 1. 系統架構 (System Architecture)

專案已從單純的 RAG 服務重構為 **Agent-First** 架構，核心由 LangGraph 驅動，前端採用 IDE 風格的三欄式佈局。

- **Frontend**: 基於 Next.js 16+ 的單頁應用 (SPA)，使用 React 19 與 Tailwind CSS 4，採用 `react-resizable-panels` 實現多工介面。
- **Backend**: 基於 FastAPI 的異步網頁服務，並整合 **LangGraph** 作為 Agent 的狀態機與決策引擎。
- **Core Engine**:
  - **Agentic Workflow**: 能夠自主規劃任務、調用工具 (RAG, Python Analysis) 的智能體。
  - **RAG Service**: 保留原有的高效檢索增強生成模組。

---

## 2. 技術棧詳情 (Tech Stack)

### 後端 (Backend)

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **Agent Orchestration**: **[LangGraph](https://langchain-ai.github.io/langgraph/)** (核心) - 用於構建有狀態、多步驟的代理應用。
- **LLM Framework**: **[LangChain](https://www.langchain.com/)** - 用於模型綁定與工具調用。
- **Runtime Optimization**: 針對 M4 Mac 優化，支援多核心併發處理。
- **依賴管理**: 使用 `pip` 與 `requirements.txt` (支援 `langchain-google-genai`, `langchain-openai`)。
- **數據處理**: `Pandas`, `NumPy`, `OpenPyXL`。
- **向量資料庫**: `ChromaDB` (本地化存儲)。
- **嵌入模型**: `Sentence-Transformers` (`paraphrase-multilingual-MiniLM-L12-v2`)。
- **異步串流**: `sse-starlette` (支援 Agent 的 Token-by-Token 串流輸出)。

### 前端 (Frontend)

- **Framework**: [Next.js 16.1.1 (App Router)](https://nextjs.org/)
- **UI 框架**: [Tailwind CSS 4](https://tailwindcss.com/), [Radix UI](https://www.radix-ui.com/)。
- **Layout Engine**: **[react-resizable-panels](https://github.com/bvaughn/react-resizable-panels)** (實現 IDE 風格的 Sidebar/Main/Context 三欄佈局)。
- **狀態管理**: [Zustand](https://github.com/pmndrs/zustand) (全域 Store，管理對話 Thread 與狀態)。
- **數據獲取**: [@tanstack/react-query](https://tanstack.com/query/latest)。
- **圖表視覺化**: [Plotly.js](https://plotly.com/javascript/), [Recharts](https://recharts.org/)。
- **圖標庫**: [Lucide React](https://lucide.dev/)。

---

## 3. 核心功能邏輯與流程

### 3.1 Agentic Workflow (LangGraph)

- **架構**: 採用 State Machine (Graph) 設計，包含 Node (節點) 與 Edge (邊)。
- **State**: `messages` (對話歷史), `sender` (當前發言者)。
- **流程**:
  1.  `call_model`: 調用 LLM (Gemini/OpenAI) 進行思考。
  2.  `tools_condition`: 判斷是否需要調用工具。
  3.  `tool_node`: 執行工具 (如 `retrieve_documents`)。
  4.  回圈直到完成任務。

### 3.2 RAG (檢索增強生成)

- 支援 PDF/DOCX/TXT/Excel 上傳。
- **預處理**: 自動去除合併儲存格、語義分析分片 (Semantic Chunking)。
- **檢索**: 基於語義相似度在本地 ChromaDB 進行 Top-K 檢索。

---

## 4. 維護與開發指南

### 4.1 專案結構 (Directory Structure)

```
.
├── backend/
│   ├── app/
│   │   ├── agent/          # [NEW] LangGraph Agent 核心邏輯
│   │   │   ├── graph.py    # 圖定義 (Workflow)
│   │   │   ├── nodes.py    # 節點邏輯 (LLM調用)
│   │   │   ├── state.py    # 狀態定義 (AgentState)
│   │   │   └── tools.py    # 工具定義 (RAG wrap)
│   │   ├── api/            # API Endpoints
│   │   │   ├── agent.py    # [NEW] Agent SSE Endpoint
│   │   │   ├── rag.py      # 原 RAG Endpoint
│   │   │   └── ...
│   │   ├── services/       # 核心服務 (RAGService, LLMService)
│   │   └── core/           # 設定 (Config)
│   └── main.py             # FastAPI 入口
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── agent/      # [NEW] Agent Workspace 頁面
│   │   │   ├── rag/        # RAG 頁面
│   │   │   └── page.tsx    # Dashboard (入口)
│   │   ├── components/
│   │   │   ├── chat/       # 聊天組件
│   │   │   ├── layout/     # [NEW] AppLayout (ThreadSidebar, TabbedPanel, RightPanel)
│   │   │   └── stats/      # 統計圖表組件
│   │   └── lib/
│   │       ├── store.ts    # [NEW] Zustand Store
│   │       └── api.ts      # API Clients
│   └── package.json
├── App.log                 # 應用日誌
└── start_all.sh            # [Access] 一鍵啟動腳本
```

### 4.2 啟動方式 (How to Start)

本專案提供一鍵啟動腳本，會同時啟動 Backend 與 Frontend：

```bash
# 在專案根目錄執行
bash start_all.sh

# 或者 Mac 用戶雙擊執行
Start OpenCode.command
```

服務位置：

- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Docs**: `http://localhost:8000/docs`

### 4.3 配置 (Configuration)

- **API Keys**: 所有外部 API (Google Gemini, OpenAI) 金鑰均在`.env`文件中配置。
- **動態配置**: Agent 支援從前端 UI 傳入 API Key，覆蓋環境變數設定 (詳見 `backend/app/agent/nodes.py`)。

---

## 5. 常見問題 (Troubleshooting)

1.  **Backend 啟動失敗 (ModuleNotFoundError)**:
    - 請確認是否已啟動虛擬環境: `source .venv/bin/activate`
    - 請確認依賴是否安裝: `pip install -r requirements.txt`

2.  **Frontend 建置錯誤 (PanelGroup)**:
    - 本專案使用 `react-resizable-panels` v4+。請確保 `AppLayout.tsx` 使用 `Group` 與 `Separator` 並正確別名為 `PanelGroup`。

3.  **LLM 回應 400 API Key Invalid**:
    - 請檢查 `.env` 中的 `GOOGLE_API_KEY` 是否正確。
    - 或者在前端介面的「設定」中填入有效的 API Key。

---

_Created by Antigravity AI_
