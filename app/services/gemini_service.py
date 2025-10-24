# -*- coding: utf-8 -*-
import io
import re
import json
import os
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

load_dotenv()

# ------------------- Cấu hình Gemini -------------------
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Thiếu GEMINI_API_KEY trong file .env")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

# Khởi tạo Global Embedding Model (chỉ 1 lần)
try:
    EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2') 
    print("✅ Embedding Model loaded.")
except Exception as e:
    print(f"❌ LỖI: Cannot load Embedding Model: {e}")
    EMBEDDING_MODEL = None

# Regex MSSV
RE_MSSV_STRICT = re.compile(r"\bPH\d{5}\b", re.IGNORECASE)
RE_MSSV_LOOSE = re.compile(r"\bPH\d{4,6}\b", re.IGNORECASE)
PLAGIARISM_THRESHOLD = 0.80 # Ngưỡng tương đồng cosine

class GeminiService:

    @staticmethod
    def _get_image_bytes(pdf_bytes: bytes) -> List[bytes]:
        """Convert PDF bytes to a list of PNG image bytes."""
        try:
            # DPI cao hơn (ví dụ 300) tốt hơn cho scan/chữ viết tay mờ
            pages = convert_from_bytes(pdf_bytes, dpi=300) 
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
        """
        Gửi toàn bộ PDF lên Gemini để trích xuất thông tin cấu trúc 
        và nội dung thô (raw_content) cho kiểm tra đạo văn.
        """
        images_bytes = GeminiService._get_image_bytes(pdf_bytes)
        if not images_bytes:
             return {}

        # ------------------- PROMPT MỚI -------------------
        prompt = """
Bạn là công cụ trích xuất dữ liệu từ phiếu "Báo cáo thực tập".
Tôi gửi các trang PDF (đã convert sang ảnh) chứa thông tin.
Hãy trả về DUY NHẤT một JSON với các key sau (không giải thích). 
Hãy trích xuất nội dung chi tiết của phần báo cáo công việc hàng tuần vào key "Nội dung báo cáo thô".

{
  "Họ và tên": "",
  "MSSV": "",
  "Ngành": "",
  "Vị trí thực tập": "",
  "Ưu điểm": "",
  "Nhược điểm": "",
  "Đề xuất": "",
  "Điểm thái độ": "",
  "Điểm công việc": "",
  "Đánh giá cuối cùng": "",
  "Nội dung báo cáo thô": "" 
}
"""
        # ---------------------------------------------------

        # Chuẩn bị contents
        contents = [prompt]
        for b in images_bytes:
            contents.append({"mime_type": "image/png", "data": b})

        # Gọi Gemini
        try:
            resp = model.generate_content(contents)
            raw_text = resp.text.strip()
            # Xử lý trường hợp Gemini bao JSON bằng Markdown (```json ... ```)
            m = re.search(r"\{[\s\S]*\}", raw_text) 
            data = json.loads(m.group(0)) if m else {}
        except Exception as e:
            print("[ERROR] Lấy dữ liệu từ Gemini thất bại:", e)
            data = {}

        # ------------------- Fallback OCR cho MSSV -------------------
        mssv = (data.get("MSSV") or "").strip()
        if not RE_MSSV_STRICT.fullmatch(mssv) and images_bytes:
            # Chỉ dùng ảnh trang 1 cho fallback MSSV
            img = Image.open(io.BytesIO(images_bytes[0])).convert("RGB")
            # Tăng DPI cho Pytesseract để cải thiện độ chính xác cho scan mờ
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            
            text = pytesseract.image_to_string(img, lang="vie+eng", config="--oem 3 --psm 6")
            m = RE_MSSV_STRICT.search(text) or RE_MSSV_LOOSE.search(text)
            if m:
                data["MSSV"] = m.group(0).upper()
            else:
                data["MSSV"] = ""

        # ------------------- Chuẩn hoá Điểm số -------------------
        for score_key in ["Điểm thái độ", "Điểm công việc"]:
            v = str(data.get(score_key) or "")
            m = re.search(r"(\d{1,2}(?:[.,]\d+)?)", v)
            if m:
                # Thay thế dấu phẩy bằng dấu chấm cho chuẩn hoá float
                data[score_key] = m.group(1).replace(",", ".") 
            else:
                data[score_key] = ""

        # ------------------- Đảm bảo đủ Keys -------------------
        keys = ["Họ và tên","MSSV","Ngành","Vị trí thực tập",
                "Ưu điểm","Nhược điểm","Đề xuất",
                "Điểm thái độ","Điểm công việc","Đánh giá cuối cùng", "Nội dung báo cáo thô"]
        for k in keys:
            if k not in data:
                data[k] = ""

        return data
    
    @staticmethod
    def check_plagiarism_similarity(content_a: str, content_b: str) -> float:
        """
        Tính toán độ tương đồng ngữ nghĩa (Cosine Similarity) giữa hai đoạn văn bản.
        """
        if EMBEDDING_MODEL is None or not content_a or not content_b or len(content_a) < 50 or len(content_b) < 50:
            return 0.0
        
        try:
            # Mã hóa nội dung thành vector nhúng
            embeddings = EMBEDDING_MODEL.encode([content_a, content_b])
            
            # Tính toán độ tương đồng Cosine
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return similarity
        except Exception as e:
            print(f"[ERROR] Tính toán độ tương đồng thất bại: {e}")
            return 0.0

    @staticmethod
    def is_plagiarized(content_a: str, content_b: str, threshold: float = PLAGIARISM_THRESHOLD) -> float:
        """Kiểm tra xem nội dung có bị đạo văn không, trả về điểm tương đồng."""
        return GeminiService.check_plagiarism_similarity(content_a, content_b)