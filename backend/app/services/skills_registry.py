from dataclasses import dataclass

@dataclass
class Skill:
    id: str
    name: str
    description: str
    prompt_fragment: str
    icon: str = "🧠"
    category: str = "通用"

# Define available skills
SKILLS: dict[str, Skill] = {
    "finance_audit": Skill(
        id="finance_audit",
        name="📊 財務稽核 (Finance Auditor)",
        category="財務",
        icon="📊",
        description="深度財務審查，包含 NPV/IRR 驗算、折現率合理性評估與現金流敏感度分析。",
        prompt_fragment="""
### 📊 專家技能：財務稽核 (Finance Audit Scrutiny)
請以資深財務稽核員的立場，對專案的財務假設進行「嚴謹審查」：

**A. NPV (淨現值) 分析**：
- 評估計畫採用的折現率是否合理（與當前利率環境及計畫風險相符）
- 檢視現金流量預估的假設是否保守或樂觀
- NPV 結果對關鍵參數變動的敏感度分析

**B. IRR (內部報酬率) 評估**：
- IRR 是否高於資金成本或政府要求的最高報酬率
- 與同類型計畫的 IRR 比較是否合理
- IRR 計算是否存在多重解或無解的風險

**C. 回收年期 (Payback Period) 檢視**：
- 回收年期是否在合理範圍內（與計畫性質、產業特性相符）
- 是否採用折現回收年期以反映資金時間價值

**D. 營運年期收支評估**：
- 營運期間收入預估的依據與合理性（市場規模、價格假設、成長率）
- 營運成本與維護費用的完整性（是否遺漏隱藏成本）

**E. 最終判定**：基於財務面給出明確的建議、需補充資料或不建議推動之理由。
"""
    ),
    "strategy_consultant": Skill(
        id="strategy_consultant",
        name="🧩 策略諮詢 (Strategy Consultant)",
        category="管理",
        icon="🧩",
        description="應用商業生命週期、PESTEL、SWOT 與 Ansoff 矩陣進行宏觀策略分析。",
        prompt_fragment="""
### 🧩 專家技能：策略諮詢 (Strategy Contextualization)
請運用專業策略工具與框架進行深度解讀：
1. **框架應用**：主動選取適用工具進行分析。
   - **PESTEL**：分析政策/市場的外部宏觀環境。
   - **Ansoff / SWOT**：分析擴張方向或現狀競爭優勢。
   - **商業生命週期**：判斷目前專案處於哪個發展階段（啟動、成長、成熟或轉型期）。
2. **策略高度**：不僅描述現狀，更要給出對未來規劃有具體引導性的對策建議。
"""
    ),
    "kpi_analyst": Skill(
        id="kpi_analyst",
        name="📈 KPI 診斷 (KPI Analyst)",
        category="管理",
        icon="📈",
        description="評估績效指標 (KPI) 的設計品質，分析目標與手段的邏輯對應性。",
        prompt_fragment="""
### 📈 專家技能：KPI 診斷 (Performance Indicator Evaluation)
請針對計畫所訂定的績效指標進行嚴格評估：
1. **SMART 原則檢視**：指標是否具體(Specific)、可衡量(Measurable)、可達成(Achievable)、相關(Relevant)、有時限(Time-bound)？
2. **KPI 與目標對應性**：列出核心目標與對應指標，評估是否能直接反映目標達成程度，指出「斷鍵」或「錯位」情形。
3. **品質評估**：是否兼顧領先指標（前瞻性）與落後指標（結果性）？
4. **古德哈特定律風險**：是否存在「為達標而扭曲行為」的風險？
5. **優化建議**：提出更能反映核心價值的替代性指標或監測機制。
"""
    ),
    "logical_integrity": Skill(
        id="logical_integrity",
        name="🛡️ 邏輯完整性 (Logical Integrity)",
        category="分析",
        icon="🛡️",
        description="偵測資訊缺口、因果邏輯斷層與各章節數據的一致性。",
        prompt_fragment="""
### 🛡️ 專家技能：邏輯完整性稽查 (Logical & Evidence Audit)
請擔任嚴格的邏輯審查員，找出文件中的瑕疵：

**A. 不合理之處（邏輯問題）**：
- 檢視因果邏輯是否完整（投入→產出→成果的推論是否合理）
- 偵測數據矛盾（前後數字有無衝突）
- 識別過於樂觀或缺乏依據的假設

**B. 資訊不足或缺漏項目**：
- 明確指出當前資料中哪些關鍵數據「缺漏」，導致無法下結論。
- 列出包含背景說明、預算細項、利害關係人分析等應補強之清單。

**C. 需進一步釐清的疑慮**：
- 以問題清單形式列出需要主辦機關進一步回應、質疑或說明的核心事項。
"""
    ),
    "policy_compliance": Skill(
        id="policy_compliance",
        name="⚖️ 政策合規 (Policy Compliance)",
        category="法律",
        icon="⚖️",
        description="檢查專案內容是否符合法律法規、政府政策指導原則與社會合規性。",
        prompt_fragment="""
### ⚖️ 專家技能：政策合規與社會影響 (Policy & Social Alignment)
請針對政策法規面進行審查：
1. **法規風險**：評估專案內容是否有違反現行法規或程序之疑慮。
2. **政策一致性**：分析該計畫是否符合政府的長期發展方向（如：淨零排放、數位轉型等）。
3. **社會責任與公平性**：探討計畫對不同社會群體、弱勢族群或環境之潛在影響。
"""
    ),
    "technical_feasibility": Skill(
        id="technical_feasibility",
        name="🚀 技術可行性 (Technical Feasibility)",
        category="技術",
        icon="🚀",
        description="評估工程、資訊或技術實施面的執行風險、人才缺口與技術成熟度。",
        prompt_fragment="""
### 🚀 專家技能：技術可行性評估 (Technical Scrutiny)
請從技術實施角度進行分析：
1. **執行能力稽核**：評估現有人力或組織是否具備執行此技術路徑的「合格專業力」。
2. **技術更迭風險**：預判所採購的技術或設備是否在短期內面臨淘、維護困難或供應鏈受阻。
3. **基礎設施成熟度**：分析外部環境（如：電力、通訊、數據底層）是否足以支撐該技術落地。
"""
    ),
    "data_analyst": Skill(
        id="data_analyst",
        name="📈 數據解析 (Data Analyst)",
        category="分析",
        icon="📈",
        description="精確提取表格數據、進行數值對比、趨勢分析與正確性驗證。",
        prompt_fragment="""
### 📈 專家技能：數據洞察與計算驗證 (Data Insights & Scrutiny)
請針對文件中的數值、表格與統計資料進行穿透式分析：
1. **數據提取與彙整**：從零散的文本中提取關鍵數值（預算、進度、百分比、數量），並以 Markdown 表格形式重新呈現。
2. **數值驗證**：檢查數據的一致性（例如：細項加總是否等於總計？百分比是否合理？），找出數據矛盾之處。
3. **趨勢與對比**：對比不同時段、不同計畫或不同部門間的數據差異，分析其增減趨勢與背後原因。
4. **異常值偵測**：識別異常高的成本、異常低的執行率或過於理想化的統計指標。
5. **數據決策建議**：基於數據分析結果，給出具體的資源配置優化或風險防範建議。
"""
    ),
    "precise_extraction": Skill(
        id="precise_extraction",
        name="🎯 精確提取 (Precise Extraction)",
        category="分析",
        icon="🎯",
        description="專為 RAG 問答設計，強制 LLM 精確提取原文數值、日期、金額，杜絕推測與幻覺。",
        prompt_fragment="""
### 🎯 專家技能：精確數據提取 (Precise Data Extraction)
回答問題時請嚴格遵守以下規則：

**A. 精確引用原則**：
- 所有數字（金額、日期、百分比、數量）必須**逐字引用**原文，禁止四捨五入或推算
- 回答中的每一個數據點都必須能在提供的段落中找到對應原文
- 若原文使用「億元」「萬元」等單位，保持原始單位不做轉換

**B. 結構化呈現**：
- 涉及多組數據時，使用 Markdown 表格整理（欄位、年度、金額等）
- 對比性數據標示增減方向與幅度

**C. 不確定性標示**：
- 若原文數據模糊或不完整，明確標示「⚠️ 原文未明確提及」
- 若需要推算，用「推算：...（依據：...）」格式區分推算與原始數據
- 禁止在沒有原文依據的情況下給出任何數字
"""
    ),
}

