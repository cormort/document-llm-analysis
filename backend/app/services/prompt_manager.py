class PromptManager:
    """Manages LLM prompts and templates."""
    
    ANALYSIS_PROMPT = """
    You are an expert document analyst. Please analyze the following text and provide a comprehensive report.
    User Instructions: {user_instruction}
    Content:
    {content}
    """
    
    REPORT_GEN_PROMPT = """
    Based on the provided content, generate a structured {report_type}.
    Content: {content}
    """

    SYSTEM_PROMPTS = {
        "general": "You are an expert document analyst.",
    }

    EXTRACT_ENTITIES_PROMPT = """
    你是一位知識圖譜專家，擅長命名實體識別 (NER) 與關係抽取 (RE)。
    請從提供的文本中自動抽取「實體」以及「實體之間的關係」。

    【實體抽取 (NER) 規則】
    - 抽取：實體名稱 (name)、類型 (type: 人物/組織/GPE/其它)、別名 (aliases: 縮寫或替代名稱)、實體描述 (description)。
    - 對於 GPE (地理政治實體，如城市/國家)：僅描述一般性背景 (例如「台灣是一個島國」)，避免描述文中具體的事件背景。
    - 對於 人物：可包含其職位或核心事蹟。

    【關係抽取 (RE) 規則】
    - 格式：(主體, 關係, 客體)
    - 關係 (relation) 應該是動詞或簡短描述。

    【輸出格式】
    必須輸出為 JSON 對象，包含 'entities' 和 'relations' 兩個列表。
    範例：
    {{
      "entities": [
        {{"name": "台北市政府", "type": "組織", "aliases": ["台北市府"], "description": "中華民國台北市的最高行政機關"}},
        {{"name": "國科會", "type": "組織", "aliases": ["NSTC"], "description": "台灣學術研究的主管機關"}}
      ],
      "relations": [
        {{"subject": "台北市政府", "relation": "合作", "object": "國科會"}}
      ]
    }}
    只輸出 JSON，不要有其他文字。
    
    === 文本:
    {content}
    """

    @classmethod
    def get_extraction_prompt(cls, content: str) -> str:
        return cls.EXTRACT_ENTITIES_PROMPT.format(content=content[:10000]) # Truncate for safety

    @classmethod
    def get_analysis_prompt(cls, content: str, user_instruction: str) -> str:
        return cls.ANALYSIS_PROMPT.format(content=content, user_instruction=user_instruction)
    
    @classmethod
    def get_system_prompt(cls, key: str = "general") -> str:
        return cls.SYSTEM_PROMPTS.get(key, cls.SYSTEM_PROMPTS["general"])

    @classmethod
    def get_report_prompt(cls, content: str, report_type: str) -> str:
        return cls.REPORT_GEN_PROMPT.format(content=content, report_type=report_type)
