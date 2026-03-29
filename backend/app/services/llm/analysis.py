"""
Analysis Prompts and Content Processing
Handles prompt building, content extraction, and token estimation for analysis tasks.
"""

import os
from typing import Any

import structlog

from app.services.document_service import document_service
from app.services.llm.token_utils import estimate_tokens_heuristic

logger = structlog.get_logger()


class AnalysisPrompts:
    """Builds and manages analysis prompts."""

    STRATEGY_TOOLKIT = {
        "🌱 創業/導入期": {
            "核心目標": "存活、驗證商業模式、尋找產品市場契合度 (PMF)",
            "主要挑戰": "資源有限、市場認知度低、高度不確定性",
            "關鍵工具": [
                "精實畫布 (Lean Canvas)",
                "早期優勢分析 (Early Advantage)",
                "市場吸引力評估",
            ],
        },
        "🚀 成長期": {
            "核心目標": "有效擴張規模、爭奪市場份額、建立品牌與競爭護城河",
            "主要挑戰": "管理擴張複雜性、應對激烈競爭、保持高速成長",
            "關鍵工具": [
                "Ansoff 矩陣",
                "波特五力分析",
                "BCG 矩陣",
                "成本優勢與定價策略",
            ],
        },
        "🌳 成熟期": {
            "核心目標": "維持利潤與市佔率、提升效率、尋找新成長動能",
            "主要挑戰": "應對激烈競爭、管理客戶關係、克服組織僵化",
            "關鍵工具": [
                "競爭強度監控",
                "波特基本競爭策略",
                "核心資源持續性評估",
                "金牛事業管理",
            ],
        },
        "🍂 衰退/轉型期": {
            "核心目標": "優雅退出或尋找「第二曲線」實現轉型",
            "主要挑戰": "決策退出 vs. 轉型、重新配置資源、管理變革阻力",
            "關鍵工具": ["退出與轉型評估", "產品/市場組合重組", "資源盤點與新資源規劃"],
        },
    }

    @staticmethod
    def build(
        user_instruction: str,
        file_name: str = "",
        content: str = "",
        financial_skepticism: bool = False,
    ) -> tuple[str, str]:
        """Build system and user prompts for analysis.

        Args:
            user_instruction: The user's analysis instruction.
            file_name: Name of the file being analyzed.
            content: Extracted file content.
            financial_skepticism: Whether to use critical analysis mode.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        system_prompt = f"""你是一位精通財務報表與數據分析的資深研究員。請根據提供的文件內容，精準回答使用者的問題。

**重要規則 - 必須標註資料出處：**
1. 引用任何數據、金額、百分比時，必須標註來源：`[來源: {file_name}, 第X頁]` 或 `[來源: {file_name}, 表格X]`
2. 如果無法確定頁碼，使用：`[來源: {file_name}]`
3. 直接引用原文時使用引號並標註來源
4. 確保每個重要論點都有對應的來源支持

**輸出格式：**
- 使用 Markdown 格式
- 數據和論點需附來源標註
- 在報告結尾可加入「參考來源」章節彙整所有引用"""

        if (
            financial_skepticism
            or "審慎質疑" in user_instruction
            or "財政審查" in user_instruction
        ):
            system_prompt = f"""【⚠️ 執行規範：極度審慎財政評估】
你現在是「資深獨立財務分析師」，請以「極度審慎 (Extreme Professional Skepticism)」的角度穿透並質疑此計畫。
你的任務是揪出計畫中所有「過度樂觀」與「不切實際」的假設。請進行犀利且毫不留情的專業解構：
1. **邏輯死穴診斷**：強制找出計畫手段與核心目標間的「致命脫節」。如果手段無法保證目標達成，請直接判定為「邏輯崩潰」。
2. **財務真實性揭穿**：質疑 NPV/IRR 背後是否有數據美化（Window Dressing）？強制要求列出 3 個可能導致預算徹底沈沒的財務引爆點。
3. **替代方案壓制**：強制證明目前方案在成本效益上是否「顯著劣於」其他潛在替代方案，並指出為何選擇此劣等路徑。
4. **資源誤配置警告**：以最高權重評估機會成本。這份預算是否在「浪費」社會資源？
5. **💀 致命風險掃描**：明確、冷酷地列出讓此計畫走向失敗的 3 個根本性缺陷。若內容空泛，請直接批評其「缺乏執行科學」。

⚠️ **必須標註資料出處**：所有引用的數據必須標註 `[來源: {file_name}, 第X頁]`

語氣必須冷靜、專業、具穿透力且極端尖銳。你的回答應讓決策者感受到第三方專業評估的壓力。"""

        user_prompt = f"""【使用者指令】：{user_instruction}

=== 文件內容 ({file_name}) ===
{content}
=== 結束 ===

請依據內容進行分析，並在引用數據時標註來源。"""

        return system_prompt, user_prompt

    @staticmethod
    async def estimate_tokens(
        file_path: str | None = None,
        text_content: str | None = None,
        instruction: str = "",
        context_window: int = 4096,
        financial_skepticism: bool = False,
    ) -> dict[str, Any]:
        """Estimate token counts for an analysis request.

        Args:
            file_path: Path to file to analyze.
            text_content: Direct text content.
            instruction: User instruction.
            context_window: Model context window size.
            financial_skepticism: Whether critical analysis mode is enabled.

        Returns:
            Dict with token breakdown and context fit info.
        """
        content = ""
        if file_path:
            content = await document_service.extract_text(file_path)
        elif text_content:
            content = text_content

        original_len = len(content)
        truncated = False

        reserved_tokens = 2000
        available_tokens = max(context_window - reserved_tokens, 1000)
        max_chars = int(available_tokens * 1.0)

        if len(content) > max_chars:
            truncated = True
            content = (
                content[:max_chars]
                + f"\n\n...(內容已截斷至 {max_chars} 字元以符合模型限制 {context_window})..."
            )

        file_name = os.path.basename(file_path) if file_path else "text_input"
        system_prompt, user_prompt = AnalysisPrompts.build(
            user_instruction=instruction,
            file_name=file_name,
            content=content,
            financial_skepticism=financial_skepticism,
        )

        system_tokens = estimate_tokens_heuristic(system_prompt)
        content_tokens = estimate_tokens_heuristic(content)
        user_prompt_tokens = estimate_tokens_heuristic(user_prompt)
        total_tokens = system_tokens + user_prompt_tokens

        return {
            "system_prompt_tokens": system_tokens,
            "content_tokens": content_tokens,
            "user_prompt_tokens": user_prompt_tokens,
            "total_tokens": total_tokens,
            "context_window": context_window,
            "fits_in_context": total_tokens < context_window,
            "content_chars": original_len,
            "truncated": truncated,
        }
