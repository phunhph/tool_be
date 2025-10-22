from typing import List
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.services.report_service import ReportService
from app.schemas.base_schemas import ListResponse, DetailResponse, CreateResponse, UpdateResponse, DeleteResponse
from app.api.routes.auth import require_role

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/", response_model=ListResponse[ReportResponse], summary="Danh sách tất cả báo cáo")
def get_reports(db: Session = Depends(get_db), _: str = Depends(require_role(["admin", "viewer"])), page: int = 1, page_size: int = 20):
    return ReportService.get_list(db, page, page_size)

@router.get("/{report_id}", response_model=DetailResponse[ReportResponse], summary="Chi tiết báo cáo theo ID")
def get_report_detail(report_id: int, db: Session = Depends(get_db), _: str = Depends(require_role(["admin", "viewer"]))):
    return ReportService.get_detail(db, report_id)

@router.post("/", response_model=CreateResponse, summary="Tạo báo cáo mới")
def create_report(payload: ReportCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["admin"])), _: str = Depends(require_role(["admin"]))):
    return ReportService.create(db, payload, 'admin')

@router.put("/{report_id}", response_model=UpdateResponse, summary="Cập nhật thông tin báo cáo")
def update_report(report_id: int, payload: ReportUpdate, db: Session = Depends(get_db), _: str = Depends(require_role(["admin"]))):
    return ReportService.update(db, report_id, payload)

@router.delete("/{report_id}", response_model=DeleteResponse, summary="Xóa báo cáo")
def delete_report(report_id: int, db: Session = Depends(get_db), _: str = Depends(require_role(["admin"]))):
    return ReportService.delete(db, report_id)

@router.post("/upload/{exam_id}", response_model=CreateResponse, summary="Upload file báo cáo cho kỳ thi")
def upload_report_files(
    exam_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(require_role(["admin", "master"]))
):
    result = ReportService.upload_files(db, exam_id, files, username)
    return {"success": True, "status": 200, "data": result}

@router.get("/export/{exam_id}", summary="Export báo cáo theo kỳ thi ra file Excel")
def export_reports(exam_id: int, db: Session = Depends(get_db)):
    return ReportService.export_by_exam(db, exam_id)
