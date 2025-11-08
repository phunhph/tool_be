from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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
    created_at: Optional[datetime] = None

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
    created_at: Optional[datetime] = None
    files: List[ReportFileResponse] = []

    class Config:
        from_attributes = True

class ReportFileSchema(BaseModel):
    id: int
    name_file: str
    path_storage: str
    created_at: Optional[datetime] = None

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

class UploadReportOutput(BaseModel):
    extracted_reports: List[Dict[str, Any]]
    plagiarism_results: List[Dict[str, Any]]
    zip_file: str
    message: str

class TaskData(BaseModel):
    task_id: str = Field(description="ID của Celery task để theo dõi tiến trình")
    websocket_url: str = Field(description="URL WebSocket để nhận cập nhật trạng thái")
    api_url: str = Field(description="URL API để lấy trạng thái task")
    file_count: int = Field(description="Số lượng file PDF đã upload")

class UploadZipReportResponse(BaseModel):
    success: bool = Field(description="Trạng thái thành công")
    status: bool = Field(description="Trạng thái xử lý")
    objectId: int = Field(description="ID của kỳ thi")
    message: str = Field(description="Thông báo kết quả")
    data: TaskData = Field(description="Thông tin task và WebSocket URL")

class FileProcessingResult(BaseModel):
    filename: str = Field(description="Tên file")
    status: str = Field(description="Trạng thái xử lý: DONE, FAILED, PENDING")
    result: Optional[Dict[str, Any]] = Field(description="Kết quả xử lý (chứa report_id nếu thành công)")
    error: Optional[str] = Field(description="Lỗi nếu có")

class PlagiarismResultDetail(BaseModel):
    report_id_1: int = Field(description="ID của report thứ nhất")
    report_id_2: int = Field(description="ID của report thứ hai")
    filename_1: str = Field(description="Tên file thứ nhất")
    filename_2: str = Field(description="Tên file thứ hai")
    similarity: float = Field(description="Độ tương đồng (0-1)")

class TaskStatusResponse(BaseModel):
    status: bool = Field(description="Trạng thái API call")
    task_id: str = Field(description="ID của task")
    exam_id: str = Field(description="ID của kỳ thi")
    username: str = Field(description="Username người upload")
    task_status: str = Field(description="Trạng thái task: PENDING, PROCESSING, COMPLETED, FAILED")
    celery_state: str = Field(description="Trạng thái từ Celery")
    progress: float = Field(description="Tiến độ xử lý (0-100)")
    pdf_total: int = Field(description="Tổng số file PDF")
    pdf_done: int = Field(description="Số file đã xử lý thành công")
    pdf_failed: int = Field(description="Số file xử lý thất bại")
    pdf_pending: int = Field(description="Số file đang chờ xử lý")
    plagiarism_count: int = Field(description="Số cặp file bị phát hiện đạo văn")
    started_at: Optional[str] = Field(description="Thời gian bắt đầu")
    completed_at: Optional[str] = Field(description="Thời gian hoàn thành")
    failed_at: Optional[str] = Field(description="Thời gian thất bại")
    error: Optional[str] = Field(description="Lỗi nếu có")
    files: List[FileProcessingResult] = Field(description="Danh sách file và kết quả xử lý")
    plagiarism_results: List[PlagiarismResultDetail] = Field(description="Kết quả kiểm tra đạo văn")