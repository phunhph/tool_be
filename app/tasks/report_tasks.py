import redis
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from app.services.websocket_manager import manager
from app.core.celery_app import celery_app
from app.services.gemini_service import GeminiService, PLAGIARISM_THRESHOLD
from app.db import SessionLocal
from app.models import Report, ReportFile
from app.schemas.report import ReportStatus

# Redis connection
r = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_uploaded_archive(self, exam_id: str, folder_path: str, file_metadata: list, username: str):
    """
    Xử lý archive ZIP chứa các file PDF báo cáo.
    - Trích xuất thông tin từ PDF bằng GeminiService
    - Tạo Report và ReportFile trong database
    - Kiểm tra đạo văn giữa các file
    - Cập nhật tiến độ lên Redis
    """
    task_id = self.request.id
    exam_id_int = int(exam_id)
    total_pdfs = len(file_metadata)

    # Khởi tạo task trong Redis
    r.sadd(f"exam:{exam_id}:tasks", task_id)
    r.hset(f"task:{task_id}", mapping={
        "exam_id": exam_id,
        "username": username,
        "status": "PROCESSING",
        "pdf_total": total_pdfs,
        "pdf_done": 0,
        "pdf_failed": 0,
        "pdf_pending": total_pdfs,
        "progress": 0,
        "started_at": datetime.utcnow().isoformat(),
    })

    # Lưu danh sách file vào Redis
    for f in file_metadata:
        filename = f.get("filename")
        r.sadd(f"task:{task_id}:files", filename)
        r.hset(f"task:{task_id}:file:{filename}", mapping={
            "filename": filename,
            "status": "PENDING",
            "result": "",
            "error": ""
        })

    db = SessionLocal()
    processed_reports = []  # Lưu các Report đã tạo để kiểm tra đạo văn
    plagiarism_results = []

    try:
        # Xử lý từng file PDF
        for i, pdf_info in enumerate(file_metadata, start=1):
            filename = pdf_info.get("filename")
            file_path = pdf_info.get("path")

            try:
                logger.info(f"[Task {task_id}] Đang xử lý file {i}/{total_pdfs}: {filename}")

                # Đọc file PDF
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File không tồn tại: {file_path}")

                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()

                # Trích xuất thông tin từ PDF bằng GeminiService
                extracted_data = GeminiService.extract_info_from_pdf(pdf_bytes)
                logger.info(f"[Task {task_id}] Response api {extracted_data}")
                # Kiểm tra MSSV có hợp lệ không
                mssv = extracted_data.get("MSSV", "").strip()
                if not mssv:
                    raise ValueError("Không tìm thấy MSSV trong file PDF")
                
                # ------------------- Chuẩn hóa dữ liệu từ Gemini -------------------
                name = extracted_data.get("Họ và tên", filename).strip()
                mssv = extracted_data.get("MSSV", "").strip()
                major = extracted_data.get("Ngành", "").strip()
                company = extracted_data.get("Thực tập tại công ty(doanh nghiệp)", "").strip()
                position = extracted_data.get("Vị trí thực tập", "").strip()
                strengths = extracted_data.get("Ưu điểm", "").strip()
                weaknesses = extracted_data.get("Nhược điểm", "").strip()
                proposal = extracted_data.get("Đề xuất", "").strip()
                raw_content = extracted_data.get("Nội dung báo cáo thô", "").strip()
                note = extracted_data.get("Đánh giá cuối cùng", "").strip()

                # ------------------- Xử lý điểm số -------------------
                def parse_score(score_str: str) -> int | None:
                    try:
                        return int(float(score_str.strip())) if score_str else None
                    except (ValueError, TypeError):
                        return None

                attitude_score = parse_score(extracted_data.get("Điểm thái độ", ""))
                work_score = parse_score(extracted_data.get("Điểm công việc", ""))

                # ------------------- Tạo Report trong database -------------------
                new_report = Report(
                    name=name,
                    student_code=mssv,
                    major=major if major else None,
                    company=company if company else None,       # thêm công ty nếu có trường trong DB
                    position=position if position else None,
                    strengths=strengths if strengths else None,
                    weaknesses=weaknesses if weaknesses else None,
                    proposal=proposal if proposal else None,
                    attitude_score=attitude_score,
                    work_score=work_score,
                    raw_content=raw_content,
                    note=note if note else None,
                    status=ReportStatus.pending,
                    exam_id=exam_id_int,
                    created_at=datetime.utcnow(),
                    created_by=username,
                )

                db.add(new_report)
                db.flush()  # Lấy ID của report

                # Tạo ReportFile trong database
                new_report_file = ReportFile(
                    name_file=filename,
                    path_storage=file_path,
                    report_id=new_report.id,
                    created_at=datetime.utcnow(),
                )
                db.add(new_report_file)

                # Commit để lưu vào DB
                db.commit()

                # Lưu thông tin để kiểm tra đạo văn sau
                processed_reports.append({
                    "report_id": new_report.id,
                    "filename": filename,
                    "raw_content": raw_content,
                    "student_code": mssv,
                })

                # Cập nhật Redis
                r.hset(f"task:{task_id}:file:{filename}", mapping={
                    "filename": filename,
                    "status": "DONE",
                    "result": json.dumps({
                        "report_id": new_report.id,
                        "student_code": mssv,
                        "name": name,
                    }, ensure_ascii=False),
                    "error": ""
                })
                r.hincrby(f"task:{task_id}", "pdf_done", 1)

                logger.info(f"[Task {task_id}] Đã xử lý thành công: {filename} (Report ID: {new_report.id})")

            except Exception as e:
                logger.error(f"[Task {task_id}] Lỗi xử lý file {filename}: {str(e)}", exc_info=True)
                
                # Rollback transaction nếu có lỗi
                db.rollback()

                # Cập nhật Redis
                error_msg = str(e)[:500]  # Giới hạn độ dài error message
                r.hset(f"task:{task_id}:file:{filename}", mapping={
                    "filename": filename,
                    "status": "FAILED",
                    "result": "",
                    "error": error_msg
                })
                r.hincrby(f"task:{task_id}", "pdf_failed", 1)

            finally:
                # Cập nhật tiến độ
                done = int(r.hget(f"task:{task_id}", "pdf_done") or 0)
                failed = int(r.hget(f"task:{task_id}", "pdf_failed") or 0)
                total = int(r.hget(f"task:{task_id}", "pdf_total") or total_pdfs)
                pending = max(0, total - done - failed)
                progress = round((done + failed) / total * 100, 2) if total > 0 else 0
                
                r.hset(f"task:{task_id}", mapping={
                    "pdf_pending": pending,
                    "progress": progress,
                    "status": "PROCESSING"
                })

        # Kiểm tra đạo văn giữa các file đã xử lý thành công
        if len(processed_reports) > 1:
            logger.info(f"[Task {task_id}] Bắt đầu kiểm tra đạo văn cho {len(processed_reports)} file")
            
            for i in range(len(processed_reports)):
                for j in range(i + 1, len(processed_reports)):
                    try:
                        content_a = processed_reports[i]["raw_content"]
                        content_b = processed_reports[j]["raw_content"]
                        
                        if not content_a or not content_b or len(content_a) < 50 or len(content_b) < 50:
                            continue

                        similarity = GeminiService.check_plagiarism_similarity(content_a, content_b)
                        
                        if similarity >= PLAGIARISM_THRESHOLD:
                            plagiarism_results.append({
                                "report_id_1": processed_reports[i]["report_id"],
                                "report_id_2": processed_reports[j]["report_id"],
                                "filename_1": processed_reports[i]["filename"],
                                "filename_2": processed_reports[j]["filename"],
                                "similarity": round(similarity, 3),
                            })

                            # Cập nhật status của 2 report thành plagiarized
                            report1 = db.query(Report).filter(Report.id == processed_reports[i]["report_id"]).first()
                            report2 = db.query(Report).filter(Report.id == processed_reports[j]["report_id"]).first()
                            
                            if report1:
                                report1.status = ReportStatus.plagiarized
                            if report2:
                                report2.status = ReportStatus.plagiarized
                            
                            db.commit()
                            
                            logger.warning(
                                f"[Task {task_id}] Phát hiện đạo văn: "
                                f"{processed_reports[i]['filename']} <-> {processed_reports[j]['filename']} "
                                f"(Similarity: {similarity:.3f})"
                            )
                    except Exception as e:
                        logger.error(f"[Task {task_id}] Lỗi khi kiểm tra đạo văn: {str(e)}", exc_info=True)

        # Lưu kết quả đạo văn vào Redis
        if plagiarism_results:
            r.set(f"task:{task_id}:plagiarism", json.dumps(plagiarism_results, ensure_ascii=False))

        # Cập nhật trạng thái hoàn thành
        r.hset(f"task:{task_id}", mapping={
            "status": "COMPLETED",
            "completed_at": datetime.utcnow().isoformat(),
            "plagiarism_count": len(plagiarism_results),
        })

        logger.info(f"[Task {task_id}] Hoàn thành xử lý: {done} thành công, {failed} thất bại, {len(plagiarism_results)} cặp đạo văn")

        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "pdf_done": done,
            "pdf_failed": failed,
            "plagiarism_count": len(plagiarism_results),
        }

    except Exception as e:
        logger.error(f"[Task {task_id}] Lỗi nghiêm trọng: {str(e)}", exc_info=True)
        r.hset(f"task:{task_id}", mapping={
            "status": "FAILED",
            "error": str(e)[:500],
            "failed_at": datetime.utcnow().isoformat(),
        })
        raise

    finally:
        db.close()
