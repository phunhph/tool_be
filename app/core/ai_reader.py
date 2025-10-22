def extract_report_info(pdf_path: str):
    """
    Giả lập gọi Gemini hoặc OCR để trích xuất thông tin từ PDF.
    Trong thực tế bạn sẽ thay phần này bằng Gemini API.
    """
    # TODO: integrate Gemini OCR/LLM
    return {
        "name": "Nguyễn Văn A",
        "student_code": "SV001",
        "major": "Công nghệ thông tin",
        "position": "Thực tập sinh",
        "strengths": "Chăm chỉ, chủ động",
        "weaknesses": "Còn thiếu kỹ năng giao tiếp",
        "proposal": "Tiếp tục phát triển kỹ năng chuyên môn",
        "attitude_score": 8,
        "work_score": 9,
        "note": "Không có dấu hiệu đạo văn",
    }
