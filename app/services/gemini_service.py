# -*- coding: utf-8 -*-
import io
import re
import json
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

# ------------------- Cấu hình Gemini -------------------
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Thiếu GEMINI_API_KEY trong file .env")

genai.configure(api_key=API_KEY)
model = genai.models.get("models/gemini-2.5-flash")

# Regex MSSV
RE_MSSV_STRICT = re.compile(r"\bPH\d{5}\b", re.IGNORECASE)
RE_MSSV_LOOSE = re.compile(r"\bPH\d{4,6}\b", re.IGNORECASE)

class GeminiService:

    @staticmethod
    def extract_info_from_pdf(pdf_bytes: bytes) -> dict:
        """
        Gửi toàn bộ PDF lên Gemini, trả về dict thông tin báo cáo.
        Nếu MSSV sai, fallback OCR trang đầu.
        """
        # Convert PDF -> list ảnh
        try:
            pages = convert_from_bytes(pdf_bytes, dpi=200)
        except Exception as e:
            print("[ERROR] Chuyển PDF sang ảnh thất bại:", e)
            return {}

        # Convert pages -> bytes PNG
        images_bytes = []
        for page in pages:
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            images_bytes.append(buf.getvalue())

        # Prompt mẫu
        prompt = """
Bạn là công cụ trích xuất dữ liệu từ phiếu "Báo cáo thực tập".
Tôi gửi các trang PDF (đã convert sang ảnh) chứa thông tin:
- Trang 1: Họ tên, MSSV, Ngành, Vị trí
- Trang cuối: Ưu điểm, Nhược điểm, Đề xuất, Điểm thái độ, Điểm công việc, Đánh giá cuối cùng

Hãy trả về DUY NHẤT một JSON với các key sau (không giải thích):
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
  "Đánh giá cuối cùng": ""
}
"""

        # Chuẩn bị contents
        contents = [prompt]
        for b in images_bytes:
            contents.append({"mime_type": "image/png", "data": b})

        # Gọi Gemini
        try:
            resp = model.generate_content(contents)
            raw_text = resp.text.strip()
            m = re.search(r"\{[\s\S]*\}", raw_text)
            data = json.loads(m.group(0)) if m else {}
        except Exception as e:
            print("[ERROR] Lấy dữ liệu từ Gemini thất bại:", e)
            data = {}

        # Fallback OCR nếu MSSV không hợp lệ
        mssv = (data.get("MSSV") or "").strip()
        if not RE_MSSV_STRICT.fullmatch(mssv) and images_bytes:
            img = Image.open(io.BytesIO(images_bytes[0])).convert("RGB")
            text = pytesseract.image_to_string(img, lang="vie+eng", config="--oem 3 --psm 6")
            m = RE_MSSV_STRICT.search(text) or RE_MSSV_LOOSE.search(text)
            if m:
                data["MSSV"] = m.group(0).upper()
            else:
                data["MSSV"] = ""

        # Chuẩn hoá điểm
        for score_key in ["Điểm thái độ", "Điểm công việc"]:
            v = str(data.get(score_key) or "")
            m = re.search(r"(\d{1,2}(?:[.,]\d+)?)", v)
            if m:
                data[score_key] = m.group(1).replace(",", ".")
            else:
                data[score_key] = ""

        # Đảm bảo đủ keys
        keys = ["Họ và tên","MSSV","Ngành","Vị trí thực tập",
                "Ưu điểm","Nhược điểm","Đề xuất",
                "Điểm thái độ","Điểm công việc","Đánh giá cuối cùng"]
        for k in keys:
            if k not in data:
                data[k] = ""

        return data
