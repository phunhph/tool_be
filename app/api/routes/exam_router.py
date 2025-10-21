from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse, CreateResponse, UpdateResponse, DeleteResponse
from app.schemas.base_schemas import ListResponse, DetailResponse
from app.services.exam_service import ExamService
from app.api.routes.auth import require_role

router = APIRouter(prefix="/exams", tags=["Exams"])

# 📋 Lấy danh sách kỳ thi
@router.get("/", response_model=ListResponse[ExamResponse])
def get_exams(db: Session = Depends(get_db), _: str = Depends(require_role(["admin", "viewer"])), page: int = 1, page_size: int = 20):
    return ExamService.get_list(db, page, page_size)

# 🔍 Xem chi tiết kỳ thi
@router.get("/{exam_id}", response_model=DetailResponse[ExamResponse])
def get_exam_detail(exam_id: int, db: Session = Depends(get_db), _: str = Depends(require_role(["admin", "viewer"]))):
    return ExamService.get_detail(db, exam_id)

# ➕ Tạo kỳ thi mới
@router.post("/", response_model=CreateResponse)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db), _: str = Depends(require_role(["admin"]))):
    return ExamService.create(db, payload)

# ✏️ Cập nhật kỳ thi
@router.put("/{exam_id}", response_model=UpdateResponse)
def update_exam(exam_id: int, payload: ExamUpdate, db: Session = Depends(get_db), _: str = Depends(require_role(["admin"]))):
    return ExamService.update(db, exam_id, payload)

# ❌ Xóa kỳ thi
@router.delete("/{exam_id}", response_model=DeleteResponse)
def delete_exam(exam_id: int, db: Session = Depends(get_db), _: str = Depends(require_role(["admin"]))):
    return ExamService.delete(db, exam_id)
