# 使用者管理與行為追蹤系統實作計劃

## 目標
為 document-llm-analysis 專案新增完整的使用者管理系統（註冊、登入、登出、用戶管理）以及按鈕點擊行為追蹤功能。

## 技術決策
- **認證方式**: JWT (無狀態、易擴展)
- **資料庫**: SQLite (輕量級、無需額外安裝)
- **功能範圍**: 完整功能（註冊、登入、登出、用戶列表、權限管理、行為追蹤）

## 架構概覽

### 後端 (FastAPI + SQLite)
```
backend/app/
├── models/
│   ├── user.py          # 使用者資料模型
│   └── analytics.py     # 行為追蹤資料模型
├── api/
│   ├── auth.py          # 認證 API (登入/註冊/登出)
│   ├── users.py         # 用戶管理 API
│   └── analytics.py     # 行為追蹤 API
├── core/
│   ├── security.py      # JWT、密碼雜湊
│   └── database.py      # SQLite 連線
└── services/
    └── user_service.py  # 用戶業務邏輯
```

### 前端 (Next.js + Zustand)
```
frontend/src/
├── stores/
│   ├── auth-store.ts    # 認證狀態管理
│   └── analytics-store.ts # 行為追蹤狀態
├── hooks/
│   └── useAnalytics.ts  # 行為追蹤 Hook
├── components/
│   └── auth/
│       ├── LoginForm.tsx
│       ├── RegisterForm.tsx
│       └── UserManagement.tsx
└── app/
    ├── login/page.tsx
    ├── register/page.tsx
    └── admin/users/page.tsx
```

## 實作階段

### Phase 1: 後端資料庫與模型 (預計 30 分鐘)
- [ ] 1.1 建立 SQLite 資料庫連線模組
- [ ] 1.2 建立使用者資料模型 (User model)
- [ ] 1.3 建立行為追蹤資料模型 (AnalyticsEvent model)
- [ ] 1.4 建立資料庫初始化腳本

### Phase 2: 後端認證系統 (預計 45 分鐘)
- [ ] 2.1 實作密碼雜湊與驗證 (bcrypt)
- [ ] 2.2 實作 JWT token 生成與驗證
- [ ] 2.3 建立 /api/auth/register 端點
- [ ] 2.4 建立 /api/auth/login 端點
- [ ] 2.5 建立 /api/auth/logout 端點
- [ ] 2.6 建立 /api/auth/me 端點 (取得當前用戶)
- [ ] 2.7 建立 JWT 驗證中介軟體/依賴

### Phase 3: 後端用戶管理 API (預計 30 分鐘)
- [ ] 3.1 建立 /api/users 端點 (列表，需管理員權限)
- [ ] 3.2 建立 /api/users/:id 端點 (查詢/更新/刪除)
- [ ] 3.3 實作權限檢查裝飾器

### Phase 4: 後端行為追蹤 API (預計 30 分鐘)
- [ ] 4.1 建立 /api/analytics/track 端點 (記錄事件)
- [ ] 4.2 建立 /api/analytics/stats 端點 (統計報表)
- [ ] 4.3 建立 /api/analytics/events 端點 (事件列表)
- [ ] 4.4 實作事件聚合查詢 (按按鈕、按用戶、按時間)

### Phase 5: 前端認證狀態管理 (預計 30 分鐘)
- [ ] 5.1 建立 auth-store.ts (Zustand)
- [ ] 5.2 建立 login API 客戶端函數
- [ ] 5.3 建立 register API 客戶端函數
- [ ] 5.4 建立 token 儲存 (localStorage)
- [ ] 5.5 建立 Axios 攔截器 (自動帶入 token)

### Phase 6: 前端登入/註冊頁面 (預計 30 分鐘)
- [ ] 6.1 建立 /login 頁面
- [ ] 6.2 建立 /register 頁面
- [ ] 6.3 更新 Sidebar 顯示登入狀態
- [ ] 6.4 實作保護路由 (需登入才能訪問)

### Phase 7: 前端行為追蹤系統 (預計 30 分鐘)
- [ ] 7.1 建立 useAnalytics Hook
- [ ] 7.2 建立 trackClick 函數
- [ ] 7.3 在所有按鈕添加追蹤
- [ ] 7.4 建立 analytics-store.ts

### Phase 8: 用戶管理後台頁面 (預計 30 分鐘)
- [ ] 8.1 建立 /admin/users 頁面
- [ ] 8.2 實作用戶列表表格
- [ ] 8.3 實作用戶編輯/刪除功能
- [ ] 8.4 建立 /admin/analytics 頁面 (行為報表)

### Phase 9: 測試與整合 (預計 30 分鐘)
- [ ] 9.1 後端 API 測試
- [ ] 9.2 前端整合測試
- [ ] 9.3 驗證權限控制
- [ ] 9.4 驗證行為追蹤記錄

## 錯誤記錄
| 錯誤 | 嘗試次數 | 解決方式 |
|------|---------|---------|
| - | - | - |

## 相依套件
### 後端 (已存在)
- python-jose[cryptography] - JWT 處理
- passlib[bcrypt] - 密碼雜湊
- sqlalchemy - ORM

### 前端 (已存在)
- zustand - 狀態管理
- @tanstack/react-query - 資料抓取

## 安全考量
- 密碼使用 bcrypt 雜湊 (work factor 12)
- JWT 使用 HS256 簽名
- Token 有效期 24 小時
- 敏感操作需管理員權限
- CORS 配置保持現有設置
