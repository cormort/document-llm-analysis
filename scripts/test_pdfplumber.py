import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.services.llm_service import LLMService

def test_pdf():
    files = [
        "data/115-118年「農糧產業調整與轉型計畫」(草案)(114.10).pdf",
        "data/高雄捷運黃線建設及周邊土地開發計畫.pdf"
    ]
    srv = LLMService()
    
    for f in files:
        if os.path.exists(f):
            print(f"Testing {f}")
            # we will extract first 50 pages or find "財務效益分析"
            text = srv.extract_text_from_pdf(f, start_page=1, end_page=200)
            
            if "財務效益" in text or "效益分析" in text:
                print(f"FOUND '財務效益' in {f}!")
                # show context around it
                idx = text.find("財務效益")
                if idx == -1: idx = text.find("效益分析")
                
                print(text[max(0, idx-500):idx+1000])
                print("-" * 50)
            else:
                print(f"Not found in {f}")

if __name__ == "__main__":
    test_pdf()
