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
    async def run_full_processing(
        task,
        exam_id: str,
        folder_path: str,
        file_metadata: List[Dict[str, Any]],
        update_progress_fn: Callable[[Any, int, int, str], Awaitable[None]],
    ):
        total_files = len(file_metadata)
        reports_data_list = []
        files_processed = 0

        logger.info(f"🔹 Bắt đầu xử lý {total_files} file cho exam {exam_id}")

        loop = asyncio.get_event_loop()

        # Dùng ThreadPoolExecutor để xử lý file song song
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(ReportService._process_single_file_task_worker, data, folder_path): data
                for data in file_metadata
            }

            for future in as_completed(futures):
                report_data = future.result()
                reports_data_list.append(report_data)
                files_processed += 1

                await update_progress_fn(task, files_processed, total_files, exam_id)

        # So sánh đạo văn giữa các báo cáo
        successful_reports = [r for r in reports_data_list if r.get("status") == "SUCCESS"]
        plagiarism_results = []

        if len(successful_reports) <= 30:
            for i in range(len(successful_reports)):
                for j in range(i + 1, len(successful_reports)):
                    r1, r2 = successful_reports[i], successful_reports[j]
                    sim = await GeminiService.is_plagiarized(
                        r1.get("raw_content", ""), r2.get("raw_content", "")
                    )

                    if sim >= PLAGIARISM_THRESHOLD:
                        plagiarism_results.append(
                            {
                                "file_1": r1["original_filename"],
                                "file_2": r2["original_filename"],
                                "similarity": f"{sim * 100:.2f}%",
                                "status": "PLAGIARIZED",
                            }
                        )

        # Cleanup
        shutil.rmtree(folder_path, ignore_errors=True)
        logger.info(f"✅ Xử lý hoàn tất cho exam {exam_id}, đã dọn thư mục tạm.")

        return {
            "all_reports": reports_data_list,
            "plagiarism_results": plagiarism_results,
            "zip_file": f"results_{exam_id}.zip",
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
    