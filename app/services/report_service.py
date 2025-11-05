import os
import shutil
import zipfile
import asyncio
import logging
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Any, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from app.models import Report, Exam
from app.schemas.report import ReportStatus, ReportCreate, ReportUpdate
from app.schemas.base_schemas import (
    CreateResponse, DeleteResponse, DetailResponse, ListResponse, UpdateResponse
)
from app.services.gemini_service import GeminiService, PLAGIARISM_THRESHOLD
from app.tasks.report_tasks import process_uploaded_archive
import tempfile
import json
# Logging setup
logger = logging.getLogger(__name__)

UPLOAD_ROOT = "uploads/reports"
MAX_WORKERS = 5  # số luồng xử lý song song


# ------------------- Helper chung -------------------
def raise_error(status: int, message: str):
    raise HTTPException(status_code=status, detail={"status": status, "message": message})


# ------------------- Service chính -------------------
class ReportService:

    # ------------------- Mapper -------------------
    @staticmethod
    def map_to_schema(report: Report) -> Dict[str, Any]:
        return {
            "id": report.id,
            "name": report.name,
            "student_code": report.student_code,
            "major": report.major,
            "position": report.position,
            "advantage": report.strengths,
            "disadvantage": report.weaknesses,
            "suggestion": report.proposal,
            "note": report.note,
            "attitude_point": report.attitude_score,
            "work_point": report.work_score,
            "status": report.status,
            "exam_id": report.exam_id,
            "created_at": report.created_at,
            "files": [
                {
                    "id": f.id,
                    "name_file": f.name_file,
                    "path_storage": f.path_storage,
                    "created_at": f.created_at,
                }
                for f in getattr(report, "files", [])
            ],
        }

    # ------------------- CRUD -------------------
    @staticmethod
    def get_list(db: Session, page: int = 1, page_size: int = 20):
        query = db.query(Report).order_by(Report.created_at.desc())
        total = query.count()
        reports = query.offset((page - 1) * page_size).limit(page_size).all()

        return ListResponse(
            data=[ReportService.map_to_schema(r) for r in reports],
            total=total,
            pageSize=page_size,
            pageIndex=page,
        )

    @staticmethod
    def get_detail(db: Session, report_id: int):
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise_error(404, "Report không tồn tại")
        return DetailResponse(status=True, data=ReportService.map_to_schema(report))

    @staticmethod
    def create(db: Session, payload: ReportCreate, username: str):
        data = payload.dict(exclude_unset=True)
        new_report = Report(
            name=data.get("name"),
            student_code=data.get("student_code"),
            major=data.get("major"),
            position=data.get("position"),
            strengths=data.get("advantage"),
            weaknesses=data.get("disadvantage"),
            proposal=data.get("suggestion"),
            attitude_score=data.get("attitude_point"),
            work_score=data.get("work_point"),
            note=data.get("note"),
            status=data.get("status") or ReportStatus.pending,
            exam_id=data.get("exam_id"),
            created_at=datetime.utcnow(),
            created_by=username,
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        return CreateResponse(message="Tạo báo cáo thành công", status=True, objectId=new_report.id)

    @staticmethod
    def update(db: Session, report_id: int, payload: ReportUpdate):
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise_error(404, "Report không tồn tại")

        for key, value in payload.dict(exclude_unset=True).items():
            setattr(report, key, value)

        db.commit()
        db.refresh(report)

        return UpdateResponse(
            message="Cập nhật báo cáo thành công",
            status=True,
            data=ReportService.map_to_schema(report),
        )

    @staticmethod
    def delete(db: Session, report_id: int):
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise_error(404, "Report không tồn tại")

        db.delete(report)
        db.commit()

        return DeleteResponse(message="Xóa báo cáo thành công", status=True, examId=report.id)

    # ------------------- Worker xử lý file đơn -------------------
    @staticmethod
    def _process_single_file_task_worker(file_data: Dict[str, Any], folder_path: str) -> Dict[str, Any]:
        file_name = file_data["filename"]
        file_path = os.path.join(folder_path, file_name)

        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            info = GeminiService.extract_info_from_pdf(pdf_bytes)

            return {
                "original_filename": file_name,
                "name": info.get("Họ và tên", file_name),
                "student_code": info.get("MSSV", "UNKNOWN"),
                "raw_content": info.get("Nội dung báo cáo thô", ""),
                "status": "SUCCESS" if info.get("MSSV") else "MISSING_MSSV",
                **info,
            }
        except Exception as e:
            return {"original_filename": file_name, "status": "ERROR", "error_detail": str(e)}

    # ------------------- Hàm xử lý đa luồng chính -------------------
    @staticmethod
    async def run_full_processing(task, exam_id: str, folder_path: str, file_metadata: List[Dict[str, Any]], update_progress_func):
        """
        Hàm xử lý chính chạy trong Celery Worker.
        Gồm các bước:
             Duyệt từng file PDF
             Gọi Gemini để trích xuất thông tin
             Kiểm tra đạo văn
             Cập nhật tiến độ lên Redis + WebSocket
             Nén kết quả thành ZIP
        """
        total = len(file_metadata)
        processed = 0
        results = []
        plagiarism_results = []

        # Tạo folder tạm cho output
        temp_output_dir = tempfile.mkdtemp(prefix=f"reports_{exam_id}_")

        for file_info in file_metadata:
            try:
                filename = file_info["filename"]
                file_path = os.path.join(folder_path, filename)

                # --- Đọc file ---
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()

                # --- Trích xuất dữ liệu từ Gemini ---
                extracted = GeminiService.extract_info_from_pdf(pdf_bytes)
                extracted["filename"] = filename
                results.append(extracted)

                processed += 1

                # --- Gửi tiến độ ---
                await update_progress_func(task, processed, total, exam_id)

            except Exception as e:
                print(f"[ERROR] Lỗi xử lý file {filename}: {e}")
                continue

        # --- Kiểm tra đạo văn (nếu có >1 file) ---
        if len(results) > 1:
            for i in range(len(results)):
                for j in range(i + 1, len(results)):
                    sim = GeminiService.check_plagiarism_similarity(
                        results[i].get("Nội dung báo cáo thô", ""),
                        results[j].get("Nội dung báo cáo thô", "")
                    )
                    if sim >= 0.75:
                        plagiarism_results.append({
                            "file_a": results[i]["filename"],
                            "file_b": results[j]["filename"],
                            "similarity": round(sim, 3)
                        })

        # --- Ghi kết quả ra JSON ---
        output_json_path = os.path.join(temp_output_dir, "summary.json")
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "exam_id": exam_id,
                "results": results,
                "plagiarism_results": plagiarism_results
            }, f, ensure_ascii=False, indent=2)

        # --- Nén thành ZIP ---
        zip_output_path = os.path.join(temp_output_dir, f"exam_{exam_id}_result.zip")
        with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_output_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), file)

        # --- Gửi tiến độ hoàn tất ---
        await update_progress_func(task, total, total, exam_id)

        # --- Trả kết quả cuối cùng cho Celery backend ---
        return {
            "plagiarism_results": plagiarism_results,
            "zip_file": zip_output_path
        }

    # ------------------- Nhận file ZIP và khởi tạo task -------------------
    @staticmethod
    def process_zip_upload(db: Session, exam_id: int, zip_bytes: bytes, zip_filename: str, username: str):
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise_error(404, "Kỳ thi không tồn tại")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        folder_name = f"report_{exam.code}_{timestamp}"
        folder_path = os.path.join(UPLOAD_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        file_metadata = []

        try:
            with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zip_ref:
                member_names = [
                    name for name in zip_ref.namelist() if name.lower().endswith(".pdf") and not name.endswith("/")
                ]

                if not member_names:
                    raise_error(400, "File ZIP không chứa file PDF hợp lệ.")

                for name in member_names:
                    content = zip_ref.read(name)
                    base_name = os.path.basename(name)
                    temp_path = os.path.join(folder_path, base_name)

                    # tránh ghi đè file trùng tên
                    if os.path.exists(temp_path):
                        base_name = f"{datetime.utcnow().timestamp()}_{base_name}"
                        temp_path = os.path.join(folder_path, base_name)

                    with open(temp_path, "wb") as f:
                        f.write(content)

                    file_metadata.append({"filename": base_name, "path": temp_path})
        except Exception as e:
            shutil.rmtree(folder_path, ignore_errors=True)
            raise_error(500, f"Lỗi khi giải nén file ZIP: {e}")

        # Gọi Celery task
        task = process_uploaded_archive.delay(str(exam_id), folder_path, file_metadata, username)

        return {
            "success": True,
            "status": True,
            "objectId": exam_id,
            "message": f"Đã nhận {len(file_metadata)} file PDF. Hệ thống đang xử lý ngầm.",
            "data": {"task_id": task.id, "websocket_url": f"/ws/status/{task.id}"},
        }
    