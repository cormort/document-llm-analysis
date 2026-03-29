"""
AI interpretation utilities for statistical analysis.

This module provides unified AI interpretation functions that can be used
across different statistical analysis contexts.
"""

import pandas as pd
from app.services.llm_service import llm_service


async def interpret_diagnostics(
    descriptive_stats: pd.DataFrame,
    quality_report: pd.DataFrame | None,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI interpretation for data diagnostics.
    """
    MAX_ROWS = 20
    MAX_COLS = 15

    stats_df = descriptive_stats
    if len(stats_df) > MAX_ROWS:
        stats_df = stats_df.iloc[:MAX_ROWS]
    if len(stats_df.columns) > MAX_COLS:
        stats_df = stats_df.iloc[:, :MAX_COLS]

    stats_str = stats_df.to_markdown()

    if quality_report is not None:
        quality_df = quality_report
        if len(quality_df) > MAX_ROWS:
            quality_df = quality_df.iloc[:MAX_ROWS]
        quality_str = quality_df.to_markdown()
    else:
        quality_str = "N/A"

    note = (
        f"(註：為避免超過上下文上限，僅顯示前 {MAX_ROWS} 筆數據與前 {MAX_COLS} 個欄位)"
    )

    prompt = f"""請針對以下描述性統計與資料品質診斷結果進行深度分析 {note}：
【基礎統計】
{stats_str}
【品質報告摘要】
{quality_str}

請提供以下面向的解讀（使用繁體中文，專業且具洞察力）：
1. **📌 資料品質評估**：檢查是否存在嚴重的缺失值或異常值。
2. **📈 分佈特徵解讀**：根據 Skewness（偏度）與 Kurtosis（峰度）判斷分佈特性。
3. **⚠️ 潛在風險**：指出哪些欄位與業務邏輯可能存在的數據風險。
4. **💡 統計意涵與政策建議**：這些分佈特徵對於決策有何啟發？

請使用 Markdown 格式輸出。"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def interpret_correlation(
    corr_matrix: pd.DataFrame,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """Generate AI interpretation for correlation matrix."""
    MAX_DIM = 12

    truncated_matrix = corr_matrix.iloc[:MAX_DIM, :MAX_DIM]
    corr_str = truncated_matrix.to_markdown()

    note = (
        f"(註：為避免超過 Token 上限，僅顯示前 {MAX_DIM}x{MAX_DIM} 的矩陣切片)"
        if (len(corr_matrix) > MAX_DIM or len(corr_matrix.columns) > MAX_DIM)
        else ""
    )

    prompt = f"""請針對以下變數相關性矩陣進行專業解讀 {note}：

{corr_str}

請分析：
1. **核心正相關**：哪些變數呈現強烈連動？
2. **顯著負相關**：是否存在消長關係？
3. **隱藏關聯**：是否有出乎意料的弱相關或強相關？
4. **決策建議**：這對資源分配或重點關注對象有何啟示？
5. **變數選擇建議 (重要)**：若要進行「線性回歸」或「邏輯斯回歸」，
根據相關性，建議優先將哪些變數納入模型？
哪些變數因共線性太高(彼此太像)應該排除？

請用繁體中文回覆。"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def interpret_chart(
    chart_type: str,
    used_cols: list[str],
    data_summary: str,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI interpretation for chart analysis.
    """

    instruction = (
        "請從『計畫成本效益』與『政府財政負擔審查者』的觀點，"
        "針對此統計資料提供關鍵發現、成因洞察、政策與營運建議（含財政衝擊評估）、"
        "具體後續行動方案，以及「延伸分析建議與資料需求」。"
    )

    # Aggressive limit: 1500 chars (approx 500-1000 tokens)
    LIMIT_CHARS = 1500
    truncated_summary = (
        data_summary[:LIMIT_CHARS] + "...(truncated)"
        if len(data_summary) > LIMIT_CHARS
        else data_summary
    )

    results_summary = (
        f"分析類型: {chart_type}\n欄位資訊: {used_cols}\n數據摘要:\n{truncated_summary}"
    )

    return await llm_service.analyze_text(
        text_content=results_summary,
        user_instruction=instruction,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def interpret_groupby(
    group_col: str,
    target_col: str,
    result_df: pd.DataFrame,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI interpretation for group-by analysis.
    """

    # Truncate results to top 20 rows
    truncated_df = result_df.head(20)
    result_str = truncated_df.to_markdown()
    note = "(僅顯示前20筆數據)" if len(result_df) > 20 else ""

    prompt = f"""分組：{group_col}
目標：{target_col}
結果 {note}：
{result_str}

請分析領先/落後組別、差距原因與改善政策 (繁體中文)。"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def interpret_prophet(
    time_col: str,
    value_col: str,
    forecast_periods: int,
    forecast_df: pd.DataFrame,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI interpretation for Prophet time series forecast.

    Args:
        time_col: Time column name
        value_col: Value column name
        forecast_periods: Number of forecast periods
        forecast_df: Forecast result DataFrame
        provider: LLM provider name
        model_name: Model identifier
        local_url: Local LLM URL
        api_key: Optional API key
        context_window: Context window size

    Returns:
        AI-generated interpretation
    """

    forecast_str = (
        forecast_df[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        .tail(forecast_periods)
        .to_markdown()
    )

    prompt = f"""請針對以下時間序列預測結果進行專業解讀：
時間欄位: {time_col}
數值欄位: {value_col}
預測期數: {forecast_periods}

預測數據 (未來 {forecast_periods} 期):
{forecast_str}

請分析：
1. **主要趨勢**：未來 {forecast_periods} 期的整體趨勢如何？
2. **季節性/週期性**：是否存在明顯的季節性或週期性模式？
3. **不確定性**：信賴區間的寬度代表什麼？
4. **決策建議**：這些預測結果對業務或政策制定有何啟示？

請用繁體中文回覆。"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def interpret_field_implications(
    field_name: str,
    stats_info: dict,
    sample_values: list,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI interpretation for single field implications.
    """

    prompt = f"""請針對單一欄位「{field_name}」進行深入的政策與業務意涵分析。

【欄位統計資訊】
- 平均值 (Mean): {stats_info.get("mean")}
- 中位數 (Median): {stats_info.get("median")}
- 標準差 (Std): {stats_info.get("std")}
- 偏度 (Skewness): {stats_info.get("skewness")} ({"右偏/長尾" if stats_info.get("skewness", 0) > 0 else "左偏/負偏"})
- 峰度 (Kurtosis): {stats_info.get("kurtosis")}
- 樣本值範例: {sample_values}

請扮演「資深政策分析師」或「商業策略顧問」，回答以下問題 (繁體中文)：
1. **📊 數據型態解讀**：這個欄位的分佈型態代表什麼現實意義？(例如：高度右偏可能代表貧富不均、極端值效應)
2. **🏢 業務/政策意涵**：針對此指標的表現，反映了什麼樣的現況或問題？
3. **⚠️ 風險與機會**：是否有異常集中的極端值需要特別關注？或是分佈過於分散導致管理困難？
4. **🎯 行動建議**：管理者應該制定什麼樣的 KPI 或政策來優化此指標？
"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def suggest_feature_engineering(
    df_schema: str,
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI suggestions for feature engineering.
    """

    prompt = f"""你是一位精通數據挖掘與特徵工程的資料科學家。請根據以下目前的資料表欄位清單，建議 3-5 個「更有分析價值的新欄位」(衍生變數)。

【現有欄位清單】
{df_schema}

請思考：
- 如何組合現有欄位來產生新的 KPI？ (例如：效率 = 產出 / 投入、人均值 = 總量 / 人數、成長率、佔比等)
- 哪些轉換能讓分析更具深度？ (例如：日期轉為「是否週末」、「季節」、數值分箱級距)

請輸出建議格式：
1. **建議新欄位名稱** (例如：`Efficiency_Score`)
2. **計算邏輯** (例如：`Output / Input`)
3. **分析價值** (為什麼這個新欄位比原欄位更有意義？)

請用繁體中文回覆。
"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )


async def interpret_dataset_holistically(
    columns_stats: list[dict],
    provider: str,
    model_name: str,
    local_url: str,
    api_key: str | None = None,
    context_window: int = 16384,
) -> str:
    """
    Generate AI holistic analysis for the dataset based on multiple fields.
    """

    # Format the stats for the prompt
    stats_text = ""
    for col in columns_stats:
        stats_text += f"""
### 欄位：{col.get("name")}
- 平均值: {col.get("mean")}
- 標準差: {col.get("std")}
- 偏度: {col.get("skewness")}
- 峰度: {col.get("kurtosis")}
- 範例值: {col.get("sample_values")}
"""

    prompt = f"""請針對這份資料集的關鍵欄位進行「全域性 (Holistic) 綜合分析」。我們不只看單一欄位，而是要找出這些變數組合背後的整體故事。

【資料集關鍵欄位摘要】
{stats_text}

請扮演「資深資料科學家」或「高階策略顧問」，提供一份宏觀的分析報告 (繁體中文)：

1.  **🔗 跨欄位關聯與模式 (Cross-Field Patterns)**：
    這些欄位放在一起看，呈現出什麼樣的系統性特徵？(例如：若 A 欄位高變異且 B 欄位呈現極端值，是否暗示某種不穩定性？)

2.  **🧩 整體結構洞察 (Structural Insights)**：
    資料是呈現常態分佈、還是在某些區間呈現極端集中？這代表此業務/現象的本質為何？(例如：是「常態運作」還是「極端事件驅動」？)

3.  **🚩 系統性風險與異常 (Systemic Risks)**：
    是否有「多個指標同時亮紅燈」的情況？或者某些欄位的組合顯示出潛在的結構性問題？

4.  **🚀 綜合策略建議 (Strategic Recommendations)**：
    基於這些變數的共同表現，管理者應該採取什麼樣的整體策略？(而非針對單一欄位的微調)

請用 Markdown 格式輸出，語氣專業且具啟發性。
"""

    return await llm_service.analyze_text(
        text_content="",
        user_instruction=prompt,
        provider=provider,
        model_name=model_name,
        local_url=local_url,
        context_window=context_window,
        api_key=api_key,
    )
