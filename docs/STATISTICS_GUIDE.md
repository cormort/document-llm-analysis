# 📊 統計分析功能說明手冊

本文件詳細說明系統中所有統計分析功能的技術棧、公式定義與使用情境。

---

## 🛠️ 技術棧 (Tech Stack)

| 類別 | 技術 | 用途 |
|------|------|------|
| 資料處理 | `pandas` | DataFrame 操作、資料清理、分組統計 |
| 數值計算 | `numpy` | 數學運算、陣列操作 |
| 統計檢定 | `scipy.stats` | T-Test、ANOVA、Shapiro-Wilk 常態性檢定 |
| 機器學習 | `sklearn` | 線性回歸、邏輯斯回歸、分類指標 |
| 視覺化 | `plotly` | 互動式圖表 (Heatmap、Box、Violin 等) |
| AI 解讀 | LLM Service | Gemini / OpenAI / Ollama 語意分析 |

---

## 📈 描述性統計 (Descriptive Statistics)

### 基本指標

| 指標 | 公式 | 說明 |
|------|------|------|
| **平均值 (Mean)** | $\bar{x} = \frac{1}{n}\sum_{i=1}^{n}x_i$ | 資料的中心趨勢 |
| **標準差 (Std)** | $\sigma = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(x_i - \bar{x})^2}$ | 資料的離散程度 |
| **中位數 (Median)** | 排序後第 50% 位置的值 | 對極端值較穩健 |
| **最小值/最大值** | $\min(x), \max(x)$ | 資料邊界 |

### 分佈形狀指標

| 指標 | 公式 | 解讀 |
|------|------|------|
| **偏度 (Skewness)** | $\gamma_1 = \frac{E[(X-\mu)^3]}{\sigma^3}$ | `>0` 右偏 (長尾在右), `<0` 左偏, `≈0` 對稱 |
| **峰度 (Kurtosis)** | $\gamma_2 = \frac{E[(X-\mu)^4]}{\sigma^4} - 3$ | `>0` 高狹峰 (尾部厚), `<0` 低闊峰 |

---

## 🔗 相關性分析 (Correlation)

### Pearson 相關係數

$$r = \frac{\sum_{i=1}^{n}(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^{n}(x_i - \bar{x})^2}\sqrt{\sum_{i=1}^{n}(y_i - \bar{y})^2}}$$

| 數值範圍 | 解讀 |
|----------|------|
| `0.8 ~ 1.0` | 強正相關 |
| `0.5 ~ 0.8` | 中度正相關 |
| `0.0 ~ 0.5` | 弱正相關 |
| `-0.5 ~ 0.0` | 弱負相關 |
| `-1.0 ~ -0.5` | 強負相關 |

---

## 🧪 推論統計 (Inferential Statistics)

### 1. 獨立樣本 T-檢定 (Independent Samples T-Test)

**用途**: 比較兩個獨立群體的平均值是否有顯著差異。

**公式**:
$$t = \frac{\bar{x}_1 - \bar{x}_2}{\sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}}$$

**判讀**:
- P-Value < 0.05 → 兩組有顯著差異
- P-Value ≥ 0.05 → 無法拒絕虛無假設 (兩組無顯著差異)

---

### 2. 單因子變異數分析 (One-Way ANOVA)

**用途**: 比較三個以上群體的平均值是否有顯著差異。

**公式**:
$$F = \frac{MS_{between}}{MS_{within}} = \frac{\frac{SS_{between}}{k-1}}{\frac{SS_{within}}{N-k}}$$

其中:
- $SS_{between}$ = 組間變異
- $SS_{within}$ = 組內變異
- $k$ = 組數
- $N$ = 總樣本數

**判讀**: P-Value < 0.05 表示至少有一組與其他組不同。

---

### 3. 線性回歸 (Linear Regression)

**用途**: 建立預測模型，分析自變數如何影響應變數。

**模型**:
$$Y = \beta_0 + \beta_1 X_1 + \beta_2 X_2 + ... + \epsilon$$

**評估指標**:

