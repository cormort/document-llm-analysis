"""LLM 產生程式碼的安全檢查（無副作用、可獨立測試）。

原本這些邏輯寫在 `app/api/query.py`，但該模組會匯入 LLM service 等重量級
依賴，導致安全檢查無法獨立測試。搬出來之後：

- `validate_code_safety` 可以在不載入 LLM SDK 的情況下單元測試
- `/api/query/execute` 之外的地方（例如背景 worker）也能重用

注意：這只是第一層防護。Python 的 `exec` 沒有真正的沙箱，
真正安全作法是不要把 LLM 產生的程式碼直接執行（改用 DuckDB SQL 流程）。
"""

import ast
import re

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
    r"\bopen\s*\(",    # 原本寫成 r"\bopen\s*([\"']"，括號未跳脫＝無效正則
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
    ast.AnnAssign,
    ast.Return,
    ast.If,
    ast.For,
    ast.While,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Call,
    ast.Attribute,
    ast.Name,
    ast.Constant,
    ast.List,
    ast.Dict,
    ast.Tuple,
    ast.Set,
    ast.Subscript,
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
    ast.comprehension,
    ast.NamedExpr,
    ast.Starred,
    ast.keyword,
    # 運算子與 expression context（`ast.Load`/`ast.Store`/`ast.Gt`…）等
    # 沒有行為的輔助節點
    ast.expr_context,
    ast.operator,
    ast.unaryop,
    ast.boolop,
    ast.cmpop,
)

# 明確禁止的語句（在黑名單正則之外，再用 AST 做一次結構性阻擋）
DISALLOWED_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.Delete,
    ast.With,
    ast.AsyncWith,
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Raise,
    ast.Try,
    ast.ExceptHandler,
    ast.Yield,
    ast.YieldFrom,
    ast.Await,
)

# 允許直接呼叫的內建函式（方法呼叫另由「屬性名稱不得以 _ 開頭」限制）
ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "len",
        "list",
        "max",
        "min",
        "range",
        "round",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
    }
)

# 檔案 IO 相關方法（可用於任意讀檔／寫檔／外洩資料）
DENIED_CALL_ATTRS: frozenset[str] = frozenset(
    {
        "to_csv",
        "to_excel",
        "to_json",
        "to_pickle",
        "to_sql",
        "to_parquet",
        "to_feather",
        "to_hdf",
        "to_orc",
        "to_stata",
        "to_clipboard",
        "to_gbq",
        "to_xml",
        "to_latex",
        "to_markdown",
        "to_html",
        "read_csv",
        "read_excel",
        "read_json",
        "read_pickle",
        "read_sql",
        "read_sql_query",
        "read_table",
        "read_html",
        "read_clipboard",
        "read_parquet",
        "read_orc",
        "read_feather",
        "read_hdf",
        "read_stata",
        "read_sas",
        "read_spss",
        "read_gbq",
        "read_xml",
        "read_fwf",
    }
)

MAX_CODE_LENGTH = 4000
MAX_AST_NODES = 400


def validate_code_safety(code: str) -> tuple[bool, str]:
    """驗證程式碼安全性，包含正則黑名單和 AST 白名單檢查。

    採取 fail-closed 策略：
    - 正則黑名單（快速阻擋明顯的危險字串）
    - AST 結構檢查：禁止 import / with / try / class / async 等語句
    - 禁止存取任何以 `_` 開頭的屬性（擋掉 `__class__`、`__globals__` 之類的逃逸）
    - 只允許呼叫白名單內的內建函式，或 DataFrame/模組上的公開方法
    """
    if not code or not code.strip():
        return False, "程式碼為空"
    if len(code) > MAX_CODE_LENGTH:
        return False, f"程式碼過長（上限 {MAX_CODE_LENGTH} 字元）"

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return False, f"禁止使用的程式碼模式: {pattern}"

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"語法錯誤: {e}"

    node_count = 0
    for node in ast.walk(tree):
        node_count += 1
        if node_count > MAX_AST_NODES:
            return False, f"程式碼過於複雜（節點數上限 {MAX_AST_NODES}）"

        # 1. 節點型別白名單（fail-closed：未列在白名單就拒絕）
        if not isinstance(node, ALLOWED_NODES):
            return False, f"不允許的語法: {type(node).__name__}"

        # 2. 明確禁止的語句（保險用，正常已被上面的白名單擋下）
        if isinstance(node, DISALLOWED_NODES):
            return False, f"不允許的語句: {type(node).__name__}"

        # 3. 禁止私有/魔術屬性與名稱（沙箱逃逸的主要途徑）
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return False, f"不允許存取私有屬性: {node.attr}"
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return False, f"不允許使用名稱: {node.id}"

        # 4. 呼叫限制
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id not in ALLOWED_CALL_NAMES:
                    return False, f"不允許呼叫函式: {func.id}"
            elif isinstance(func, ast.Attribute):
                if func.attr.startswith("_"):
                    return False, f"不允許呼叫方法: {func.attr}"
                if func.attr in DENIED_CALL_ATTRS:
                    return False, f"不允許呼叫檔案 IO 方法: {func.attr}"
            else:
                return False, "不允許的呼叫形式"

    return True, ""
