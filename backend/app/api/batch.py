"""Batch Analysis API endpoints."""

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.models.batch import (
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    BatchAnalyzeResult,
)
from app.services.llm_service import llm_service
from app.utils.file_resolver import load_dataframe

router = APIRouter()


async def load_dataframe_async(file_path: str):
    """在 threadpool 中載入 DataFrame。

    pandas 的解析是阻塞式 CPU/IO 工作，直接在 `async def` 端點裡呼叫會卡住
    event loop（單一 worker 時整個服務都會被拖住）。
    """
    return await run_in_threadpool(load_dataframe, file_path)


DATA_DIR = Path("data")


@router.post("/analyze", response_model=BatchAnalyzeResponse)
async def analyze_batch(request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
    """Perform batch analysis on a dataset."""
    start_time = time.time()
    try:
        df = await load_dataframe_async(request.file_path)
        if df is None:
            raise HTTPException(
                status_code=404, detail=f"檔案未找到: {request.file_path}"
            )

        results = []

        groups = df.groupby(request.group_by_cols)

        for name, group_df in groups:
            group_label = " - ".join(
                [str(n) for n in (name if isinstance(name, tuple) else [name])]
            )

            # Simple aggregation for context
            agg_data = group_df[request.metric_cols].sum().to_dict()
            context = f"Group: {group_label}\nData: {agg_data}"

            # Call LLM for this group if in pairwise mode
            if request.analysis_mode == "pairwise":
                analysis = await llm_service.analyze_text(
                    text_content=context,
                    user_instruction=f"請分析以下數據組。幣別：{request.currency_unit}",
                    provider=request.config.provider,
                    model_name=request.config.model_name,
                )
                results.append(
                    BatchAnalyzeResult(
                        group_value=group_label,
                        analysis_text=analysis,
                        data_summary=agg_data,
                    )
                )
            else:
                # In consolidated mode, we just collect data first
                results.append(
                    BatchAnalyzeResult(
                        group_value=group_label,
                        analysis_text="Consolidated mode (details in main report)",
                        data_summary=agg_data,
                    )
                )

        consolidated_report = None
        if request.analysis_mode == "consolidated":
            all_groups_context = "\n".join(
                [f"{r.group_value}: {r.data_summary}" for r in results]
            )
            consolidated_report = await llm_service.analyze_text(
                text_content=all_groups_context,
                user_instruction=f"請彙總分析以下所有數據組。請特別注意趨勢與異常值。幣別：{request.currency_unit}",
                provider=request.config.provider,
                model_name=request.config.model_name,
            )

        return BatchAnalyzeResponse(
            results=results,
            consolidated_report=consolidated_report,
            execution_time=time.time() - start_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
