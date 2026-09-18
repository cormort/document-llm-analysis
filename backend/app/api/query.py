"""Data Query API endpoints for executing and interpreting Pandas queries."""

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pandas as pd
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.models.query import QueryExecuteRequest, QueryExecuteResponse
from app.services.llm_service import llm_service
from app.utils.code_safety import validate_code_safety
from app.utils.file_resolver import resolve_data_file

logger = logging.getLogger(__name__)

router = APIRouter()

EXECUTION_TIMEOUT_SECONDS = 10


@router.post("/execute", response_model=QueryExecuteResponse)
async def execute_query(request: QueryExecuteRequest) -> QueryExecuteResponse:
    """Execute generated Pandas code on a local file with safety checks."""
    try:
        is_safe, error_msg = validate_code_safety(request.pandas_code)
        if not is_safe:
            return QueryExecuteResponse(
                success=False, error=f"安全檢查失敗: {error_msg}"
            )

        file_path = resolve_data_file(request.file_path)

        if file_path is None:
            return QueryExecuteResponse(
                success=False, error=f"檔案未找到: {request.file_path}"
            )

        if file_path.suffix.lower() == ".csv":
            df = await run_in_threadpool(pd.read_csv, file_path)
        elif file_path.suffix.lower() in [".xls", ".xlsx"]:
            df = await run_in_threadpool(pd.read_excel, file_path)
        else:
            return QueryExecuteResponse(success=False, error="不支援的文件格式")

        def execute_code():
            exec_globals = {"pd": pd, "df": df, "result": None}

            try:
                # 注意：`exec` 不是真正的沙箱，validate_code_safety 只是
                # 第一層防護。此端點必須搭配認證使用（見 app/api/deps.py），
                # 且生產環境建議改用 /api/query/nl-to-sql（DuckDB）流程。
                exec(request.pandas_code, {"__builtins__": {}}, exec_globals)
                return exec_globals.get("result")
            except Exception as e:
                raise RuntimeError(f"執行錯誤: {type(e).__name__}: {e}") from e

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(execute_code)
            result = future.result(timeout=EXECUTION_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            # 注意：ThreadPoolExecutor 無法真正中止執行中的執行緒，
            # shutdown(wait=False) 只是不再等待；惡意/無窮迴圈的程式碼
            # 仍會佔用一個執行緒直到它自己結束。
            return QueryExecuteResponse(
                success=False,
                error=f"執行超時（超過 {EXECUTION_TIMEOUT_SECONDS} 秒），已放棄等待",
            )
        except Exception as e:
            logger.warning("查詢執行失敗", exc_info=e)
            return QueryExecuteResponse(success=False, error=str(e))
        finally:
            executor.shutdown(wait=False)

        if result is None:
            return QueryExecuteResponse(
                success=False,
                error="執行成功但未產生結果 (變數 'result' 未定義)",
            )

        if isinstance(result, pd.DataFrame):
            return QueryExecuteResponse(
                success=True,
                data=result.head(100).to_dict(orient="records"),
                summary=f"找到 {len(result)} 筆結果",
            )
        elif isinstance(result, pd.Series):
            return QueryExecuteResponse(
                success=True,
                data=result.head(100).to_frame().to_dict(orient="records"),
                summary=f"Result count: {len(result)}",
            )
        else:
            return QueryExecuteResponse(
                success=True, data=[{"value": str(result)}], summary="運算結果"
            )

    except Exception as exec_err:
        logger.exception("查詢端點未預期的錯誤")
        return QueryExecuteResponse(
            success=False, error=f"Python 執行錯誤: {type(exec_err).__name__}"
        )


@router.post("/interpret")
async def interpret_results(request: dict[str, str | dict[str, str | None]]):
    """Interpret the results of a query execution using LLM."""
    try:
        question = request.get("question")
        summary = request.get("data_summary")
        sample = request.get("data_sample")
        config = request.get("config", {})

        prompt = f"問題: {question}\n數據摘要: {summary}\n數據樣例: {sample}\n\n請根據以上數據回答原問題，並提供簡短的觀察結果。"

        content = await llm_service.analyze_text(
            text_content=prompt,
            user_instruction="您是一位數據分析專家，請根據提供的數據執行結果與問題進行解讀。",
            provider=config.get("provider", "Local (LM Studio)"),
            model_name=config.get("model_name", "qwen2.5-7b-instruct"),
            local_url=config.get("local_url", "http://localhost:1234/v1"),
            api_key=config.get("api_key"),
        )
        return {"interpretation": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
