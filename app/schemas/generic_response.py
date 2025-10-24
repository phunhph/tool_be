# app/schemas/generic_response.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- SCHEMA DATA CHO UPLOAD ---
class PlagiarismResultSchema(BaseModel):
    # Dựa trên output từ check_and_log_plagiarism
    file_1: str = Field(description="Tên file thứ nhất.")
    file_2: str = Field(description="Tên file thứ hai.")
    score: str = Field(description="Điểm tương đồng Cosine (chuỗi thập phân).")
    id_1: Optional[int] = Field(description="ID Report của file 1.")
    id_2: Optional[int] = Field(description="ID Report của file 2.")
    
class UploadSuccessData(BaseModel):
    message: str = Field(description="Thông báo tổng quan.")
    zip_file: str = Field(description="Tên file nén chứa các báo cáo.")
    plagiarism_results: List[PlagiarismResultSchema] = Field(description="Kết quả kiểm tra đạo văn giữa các file vừa upload.")

# --- SCHEMA PHẢN HỒI CHUNG (Dựa trên lỗi ResponseValidationError) ---
# Lỗi cho thấy bạn cần các trường: message, status (boolean), objectId, data
class GenericResponse(BaseModel):
    """Schema Response chung có thể đang được sử dụng."""
    success: bool
    status: int # Thay vì bool (như lỗi mong muốn) để truyền HTTP code
    objectId: Optional[int]
    data: Optional[Any] # Cho phép truyền vào bất kỳ schema Data nào khác

class UploadResponseSchema(BaseModel):
    """Schema Chính xác cho Endpoint Upload, cần sửa lại cho phù hợp với lỗi."""
    
    # 🚨 Dựa trên lỗi, chúng ta cần GÁN CÁC FIELD SAI VÀO CẤU TRÚC:
    # Nếu không thể sửa cấu trúc GenericResponse, phải tuân thủ nó:
    message: str = Field(description="Thông báo của hệ thống (Lỗi này yêu cầu field này ở cấp root).")
    status: bool = Field(description="Trạng thái HTTP code (Lỗi này yêu cầu là boolean, cần kiểm tra lại).")
    objectId: int = Field(description="ID của Exam (hoặc đối tượng chính).")
    
    # Lồng data của bạn vào một trường phụ
    data: UploadSuccessData