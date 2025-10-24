from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class ReportStatus(str, Enum):
    pending = "pending"
    checked = "checked"
    plagiarized = "plagiarized"
    approved = "approved"

class ReportFileResponse(BaseModel):
    id: int
    name_file: str
    path_storage: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReportBase(BaseModel):
    name: Optional[str]
    student_code: Optional[str]
    major: Optional[str]
    position: Optional[str]
    advantage: Optional[str]
    disadvantage: Optional[str]
    suggestion: Optional[str]
    note: Optional[str]
    attitude_point: Optional[int]
    work_point: Optional[int]
    status: Optional[ReportStatus]
    exam_id: Optional[int]

class ReportCreate(ReportBase):
    status: ReportStatus = ReportStatus.pending
    pass

class ReportUpdate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    created_at: datetime
    files: List[ReportFileResponse] = []

    class Config:
        from_attributes = True

class ReportFileSchema(BaseModel):
    id: int
    name_file: str
    path_storage: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class ReportInfoSchema(BaseModel):
    name: str = Field(description="Tên sinh viên/người làm báo cáo.")
    student_code: str = Field(description="Mã số sinh viên.")
    major: str = Field(description="Ngành học/Bộ phận.")
    position: str = Field(description="Vị trí thực tập/công việc.")
    strengths: str = Field(description="Ưu điểm/điểm mạnh đã nhận dạng.")
    weaknesses: str = Field(description="Nhược điểm/điểm yếu đã nhận dạng.")
    proposal: str = Field(description="Đề xuất/Kiến nghị.")
    attitude_score: float = Field(description="Điểm thái độ (chỉ lấy số).")
    work_score: float = Field(description="Điểm công việc/kết quả (chỉ lấy số).")
    note: str = Field(description="Tóm tắt nhận xét hoặc bất kỳ thông tin quan trọng nào khác.")
    # Trường quan trọng để kiểm tra đạo văn
    raw_content: str = Field(description="Toàn bộ nội dung báo cáo công việc hàng tuần được trích xuất.")