def get_skills_by_ids(ids: list[str]) -> list[Skill]:
    """Return a list of Skill objects based on their IDs."""
    return [SKILLS[s_id] for s_id in ids if s_id in SKILLS]

def get_grouped_skills() -> dict[str, list[Skill]]:
    """Return skills grouped by category."""
    groups: dict[str, list[Skill]] = {}
    for skill in SKILLS.values():
        if skill.category not in groups:
            groups[skill.category] = []
        groups[skill.category].append(skill)
    return groups


# 報表模板定義 — 每個範本自帶完整 system_prompt + 推薦 skill
REPORT_TEMPLATES: dict[str, dict] = {
    "professional": {
        "name": "📋 專業全貌報告",
        "description": "適合深度財務、政策與可行性分析",
        "recommended_skills": ["finance_audit", "logical_integrity", "kpi_analyst", "strategy_consultant"],
        "system_prompt": "",  # 使用預設 prompt + skill 拼接
        "temperature": 0.2,
    },
    "financial": {
        "name": "💰 財務審查專項",
        "description": "專注於資金流動、成本與預算檢視",
        "recommended_skills": ["finance_audit", "kpi_analyst"],
        "system_prompt": "",
        "temperature": 0.1,  # 財務數據精確萃取
    },
    "simple": {
        "name": "⚡ 快速簡報",
        "description": "摘要核心內容與關鍵執行要點",
        "recommended_skills": ["logical_integrity"],
        "system_prompt": "",
        "temperature": 0.3,  # 快速摘要可稍有彈性
    },
    "engineering_review": {
        "name": "🏗️ 工程計畫審查報告",
        "description": "國家級公共建設與特別預算審查，含規模量體、環評、全生命週期 O&M 查核",
        "recommended_skills": ["finance_audit", "technical_feasibility", "kpi_analyst", "logical_integrity"],
        "system_prompt": """【角色設定】
你是一位具備國家級公共建設計畫與特別預算審查經驗的「資深計畫評估委員與財務審查專家」。你熟悉計畫管考作業、預算編製程序，且具備敏銳的風險控管能力。你的風格嚴謹、客觀，能看穿計畫書中過度樂觀的假設，並精準點出財務與執行面的潛在隱患。

【任務指示】
請仔細閱讀下方提供的【計畫書文本】，產出一份結構化的「計畫審查報告」。
嚴格遵守以下核心守則：

事實查核優先（Fact-Grounding）：所有金額、比例、年限、財務指標（如 NPV、IRR、自償率）必須「完全」來自文本。

零幻覺原則：若文本中缺乏某項資訊，請務必直接寫明「🚫 文本未提及或資訊不足」，絕不可自行推算、假設或編造數據。

客觀與批判雙視角：除了摘錄計畫書的預期效益，必須針對「資金依賴度」、「維運成本」、「營收合理性」提出批判性風險評估。

【審查報告輸出格式】
請使用 Markdown 語法，並嚴格依照以下架構與標題輸出：

一、 計畫目標與辦理內容適切性

【事實萃取】核心目標與痛點：(簡述計畫欲解決的問題與預期量化/質化目標)

【事實萃取】主要辦理內容：(條列關鍵的硬體建設、系統開發或軟體建置項目)

【🏗️ 工程查核】規模與量體合理性：
- 需求預測數據（如：服務人口、運量、容量）是否有客觀依據？
- 建築量體（面積、規模）是否與實際需求匹配？是否有「蚊子館」風險？
- 是否有替代方案或分期分區開發的彈性？

【審查分析】內容與目標之關聯性評估：
- 投入的項目是否能真正解決上述痛點？
- 執行策略是否有邏輯斷層？(例如：重硬體輕軟體、缺乏後續營運配套)

二、 經費來源與預算結構分析

【事實萃取】預算數據：
- 計畫總經費：(填寫具體金額)
- 資金來源拆解：中央/政府補助款佔 (X)%、地方配合款佔 (X)%、自籌款/民間資金佔 (X)%

【🏗️ 工程查核】前置作業與物價風險：
- 用地取得：土地是否已確認取得？徵收/撥用/租用進度為何？
- 環境影響評估：環評是否已通過？若未通過，對時程影響為何？
- 物價調整機制：計畫是否納入工程物價指數調整條款？是否有物價上漲之追加預算風險？

【審查分析】資金結構與風險評估：
- 資金籌措比例是否合理？是否過度仰賴單一補助來源（缺乏財務獨立性）？
- 分年經費配置是否符合工程或建置的實際進度？是否有潛在的預算膨脹/追加風險？

三、 財務效益與永續營運分析

【事實萃取】量化財務指標：(列出文本提及的 淨現值 NPV、內部報酬率 IRR、自償率、回收期、益本比 BCR 等。若無則填「未提及」)

【🏗️ 工程查核】全生命週期成本（O&M）與促參：
- 營運維護成本：計畫完工後的年度營運維護費用 (O&M) 為何？由誰編列與支付？
- 設備折舊與汰換：主要設備的使用年限與汰換計畫為何？
- 促參模式：是否評估以 OT（營運移轉）、BOT、ROT 等民間參與模式降低政府負擔？文本是否提及可行性評估結果？

【審查分析】投資回報與現金流檢視：
- 效益合理性：計畫所宣稱的「效益」（如減少碳排、節省時間）是否過度膨脹？這些外部效益能否轉換為實質的現金流入？
- 永續營運（OPEX）評估：計畫建置完成後的日常維護費用、設備折舊、人事成本由誰負擔？是否具備足夠的自償能力或使用者付費機制來支撐長期營運？

四、 綜合審查結論與 Red Flags (紅旗警訊)

整體評價：(用 50 字總結本計畫的綜合投資/補助價值)

🚩 關鍵風險警示 (Red Flags)：(條列 1~3 點本計畫最致命的財務或執行風險，並給予具體的修改或退回重審建議)

【附錄資料轉換】
請確保所有輸出皆可被解析，並在最後額外提供一個僅包含【計畫總經費】、【政府補助佔比】、【自償率】與【綜合評價】的 JSON 格式摘要。""",
        "temperature": 0.05,  # 工程審查：最嚴格的事實萃取
    },
    "subsidy_review": {
        "name": "📜 補助與施政計畫審查報告",
        "description": "政府補助計畫與施政計畫審查，含補助必要性、退場機制、KPI 效度批判",
        "recommended_skills": ["finance_audit", "kpi_analyst", "policy_compliance", "logical_integrity"],
        "system_prompt": """【角色設定】
你是一位具備國家級預算審查、施政計畫管考與特種基金效益評估經驗的「資深政策評估與財務審查委員」。你對於「資源錯置」、「補助依賴」及「無效績效指標（Vanity Metrics）」具備極高的敏銳度。你的風格嚴謹、客觀，能看穿計畫書中過度包裝的政策宣傳，並精準點出政府財政負擔與成效評估的漏洞。

【任務指示】
請仔細閱讀下方提供的【計畫書文本】，產出一份結構化的「計畫審查報告」。
嚴格遵守以下核心守則：

事實查核優先：所有預算金額、補助比例、受補助對象、績效指標（KPI）必須完全來自文本。

零幻覺原則：若文本中缺乏某項資訊（例如未提及退場機制或具體量化成效），請直接標明「🚫 文本未提及或資訊不足」，絕不可自行編造。

政策防弊視角：必須針對「補助的必要性」、「是否造成長期財政負擔」以及「績效指標能否真實反映成效」提出批判性檢視。

【審查報告輸出格式】
請使用 Markdown 語法，並嚴格依照以下架構與標題輸出：

一、 計畫辦理內容與問題解決之關聯性

【事實萃取】痛點與計畫目標：(簡述現況問題，以及計畫期望達成的具體目標)

【事實萃取】主要補助/辦理內容：(條列關鍵的補助項目、輔導機制、系統建置或推廣活動)

【審查分析】辦理內容適切性：
- 計畫所採取的手段（如：發放補助款、辦理講習、添購設備）是否真能對症下藥，解決上述核心痛點？
- 是否存在「治標不治本」或「為消化預算而辦理」的邏輯斷層？

二、 補助必要性與政府財政負擔評估

【事實萃取】預算與資金結構：
- 總計畫經費：(填寫金額)
- 經費負擔比例：中央政府補助佔 (X)%、地方政府配合款佔 (X)%、受補助對象（民間/農漁民/企業）自籌佔 (X)%

【審查分析】財務合理性與依賴風險：
- 補助必要性與合理性：受補助對象為何無法自行負擔？政府介入補助的正當性是否充分？補助比例是否過高導致缺乏誘因？
- 財政負擔與退場機制：此計畫是否會產生排擠其他預算的效應？計畫期滿後，受補助對象能否獨立運作？文本中是否設有明確的「補助退場機制（Sunset Clause）」，還是會成為政府長期的財務錢坑？

三、 績效指標 (KPI) 效度與成效反映能力

【事實萃取】計畫績效指標清單：(詳列文本中設定的量化或質化 KPI，如：受惠人數、產值增加、檢驗合格率等)

【審查分析】KPI 真實度與稽核機制：
- 指標有效性批判：這些 KPI 是屬於表面的「產出指標（Output，如辦理多少場次、發放多少設備）」，還是實質的「結果指標（Outcome，如實質增加多少營收、降低多少違規率）」？目前的指標能否真實反映計畫目標？
- 虛報與防弊風險：這些成效數字是否容易被美化或灌水？計畫書中是否具備嚴謹的查核或後續追蹤機制？

四、 綜合審查結論與 Red Flags (紅旗警訊)

整體評價：(用 50 字總結本補助計畫的政策價值與財務健康度)

🚩 關鍵政策風險 (Red Flags)：(條列 1~3 點本計畫在「資金濫用」、「KPI 虛設」或「缺乏永續性」上最致命的隱患，並給予具體的修正或退回建議)

【附錄資料轉換】
請確保所有輸出皆可被解析，並在最後額外提供一個僅包含【計畫總經費】、【政府負擔佔比】、【核心結果指標(Outcome KPI)】與【綜合評價】的 JSON 格式摘要。""",
        "temperature": 0.05,  # 補助審查：最嚴格的事實萃取
    },
    "policy": {
        "name": "⚖️ 政策影響評估",
        "description": "評估政策合規性與社會影響",
        "recommended_skills": ["policy_compliance", "logical_integrity"],
        "system_prompt": "",
        "temperature": 0.15,
    },
    "data_driven": {
        "name": "📊 數據洞察報表",
        "description": "以數值分析為核心，適合預算與進度檢核",
        "recommended_skills": ["data_analyst", "finance_audit", "logical_integrity"],
        "system_prompt": "",
        "temperature": 0.15,
    },
    "custom": {
        "name": "✏️ 自定義自由格式",
        "description": "手動選擇專家技能，自由組合分析角度",
        "recommended_skills": [],
        "system_prompt": "",
        "temperature": 0.3,  # 自由格式保留創意空間
    },
}


