# Document LLM Analysis Agent (數據與文件深度分析助手)

這是一個專為**專業文件處理**與**結構化數據分析**設計的 AI 助手。它不只是一個聊天介面，更集成了完整的 RAG (檢索增強生成) 流程與 Text-to-Query (自然語言轉查詢) 引擎，並具備專業的三階段分析工作流。

---

## 核心功能亮點

### 1. 多模態分析 (11 種專業模式)
- **對話分析、摘要生成、翻譯、資訊萃取、報表生成、風格轉換、文件校對、圖表繪製**。
- **RAG 文件問答**：針對長 PDF/Word 提供語義搜索問答。
- **智慧查詢 (Text-to-Query)**：自然語言提問自動生成 Pandas 程式碼並執行。

### 2. 三階段智慧分析工作流
- **第一階段：解讀與建議**。AI 自動分析資料欄位，提出具維度與意義的 3 個分析方案。
- **第二階段：採納與執行**。使用者採納建議或自訂提問，AI 生成程式碼執行並顯示數據/圖表。
- **第三階段：判讀與見解**。根據查詢結果，AI 提供「關鍵發現」、「深度洞察」與「行動建議」。

### 3. 專業級預處理
- **Excel 解除合併**：自動處理合併儲存格並填補數值，確保 LLM 讀取正確的表格結構。
- **混合型 RAG**：本地化 ChromaDB 向量資料庫，支援多語言嵌入模型。
- **現代化 UI**：基於 Next.js 的卡片式佈局與響應式設計。

---

## 技術棧 (Tech Stack)

### 後端與核心邏輯 (Backend)
- **語言**：Python 3.12+
- **框架**：FastAPI
- **數據處理**：`Pandas`, `OpenPyXL`, `python-docx`, `pypdf`
- **非結構化檢索 (RAG)**：`ChromaDB`, `Sentence-Transformers`
- **LLM 驅動**：Google Gemini / OpenAI 相容協議

### 前端介面 (Frontend)
- **框架**：Next.js 14+ (App Router)
- **狀態管理**：Zustand
- **樣式**：Tailwind CSS
- **圖表視覺化**：Plotly, Matplotlib

---

## 專案結構

```
document-llm-analysis/
├── backend/           # FastAPI 後端
│   ├── app/           # 應用程式碼
│   │   ├── api/       # API 端點
│   │   ├── services/  # 業務邏輯
│   │   ├── models/    # 資料模型
│   │   └── core/      # 核心設定
│   └── tests/         # 測試
├── frontend/          # Next.js 前端
│   └── src/           # 原始碼
├── data/              # 資料目錄
└── docker-compose.yml # Docker 配置
```

---

## 快速上手 (Quick Start)

### 方式一：本地開發

1. **安裝依賴**：
```bash
cd backend && uv sync
cd ../frontend && npm install
```

2. **啟動後端**：
```bash
cd backend && uv run uvicorn app.main:app --reload
```

3. **啟動前端**：
```bash
cd frontend && npm run dev
```

### 方式二：Docker Compose

```bash
# 開發模式
docker-compose -f docker-compose.dev.yml up -d

# 完整生產模式
docker-compose up -d
```

### 驗證服務

| 服務 | URL |
|------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## 測試

```bash
# 後端測試
cd backend && uv run pytest -v

# 前端測試
cd frontend && npm test
```

---

## CI/CD

專案使用 GitHub Actions 進行 CI/CD：

- **Backend Lint**: Ruff 檢查
- **Backend Tests**: pytest + coverage
- **Frontend Lint**: ESLint
- **Frontend Build**: Next.js build
- **Docker Build**: 映像檔建置測試
- **Security Scan**: Bandit 安全掃描

---

## 與 Open WebUI 的差異

| 特性 | 本專案 | Open WebUI |
| :--- | :--- | :--- |
| **設計核心** | **專業數據工作流** | **通用型聊天介面** |
| **結構化分析** | 三階段專用工作流 | General Chat |
| **數據預處理** | Excel 合併儲存格處理 | 僅基礎文件解析 |
| **UI 風格** | 卡片式極簡現代風 | 類 ChatGPT 配置 |

**總結**：Open WebUI 是模型的大管家，而本專案是您在處理數據與報告時的「專門分析員」。
