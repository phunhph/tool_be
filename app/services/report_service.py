import os, zipfile
from datetime import datetime
from fastapi.responses import FileResponse
import openpyxl
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.core.ai_reader import extract_report_info
from app.models.report import Report
from app.models.report_file import ReportFile
from app.models.exam import Exam
from app.schemas.base_schemas import CreateResponse, DeleteResponse, DetailResponse, ListResponse, UpdateResponse
from app.schemas.report import ReportCreate, ReportUpdate, ReportStatus
from app.services.gemini_service import GeminiService, PLAGIARISM_THRESHOLD

UPLOAD_ROOT = "uploads/reports"

# Helper để raise lỗi chuẩn
def raise_error(status: int, message: str):
    from fastapi import HTTPException
    raise HTTPException(status_code=status, detail={"status": status, "message": message})

class ReportService:

    @staticmethod
    def get_list(db: Session, page: int = 1, page_size: int = 20):
        query = db.query(Report).order_by(Report.created_at.desc())
        total = query.count()
        reports = query.offset((page - 1) * page_size).limit(page_size).all()

        return ListResponse(
            data=[ReportService.map_to_schema(r) for r in reports],
            total=total,
            pageSize=page_size,
            pageIndex=page
        )

    @staticmethod
    def get_detail(db: Session, report_id: int):
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise_error(404, "Report không tồn tại")
        return DetailResponse(
            status=True,
            data=ReportService.map_to_schema(report)
        )

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
            created_by=username
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        return CreateResponse(
            message="Tạo báo cáo thành công",
            status=True,
            objectId=new_report.id
        )

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
            data=ReportService.map_to_schema(report)
        )

    @staticmethod
    def delete(db: Session, report_id: int):
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise_error(404, "Report không tồn tại")
        db.delete(report)
        db.commit()
        return DeleteResponse(
            message="Xóa báo cáo thành công",
            status=True,
            examId=report.id
        )

    @staticmethod
    def upload_files(db: Session, exam_id: int, files: list[UploadFile], username: str):
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise_error(404, "Kỳ thi không tồn tại")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        folder_name = f"report_{exam.code}_{timestamp}"
        folder_path = os.path.join(UPLOAD_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        reports_to_commit = []

        for file in files:
            # Lưu file PDF
            file_path = os.path.join(folder_path, file.filename)
            with open(file_path, "wb") as f:
                f.write(file.file.read())

            # Gọi GeminiService để trích xuất info
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
            info = GeminiService.extract_info_from_pdf(pdf_bytes)

            # Lưu Report vào DB
            report = Report(
                name=info.get("Họ và tên", file.filename),
                student_code=info.get("MSSV", "UNKNOWN"),
                major=info.get("Ngành"),
                position=info.get("Vị trí thực tập"),
                strengths=info.get("Ưu điểm"),
                weaknesses=info.get("Nhược điểm"),
                proposal=info.get("Đề xuất"),
                attitude_score=info.get("Điểm thái độ"),
                work_score=info.get("Điểm công việc"),
                note=info.get("Đánh giá cuối cùng"),
                status=ReportStatus.completed,
                created_by=username,
                exam_id=exam_id,
                created_at=datetime.utcnow()
            )
            db.add(report)
            db.flush()

            db.add(ReportFile(
                name_file=file.filename,
                path_storage=file_path,
                report_id=report.id
            ))

            reports_to_commit.append(report)

        db.commit()

        zip_name = f"{folder_name}.zip"
        zip_path = os.path.join(UPLOAD_ROOT, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files_in_folder in os.walk(folder_path):
                for f in files_in_folder:
                    path = os.path.join(root, f)
                    zipf.write(path, os.path.relpath(path, folder_path))

        return {"message": "Upload và xử lý thành công", "zip_file": zip_name}

    @staticmethod
    def upload_files(db: Session, exam_id: int, files: list[UploadFile], username: str):
        """
        Tải lên file, trích xuất thông tin, lưu DB, kiểm tra đạo văn và nén file.
        """
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            # Thay thế bằng hàm raise_error thực tế của bạn
            # raise_error(404, "Kỳ thi không tồn tại") 
            raise ValueError("Kỳ thi không tồn tại") 

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        folder_name = f"report_{exam.code}_{timestamp}"
        folder_path = os.path.join(UPLOAD_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        reports_to_check = [] # Dùng để lưu các báo cáo mới cần kiểm tra đạo văn

        for file in files:
            # Lưu file PDF
            file_path = os.path.join(folder_path, file.filename)
            # Đọc nội dung file trước khi đóng và lưu
            file_content = file.file.read() 
            
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Gọi GeminiService để trích xuất info (dùng nội dung file đã đọc)
            info = GeminiService.extract_info_from_pdf(file_content) 

            # 1. LƯU REPORT VÀ THU THẬP NỘI DUNG THÔ
            report = Report(
                name=info.get("Họ và tên", file.filename),
                student_code=info.get("MSSV", "UNKNOWN"),
                major=info.get("Ngành"),
                position=info.get("Vị trí thực tập"),
                strengths=info.get("Ưu điểm"),
                weaknesses=info.get("Nhược điểm"),
                proposal=info.get("Đề xuất"),
                attitude_score=float(info.get("Điểm thái độ", 0) or 0), # Chuẩn hoá float
                work_score=float(info.get("Điểm công việc", 0) or 0),   # Chuẩn hoá float
                note=info.get("Đánh giá cuối cùng"),
                raw_content=info.get("Nội dung báo cáo thô", ""), # 👈 LƯU NỘI DUNG THÔ
                status=ReportStatus.checked,
                created_by="test",
                exam_id=exam_id,
                created_at=datetime.utcnow()
            )
            db.add(report)
            db.flush() # Lấy report.id

            db.add(ReportFile(
                name_file=file.filename,
                path_storage=file_path,
                report_id=report.id
            ))

            # Thu thập thông tin để kiểm tra đạo văn sau khi commit
            reports_to_check.append({
                "report_id": report.id,
                "filename": file.filename,
                "content": info.get("Nội dung báo cáo thô", "")
            })

        db.commit() # Commit tất cả Report và ReportFile

        # 2. KIỂM TRA ĐẠO VĂN (So sánh giữa các file mới)
        print("\n--- Bắt đầu Kiểm tra Đạo văn giữa các file mới ---")
        plagiarism_detected = []
        
        for i in range(len(reports_to_check)):
            for j in range(i + 1, len(reports_to_check)):
                report1 = reports_to_check[i]
                report2 = reports_to_check[j]
                
                score = GeminiService.check_plagiarism_similarity(report1["content"], report2["content"])
                
                if score >= PLAGIARISM_THRESHOLD:
                    # 3. Ghi nhận kết quả đạo văn
                    plagiarism_detected.append({
                        "file_1": report1["filename"],
                        "file_2": report2["filename"],
                        "score": f"{score:.4f}",
                        "id_1": report1["report_id"],
                        "id_2": report2["report_id"]
                    })
                    
                    # CẬP NHẬT TRẠNG THÁI REPORT (Nếu cần)
                    # Ví dụ: đánh dấu cờ đạo văn trong DB hoặc thêm ghi chú vào Report
                    db.query(Report).filter(Report.id.in_([report1["report_id"], report2["report_id"]])).update(
                        {"note": Report.note + f" | ⚠️ Cảnh báo Đạo văn (Score: {score:.2f} vs {report2['filename']})"}, 
                        synchronize_session='fetch'
                    )
                    db.commit() # Commit cập nhật ghi chú/cờ

        # 4. Nén thư mục và Trả về kết quả
        zip_name = f"{folder_name}.zip"
        zip_path = os.path.join(UPLOAD_ROOT, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files_in_folder in os.walk(folder_path):
                for f in files_in_folder:
                    path = os.path.join(root, f)
                    zipf.write(path, os.path.relpath(path, folder_path))

        if plagiarism_detected:
            print(f"🚨 Phát hiện {len(plagiarism_detected)} cặp file có dấu hiệu đạo văn.")

        return {
            "message": "Upload, xử lý, và kiểm tra đạo văn thành công", 
            "zip_file": zip_name, 
            "plagiarism_results": plagiarism_detected
        }

    @staticmethod
    def map_to_schema(report: Report):
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
            "created_at": report.created_at or datetime.utcnow(),
            "files": [
                {
                    "id": f.id,
                    "name_file": f.name_file,
                    "path_storage": f.path_storage,
                    "created_at": f.created_at or datetime.utcnow()
                }
                for f in getattr(report, "files", [])
            ]
        }
