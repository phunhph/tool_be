import json
import os
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any

from app.core.celery_app import celery_app
from app.services.gemini_service import GeminiService, PLAGIARISM_THRESHOLD
from app.db import SessionLocal
from app.models import Report, ReportFile
from app.schemas.report import ReportStatus
from app.core.redis_client import redis_client
from app.core.google_drive import get_google_drive_manager
from io import BytesIO

# Redis connection
r = redis_client
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

                # Đọc file PDF (từ Google Drive hoặc Local)
                file_path = pdf_info.get("path")
                storage_type = pdf_info.get("storage", "local")
                
                pdf_bytes = None
                
                if storage_type == "google_drive" and file_path.startswith("gdrive://"):
                    # Đọc từ Google Drive
                    gdrive_file_id = file_path.replace("gdrive://", "")
                    gd_manager = get_google_drive_manager()
                    
                    if gd_manager.is_configured:
                        try:
                            # Download file từ Google Drive
                            request = gd_manager.service.files().get_media(fileId=gdrive_file_id)
                            fh = BytesIO()
                            downloader = gd_manager.service.files()._service.auth.do_request(request)
                            # Đơn giản hơn: dùng download_to_file
                            from googleapiclient.http import MediaIoBaseDownload
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                            pdf_bytes = fh.getvalue()
                            logger.info(f"[GDRIVE] Downloaded: {filename} ({len(pdf_bytes)} bytes)")
                        except Exception as e:
                            logger.error(f"Lỗi download từ Google Drive: {e}")
                            raise
                    else:
                        raise Exception("Google Drive not configured")
                else:
                    # Đọc từ Local Storage
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"File không tồn tại: {file_path}")

                    with open(file_path, "rb") as f:
                        pdf_bytes = f.read()
                    logger.info(f"[LOCAL] Read: {filename} ({len(pdf_bytes)} bytes)")

                if not pdf_bytes:
                    raise ValueError("Không thể đọc file PDF")

                # Trích xuất thông tin từ PDF bằng GeminiService
                extracted_data = GeminiService.extract_info_from_pdf(pdf_bytes)
                logger.info(f"[Task {task_id}] Response api {extracted_data}")
                # Kiểm tra MSSV có hợp lệ không
                mssv = extracted_data.get("MSSV", "").strip()
                if not mssv:
                    raise ValueError("Không tìm thấy MSSV trong file PDF")
                
                # ------------------- Chuẩn hóa dữ liệu từ Gemini -------------------
                data = extracted_data or {} 
                print (data)
                name = (data.get("Họ và tên") or filename or "").strip()
                mssv = (data.get("MSSV") or "").strip()
                major = (data.get("Ngành") or "").strip()
                company = (data.get("Thực tập tại công ty(doanh nghiệp)") or "").strip()
                position = (data.get("Vị trí thực tập") or "").strip()
                strengths = (data.get("Ưu điểm") or "").strip()
                weaknesses = (data.get("Hạn chế") or "").strip()
                proposal = (data.get("Đề xuất góp ý") or "").strip()
                raw_content = (data.get("Nội dung báo cáo thô") or "").strip()
                note = (data.get("Đánh giá cuối cùng") or "").strip()


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
                    processing_error=None,
                )

                db.add(new_report)
                db.flush()  # Lấy ID của report

                # Tạo ReportFile trong database
                # path_storage: Lưu đường dẫn Google Drive (gdrive://id) hoặc local path
                new_report_file = ReportFile(
                    name_file=filename,
                    path_storage=file_path,
                    report_id=new_report.id,
                    created_at=datetime.utcnow(),
                )
                db.add(new_report_file)
                logger.info(f"[DB] Created ReportFile: {filename} -> {file_path}")

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
            # Commit để lưu vào DB
                db.commit()
            
            except Exception as e:
                logger.error(f"[Task {task_id}] Lỗi xử lý file {filename}: {str(e)}", exc_info=True)
                
                # Rollback transaction nếu có lỗi
                db.rollback()

                # Cập nhật Redis
                error_msg = str(e)[:500]  # Giới hạn độ dài error message
                fallback_report_id = None
                fallback_student_code = None
                fallback_name = os.path.splitext(filename)[0] or filename

                try:
                    fallback_report = Report(
                        name=fallback_name,
                        student_code=f"ERR-{uuid.uuid4().hex[:8]}",
                        status=ReportStatus.failed,
                        exam_id=exam_id_int,
                        created_at=datetime.utcnow(),
                        created_by=username,
                        processing_error=error_msg,
                    )
                    db.add(fallback_report)
                    db.flush()

                    fallback_file = ReportFile(
                        name_file=filename,
                        path_storage=file_path,
                        report_id=fallback_report.id,
                        created_at=datetime.utcnow(),
                    )
                    db.add(fallback_file)
                    db.commit()

                    fallback_report_id = fallback_report.id
                    fallback_student_code = fallback_report.student_code
                    fallback_name = fallback_report.name
                except Exception as persist_error:
                    db.rollback()
                    logger.error(
                        f"[Task {task_id}] Không thể lưu báo cáo lỗi cho file {filename}: {persist_error}",
                        exc_info=True,
                    )

                result_payload = {}
                if fallback_report_id:
                    result_payload = {
                        "report_id": fallback_report_id,
                        "student_code": fallback_student_code,
                        "name": fallback_name,
                        "error": error_msg,
                    }

                r.hset(f"task:{task_id}:file:{filename}", mapping={
                    "filename": filename,
                    "status": "FAILED",
                    "result": json.dumps(result_payload, ensure_ascii=False) if result_payload else "",
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