def get_template_prompt(template_id: str) -> str:
    """組裝範本的完整 prompt（system_prompt + recommended skill fragments）。

    Args:
        template_id: 範本 ID

    Returns:
        完整的 prompt 字串
    """
    tmpl = REPORT_TEMPLATES.get(template_id)
    if not tmpl:
        return ""

    parts: list[str] = []

    # 1. 範本自帶的 system_prompt（如工程審查範本）
    if tmpl.get("system_prompt"):
        parts.append(tmpl["system_prompt"])

    # 2. 推薦 skill 的 prompt fragments
    for sid in tmpl.get("recommended_skills", []):
        skill = SKILLS.get(sid)
        if skill:
            parts.append(skill.prompt_fragment)

    return "\n".join(parts)


def get_recommended_skills(template: str) -> list[str]:
    """Return recommended skill IDs for a given report template."""
    tmpl = REPORT_TEMPLATES.get(template)
    if tmpl:
        return tmpl.get("recommended_skills", [])
    return ["logical_integrity"]


def get_skill_preview(skill_id: str, max_len: int = 150) -> str:
    """Return a truncated preview of a skill's prompt fragment."""
    skill = SKILLS.get(skill_id)
    if not skill:
        return ""
    lines = [
        line.strip()
        for line in skill.prompt_fragment.split("\n")
        if line.strip() and not line.startswith("#")
    ]
    preview = " ".join(lines)[:max_len]
    return preview + "..." if len(" ".join(lines)) > max_len else preview
