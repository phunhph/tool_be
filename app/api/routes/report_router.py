from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse, UploadReportOutput, UploadZipReportResponse
from app.services.report_service import ReportService
from app.schemas.base_schemas import ListResponse, DetailResponse, CreateResponse, UpdateResponse, DeleteResponse
from app.api.routes.auth import require_role
from fastapi import Depends, Query
from typing import Optional

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_model=ListResponse[ReportResponse], summary="Danh sách tất cả báo cáo")
def get_reports(db: Session = Depends(get_db), _: User = Depends(require_role(["admin", "viewer"])), page: int = 1, page_size: int = 20, exam_id: Optional[int] = Query(None, description="Lọc theo ID kỳ thi"),):
    return ReportService.get_list(db, page, page_size, exam_id)

@router.get("/export", summary="Xuất danh sách báo cáo ra file Excel")
def export_reports(db: Session = Depends(get_db), exam_id: Optional[int] = Query(None, description="Lọc theo ID kỳ thi"),):
    return ReportService.export_by_exam(db, exam_id)

@router.get("/{report_id}", response_model=DetailResponse[ReportResponse], summary="Chi tiết báo cáo theo ID")
def get_report_detail(report_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(["admin", "viewer"]))):
    return ReportService.get_detail(db, report_id)

@router.get("/{report_id}/download", response_class=FileResponse, summary="Tải file PDF của báo cáo")
def download_report_file(report_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(["admin", "viewer", "master"]))):
    return ReportService.download_report_pdf(db, report_id)

@router.post("/", response_model=CreateResponse, summary="Tạo báo cáo mới")
def create_report(payload: ReportCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin"]))):
    username = current_user.login_id if hasattr(current_user, 'login_id') else str(current_user.id)
    return ReportService.create(db, payload, username)

@router.put("/{report_id}", response_model=UpdateResponse, summary="Cập nhật thông tin báo cáo")
def update_report(report_id: int, payload: ReportUpdate, db: Session = Depends(get_db), _: User = Depends(require_role(["admin"]))):
    return ReportService.update(db, report_id, payload)

@router.delete("/{report_id}", response_model=DeleteResponse, summary="Xóa báo cáo")
def delete_report(report_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(["admin"]))):
    return ReportService.delete(db, report_id)

@router.post("/upload/{exam_id}", response_model=UploadReportOutput, summary="Upload file báo cáo cho kỳ thi")
def upload_report_files(
    exam_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "master"]))
):
    # Lấy username từ User object
    username = current_user.login_id if hasattr(current_user, 'login_id') else str(current_user.id)
    result = ReportService.upload_files(db, exam_id, files, username)
    return result

@router.post("/{exam_id}/upload-reports", response_model=UploadZipReportResponse, summary="Upload file ZIP chứa báo cáo cho kỳ thi")
async def upload_reports_endpoint(
    exam_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "master"]))
):
    """
    Upload file ZIP chứa các file PDF báo cáo cho kỳ thi.
    File ZIP sẽ được giải nén và xử lý bất đồng bộ qua Celery task.
    
    - **exam_id**: ID của kỳ thi
    - **file**: File ZIP chứa các file PDF báo cáo
    - **response**: Trả về task_id và websocket_url để theo dõi tiến trình xử lý
    """
    # Kiểm tra kiểu MIME hoặc phần mở rộng file
    valid_mime_types = ["application/zip", "application/x-zip-compressed"]
    valid_extensions = [".zip"]
    
    is_valid_mime = file.content_type in valid_mime_types if file.content_type else False
    is_valid_extension = any(file.filename.lower().endswith(ext) for ext in valid_extensions) if file.filename else False
    
    if not (is_valid_mime or is_valid_extension):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file ZIP.")
        
    # Đọc nội dung file ZIP thành bytes
    zip_bytes = await file.read()
    
    # Lấy username từ User object (tránh lỗi serialize khi gửi vào Celery)
    username = current_user.login_id if hasattr(current_user, 'login_id') else str(current_user.id)
    
    # Gửi bytes và tên file (để tạo folder) vào service với username từ authenticated user
    result = ReportService.process_zip_upload(db, exam_id, zip_bytes, file.filename, username)
    
    return result