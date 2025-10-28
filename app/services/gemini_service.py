# app/services/gemini_service.py
# -*- coding: utf-8 -*-
import io
import re
import json
import os
import time # 🚨 ĐÃ BỔ SUNG
from typing import List, Dict, Any

from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import google.generativeai as genai
from dotenv import load_dotenv

# Thư viện cho Đạo văn
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from fastapi import HTTPException
load_dotenv()

def raise_error(status: int, message: str):
     raise HTTPException(status_code=status, detail={"status": status, "message": message})
    
# ------------------- Cấu hình Gemini -------------------
API_KEY = os.getenv("GEMINI_API_KEY")
# ... (Phần khởi tạo model và load EMBEDDING_MODEL giữ nguyên)

# Khởi tạo model và hằng số
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash") 

try:
    EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2') 
    print("✅ Embedding Model loaded.")
except Exception as e:
    print(f"❌ LỖI: Cannot load Embedding Model: {e}")
    EMBEDDING_MODEL = None

RE_MSSV_STRICT = re.compile(r"\bPH\d{5}\b", re.IGNORECASE)
RE_MSSV_LOOSE = re.compile(r"\bPH\d{4,6}\b", re.IGNORECASE)
PLAGIARISM_THRESHOLD = 0.80 

class GeminiService:

    @staticmethod
    def _get_image_bytes(pdf_bytes: bytes) -> List[bytes]:
        # ... (Logic chuyển PDF sang ảnh giữ nguyên, dùng DPI=150)
        try:
            pages = convert_from_bytes(pdf_bytes, dpi=150) 
        except Exception as e:
            print("[ERROR] Chuyển PDF sang ảnh thất bại:", e)
            return []
        
        images_bytes = []
        for page in pages:
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            images_bytes.append(buf.getvalue())
        return images_bytes
        
    @staticmethod
    def extract_info_from_pdf(pdf_bytes: bytes) -> dict:
        """Gửi toàn bộ PDF lên Gemini với cơ chế Retry."""
        images_bytes = GeminiService._get_image_bytes(pdf_bytes)
        data = {}

        if not images_bytes:
            return data

        prompt = """
Bạn là công cụ trích xuất dữ liệu chuyên biệt từ các phiếu "Báo cáo thực tập".
Nhiệm vụ: Trích xuất các thông tin sau vào CẤU TRÚC JSON.
... (Nội dung prompt giữ nguyên)
Hãy trả về **DUY NHẤT** một đối tượng JSON với các key sau (KHÔNG thêm bất kỳ giải thích nào):

{
  "Họ và tên": "",
  "MSSV": "",
  "Ngành": "",
  "Thực tập tại công ty(doanh nghiệp)": "",
  "Vị trí thực tập": "",
  "Ưu điểm": "Nội dung trích xuất từ phần Ưu điểm",
  "Nhược điểm": "Nội dung trích xuất từ phần Hạn chế",
  "Đề xuất": "Nội dung trích xuất từ phần Đề xuất, góp ý",
  "Điểm thái độ": "SỐ CHỮ SỐ (Điểm từ Thái độ, ý thức...)",
  "Điểm công việc": "SỐ CHỮ SỐ (Điểm từ Kết quả công việc)",
  "Đánh giá cuối cùng": "",
  "Nội dung báo cáo thô": "TRÍCH XUẤT TOÀN BỘ PHẦN BÁO CÁO CÔNG TÁC TUẦN/NGÀY."
}
"""
        contents = [prompt]
        for b in images_bytes:
            contents.append({"mime_type": "image/png", "data": b})

        max_retries = 5
        base_delay = 10 

        for attempt in range(max_retries):
            try:
                print(f"[Gemini] Thử gửi request (Lần {attempt + 1})...")
                resp = model.generate_content(contents)
                raw_text = resp.text.strip()

                # Trích xuất JSON
                m = re.search(r"\{[\s\S]*\}", raw_text) 
                data = json.loads(m.group(0)) if m else {}
                break 
            except Exception as e: 
                error_message = str(e)

                if "429" in error_message or "quota exceeded" in error_message.lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + (time.time() % 4)
                        time.sleep(delay)
                        continue
                    else:
                        raise_error(503, "Dịch vụ Gemini tạm thời không khả dụng do giới hạn quota.")
                else:
                    raise_error(500, f"Lỗi Gemini API không thể phục hồi: {error_message}")
        
        # ------------------- Fallback OCR và Chuẩn hóa -------------------
        # ... (Logic Fallback MSSV và Chuẩn hóa Điểm số giữ nguyên)
        
        # Fallback OCR cho MSSV 
        mssv = (data.get("MSSV") or "").strip()
        if not RE_MSSV_STRICT.fullmatch(mssv) and images_bytes:
            img = Image.open(io.BytesIO(images_bytes[0])).convert("RGB")
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            
            text = pytesseract.image_to_string(img, lang="vie+eng", config="--oem 3 --psm 6")
            m = RE_MSSV_STRICT.search(text) or RE_MSSV_LOOSE.search(text)
            if m:
                data["MSSV"] = m.group(0).upper()
            else:
                data["MSSV"] = ""

        # Chuẩn hoá Điểm số
        for score_key in ["Điểm thái độ", "Điểm công việc"]:
            v = str(data.get(score_key) or "")
            m = re.search(r"(\d{1,2}(?:[.,]\d+)?)", v)
            if m:
                data[score_key] = m.group(1).replace(",", ".") 
            else:
                data[score_key] = ""

        # Đảm bảo đủ Keys
        keys = ["Họ và tên","MSSV","Ngành","Vị trí thực tập",
                "Ưu điểm","Nhược điểm","Đề xuất",
                "Điểm thái độ","Điểm công việc","Đánh giá cuối cùng", "Nội dung báo cáo thô"]
        for k in keys:
            if k not in data:
                data[k] = ""
        
        return data

    @staticmethod
    def check_plagiarism_similarity(content_a: str, content_b: str) -> float:
        # ... (Logic tính toán độ tương đồng giữ nguyên)
        if EMBEDDING_MODEL is None or not content_a or not content_b or len(content_a) < 50 or len(content_b) < 50:
            return 0.0
        
        try:
            embeddings = EMBEDDING_MODEL.encode([content_a, content_b])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            print(f"[ERROR] Tính toán độ tương đồng thất bại: {e}")
            return 0.0

    @staticmethod
    def is_plagiarized(content_a: str, content_b: str, threshold: float = PLAGIARISM_THRESHOLD) -> float:
        return GeminiService.check_plagiarism_similarity(content_a, content_b)