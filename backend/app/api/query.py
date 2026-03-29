"""Data Query API endpoints for executing and interpreting Pandas queries."""

import ast
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.models.query import QueryExecuteRequest, QueryExecuteResponse
from app.services.llm_service import llm_service
from app.utils.file_resolver import resolve_data_file

router = APIRouter()

EXECUTION_TIMEOUT_SECONDS = 10

FORBIDDEN_PATTERNS = [
    r"\bimport\s+os\b",
    r"\bimport\s+subprocess\b",
    r"\bimport\s+sys\b",
    r"\bimport\s+shutil\b",
    r"\bimport\s+socket\b",
    r"\b__import__\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bcompile\s*\(",
    r"\bopen\s*([\"']",
    r"\.system\s*\(",
    r"\.popen\s*\(",
    r"\.spawn\s*\(",
    r"\bgetattr\s*\(",
    r"\bsetattr\s*\(",
    r"\bdelattr\s*\(",
    r"\b__class__\b",
    r"\b__base__\b",
    r"\b__mro__\b",
    r"\b__subclasses__\b",
    r"\b__globals__\b",
    r"\b__code__\b",
    r"\b__builtins__\b",
    r"\b__dict__\b",
    r"\blocals\s*\(",
    r"\bglobals\s*\(",
    r"\bvars\s*\(",
    r"\bdir\s*\(",
    r"\btype\s*\(",
    r"\binput\s*\(",
    r"\bbreakpoint\s*\(",
]

ALLOWED_NODES = (
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AugAssign,
    ast.Return,
    ast.If,
    ast.For,
    ast.While,
    ast.With,
    ast.FunctionDef,
    ast.Call,
    ast.Attribute,
    ast.Name,
    ast.Constant,
    ast.List,
    ast.Dict,
    ast.Tuple,
    ast.Set,
    ast.Subscript,
    ast.Index,
    ast.Slice,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Lambda,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    ast.GeneratorExp,
    ast.NamedExpr,
)


def validate_code_safety(code: str) -> tuple[bool, str]:
    """驗證程式碼安全性，包含正則黑名單和 AST 白名單檢查。"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return False, f"禁止使用的程式碼模式: {pattern}"

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"語法錯誤: {e}"

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "不允許的 import 語句"
            if isinstance(node, ast.Global):
                return False, "不允許的 global 語句"
            if isinstance(node, ast.Nonlocal):
                return False, "不允許的 nonlocal 語句"
            if isinstance(node, (ast.Delete, ast.Del)):
                return False, "不允許的 del 語句"

    return True, ""


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
            df = pd.read_csv(file_path)
        elif file_path.suffix.lower() in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path)
        else:
            return QueryExecuteResponse(success=False, error="不支援的文件格式")

        def execute_code():
            exec_globals = {"pd": pd, "df": df, "result": None}
            exec_globals_copy = exec_globals.copy()

            try:
                exec(request.pandas_code, {"__builtins__": {}}, exec_globals_copy)
                result = exec_globals_copy.get("result")

                if result is None:
                    try:
                        result = eval(
                            request.pandas_code,
                            {"__builtins__": {}},
                            {"pd": pd, "df": df},
                        )
                    except Exception:
                        return None

                return result
            except Exception as e:
                raise RuntimeError(f"執行錯誤: {str(e)}") from e

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(execute_code)
            result = future.result(timeout=EXECUTION_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            return QueryExecuteResponse(
                success=False, error=f"執行超時（超過 {EXECUTION_TIMEOUT_SECONDS} 秒）"
            )
        except Exception as e:
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
                data=result.to_frame().to_dict(orient="records"),
                summary=f"Result count: {len(result)}",
            )
        else:
            return QueryExecuteResponse(
                success=True, data=[{"value": str(result)}], summary="運算結果"
            )

    except Exception as exec_err:
        return QueryExecuteResponse(
            success=False, error=f"Python 執行錯誤: {str(exec_err)}"
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