| 指標 | 公式 | 說明 |
|------|------|------|
| **R² (決定係數)** | $R^2 = 1 - \frac{SS_{res}}{SS_{tot}}$ | 模型解釋力 (0~1，越高越好) |
| **係數 (β)** | 最小平方法估計 | 正值=正向影響，負值=負向影響 |

---

### 4. 邏輯斯回歸 (Logistic Regression)

**用途**: 二元分類問題，預測事件發生機率。

**模型**:
$$P(Y=1|X) = \frac{1}{1 + e^{-(\beta_0 + \beta_1 X_1 + ...)}}$$

**評估指標**:

| 指標 | 公式 | 說明 |
|------|------|------|
| **準確率 (Accuracy)** | $\frac{TP + TN}{TP + TN + FP + FN}$ | 整體預測正確率 |
| **精確率 (Precision)** | $\frac{TP}{TP + FP}$ | 預測為正的準確度 |
| **召回率 (Recall)** | $\frac{TP}{TP + FN}$ | 實際為正的偵測率 |
| **F1-Score** | $2 \times \frac{Precision \times Recall}{Precision + Recall}$ | 精確率與召回率的調和平均 |

---

## 🔍 資料品質診斷

### 異常值偵測 (IQR Method)

**公式**:
- $Q_1$ = 第 25 百分位數
- $Q_3$ = 第 75 百分位數
- $IQR = Q_3 - Q_1$
- **下界** = $Q_1 - 1.5 \times IQR$
- **上界** = $Q_3 + 1.5 \times IQR$

超出上下界的資料點被視為異常值。

---

### 常態性檢定 (Shapiro-Wilk Test)

**用途**: 檢驗資料是否符合常態分佈 (許多統計方法的前提假設)。

**判讀**:
- P-Value > 0.05 → 資料符合常態分佈
- P-Value ≤ 0.05 → 資料顯著偏離常態分佈

---

## 🛠️ 變數轉換功能

### 基礎數學轉換

| 功能 | 公式 | 使用情境 |
|------|------|----------|
| **Log 轉換** | $\log(x+1)$ | 處理右偏資料，壓縮極端值 |
| **平方根** | $\sqrt{x}$ | 輕度右偏修正 |
| **平方** | $x^2$ | 放大差異 |
| **絕對值** | $|x|$ | 忽略正負號 |
| **排名** | $rank(x)$ | 消除極端值影響 |

---

### 標準化與正規化

| 功能 | 公式 | 結果範圍 |
|------|------|----------|
| **Z-Score** | $z = \frac{x - \mu}{\sigma}$ | 均值=0, 標準差=1 |
| **Min-Max** | $\frac{x - x_{min}}{x_{max} - x_{min}}$ | 0 ~ 1 |
| **百分位** | $\frac{rank(x)}{n} \times 100$ | 0 ~ 100 |
| **中心化** | $x - \mu$ | 均值=0 |

---

### 時間序列特徵

| 功能 | 公式 | 用途 |
|------|------|------|
| **滯後值 (Lag)** | $x_{t-n}$ | 捕捉時間延遲效應 |
| **滾動平均** | $\frac{1}{n}\sum_{i=0}^{n-1}x_{t-i}$ | 平滑趨勢 |
| **滾動標準差** | 滑動視窗內的標準差 | 衡量波動度 |
| **變動率** | $\frac{x_t - x_{t-1}}{x_{t-1}} \times 100\%$ | 成長率 |

---

### 類別編碼

| 功能 | 說明 | 範例 |
|------|------|------|
| **Label Encoding** | 類別 → 數字 | A→0, B→1, C→2 |
| **One-Hot Encoding** | 每類別一欄 | [1,0,0], [0,1,0], [0,0,1] |
| **頻率編碼** | 類別 → 出現頻率 | A(50%)→0.5, B(30%)→0.3 |

---

## 📖 參考資源

- [SciPy Statistics Documentation](https://docs.scipy.org/doc/scipy/reference/stats.html)
- [Scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html)
- [Plotly Python Documentation](https://plotly.com/python/)

---

*文件版本: 1.0 | 更新日期: 2025-12-23*
