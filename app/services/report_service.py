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
from app.services.gemini_service import GeminiService

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
    def export_by_exam(db: Session, exam_id: int):
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise_error(404, "Kỳ thi không tồn tại")

        reports = db.query(Report).filter(Report.exam_id == exam_id).all()
        if not reports:
            raise_error(404, "Không có báo cáo nào cho kỳ thi này")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Report_{exam.code}"

        headers = [
            "ID", "Họ tên", "Mã sinh viên", "Ngành", "Vị trí",
            "Điểm mạnh", "Điểm yếu", "Đề xuất", "Ghi chú",
            "Điểm thái độ", "Điểm công việc", "Trạng thái", "Ngày tạo"
        ]
        ws.append(headers)

        status_map = {
            ReportStatus.pending: "Pending",
            ReportStatus.completed: "Completed"
        }

        for r in reports:
            ws.append([
                r.id,
                r.name,
                r.student_code,
                r.major,
                r.position,
                r.strengths,
                r.weaknesses,
                r.proposal,
                r.note,
                r.attitude_score,
                r.work_score,
                status_map.get(r.status, r.status),
                r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            ])

        from openpyxl.utils import get_column_letter
        for i, col in enumerate(ws.columns, 1):
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[get_column_letter(i)].width = max_length + 2

        export_folder = "uploads/export"
        os.makedirs(export_folder, exist_ok=True)
        file_name = f"report_exam_{exam.code}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path = os.path.join(export_folder, file_name)
        wb.save(file_path)

        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

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
