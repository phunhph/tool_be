# app/services/gemini_service.py
# -*- coding: utf-8 -*-
import io
import re
import json
import os
import time
from typing import List

from PIL import Image
import pytesseract
import google.generativeai as genai
from dotenv import load_dotenv

# Thư viện cho Đạo văn
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from fastapi import HTTPException
import fitz  # PyMuPDF
import pytesseract

# Thêm vào đầu module của bạn (sau import pytesseract)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
load_dotenv()

def raise_error(status: int, message: str):
     raise HTTPException(status_code=status, detail={"status": status, "message": message})
    
# ------------------- Cấu hình Gemini -------------------
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("models/gemini-2.5-flash")
else:
    model = None

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
    def extract_info_from_pdf(pdf_bytes: bytes) -> dict:
        """
        Extract thông tin từ PDF bằng Gemini. 
        Tự chia page nếu file lớn, fallback OCR MSSV nếu cần.
        """
        data = {}

        # --- Lấy text-based chunk nếu có ---
        chunks = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text = page.get_text()
                if text.strip():
                    # chia chunk ~3000 ký tự
                    for i in range(0, len(text), 3000):
                        chunks.append(text[i:i+3000])
        except Exception as e:
            print(f"[ERROR] Không thể đọc text PDF: {e}")
        
        # --- Nếu không có text, fallback ảnh ---
        images_bytes = []
        if not chunks:
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    buf = io.BytesIO(pix.tobytes(output="png"))
                    images_bytes.append(buf.getvalue())
            except Exception as e:
                print(f"[ERROR] Không chuyển PDF sang ảnh được: {e}")

        # --- Chuẩn bị prompt ---
        prompt = """
Bạn là công cụ trích xuất dữ liệu chuyên biệt từ các phiếu "Báo cáo thực tập".
Nhiệm vụ: Trích xuất các thông tin sau và trả về DUY NHẤT một đối tượng JSON có cấu trúc cố định dưới đây.

CẤU TRÚC JSON:

{
  "Họ và tên": ["Họ và Tên"],
  "MSSV": ["MSSV"],
  "Ngành": ["Ngành"],
  "Email": ["Email"],
  "Thực tập tại công ty(doanh nghiệp)": ["Thực tập tại công ty", "doanh nghiệp"],
  "Địa chỉ": ["Địa chỉ"],
  "Vị trí thực tập": ["Vị trí thực tập"],
  "Ưu điểm": ["1 Ưu điểm"],
  "Hạn chế": ["2 Hạn chế"],
  "Đề xuất góp ý": ["Đề xuất góp ý"],
  "Điểm thái độ": ["- thái độ"],
  "Điểm ý thức": ["- ý thức"],
  "Đánh giá cuối cùng": ["Đánh giá cuối cùng"]
}

---

**Hướng dẫn đặc biệt cho trường "Đánh giá cuối cùng":**
Phần này gồm hai lựa chọn:
- [ ] Đạt
- [ ] Không đạt

Hãy xác định ô nào được đánh dấu (tích ✓, dấu X, chấm tròn ●, tô đen, hoặc có ký hiệu tương tự).
Nếu ô “Đạt” được đánh dấu → ghi giá trị là `"Đạt"`.
Nếu ô “Không đạt” được đánh dấu → ghi giá trị là `"Không đạt"`.
Nếu không xác định được → ghi `"Không rõ"`.

---

**Yêu cầu chung:**
- Luôn trả về JSON hợp lệ (không thêm chữ giải thích hoặc mô tả).
- Nếu thông tin không có trong PDF, đặt giá trị là `null`.
- Tất cả giá trị phải ở dạng chuỗi (string).
- Không thêm hoặc bỏ bất kỳ key nào.
"""

        # --- Gửi lên Gemini nếu có API_KEY ---
        if model and (chunks or images_bytes):
            contents = [prompt]
            for chunk in chunks:
                contents.append(chunk)
            for img_bytes in images_bytes:
                contents.append({"mime_type": "image/png", "data": img_bytes})

            max_retries = 5
            base_delay = 10
            for attempt in range(max_retries):
                try:
                    print(f"[Gemini] Thử gửi request (Lần {attempt+1})...")
                    resp = model.generate_content(contents)
                    raw_text = resp.text.strip()
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

        # --- Fallback OCR MSSV ---
        mssv = (data.get("MSSV") or "").strip()
        if not RE_MSSV_STRICT.fullmatch(mssv):
            if not images_bytes:
                # chuyển page đầu thành ảnh nếu chưa có
                try:
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    page = doc[0]
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes(output="png"))).convert("RGB")
                    images_bytes.append(pix.tobytes(output="png"))
                except Exception as e:
                    print(f"[ERROR] Không tạo ảnh OCR: {e}")
            if images_bytes:
                img = Image.open(io.BytesIO(images_bytes[0])).convert("RGB")
                img = img.resize((img.width*2, img.height*2), Image.Resampling.LANCZOS)
                text = pytesseract.image_to_string(img, lang="vie+eng", config="--oem 3 --psm 6")
                m = RE_MSSV_STRICT.search(text) or RE_MSSV_LOOSE.search(text)
                if m:
                    data["MSSV"] = m.group(0).upper()
                else:
                    data["MSSV"] = ""

        # --- Chuẩn hóa điểm số ---
        for score_key in ["Điểm thái độ", "Điểm công việc"]:
            v = str(data.get(score_key) or "")
            m = re.search(r"(\d{1,2}(?:[.,]\d+)?)", v)
            if m:
                data[score_key] = m.group(1).replace(",", ".")
            else:
                data[score_key] = ""

        # --- Đảm bảo đủ keys ---
        keys = ["Họ và tên","MSSV","Ngành","Vị trí thực tập",
                "Ưu điểm","Nhược điểm","Đề xuất",
                "Điểm thái độ","Điểm công việc","Đánh giá cuối cùng"]
        for k in keys:
            if k not in data:
                data[k] = ""

        return data

    @staticmethod
    def check_plagiarism_similarity(content_a: str, content_b: str) -> float:
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
