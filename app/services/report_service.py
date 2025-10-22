import os, zipfile, datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from app.core.ai_reader import extract_report_info
from app.models.report import Report
from app.models.report_file import ReportFile
from app.models.exam import Exam
from app.schemas.base_schemas import CreateResponse, DeleteResponse, DetailResponse, ListResponse, UpdateResponse
from app.schemas.report import ReportCreate, ReportUpdate, ReportStatus
from datetime import datetime

UPLOAD_ROOT = "uploads/reports"

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
            raise HTTPException(status_code=404, detail="Report not found")
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
            raise HTTPException(status_code=404, detail="Report not found")
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
            raise HTTPException(status_code=404, detail="Report not found")
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
            raise HTTPException(status_code=404, detail="Exam not found")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        folder_name = f"report_{exam.code}_{timestamp}"
        folder_path = os.path.join(UPLOAD_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        reports_to_commit = []

        for file in files:
            file_path = os.path.join(folder_path, file.filename)
            with open(file_path, "wb") as f:
                f.write(file.file.read())

            info = extract_report_info(file_path)

            report = Report(
                name=info.get("name", file.filename),
                student_code=info.get("student_code", "UNKNOWN"),
                major=info.get("major"),
                position=info.get("position"),
                strengths=info.get("strengths"),
                weaknesses=info.get("weaknesses"),
                proposal=info.get("proposal"),
                attitude_score=info.get("attitude_score"),
                work_score=info.get("work_score"),
                note=info.get("note"),
                status=ReportStatus.completed,
                created_by=username,
                exam_id=exam_id,
                created_at=datetime.utcnow()
            )
            db.add(report)
            db.flush()  # flush để lấy id trước khi add files

            db.add(ReportFile(
                name_file=file.filename,
                path_storage=file_path,
                report_id=report.id
            ))

            reports_to_commit.append(report)

        db.commit()  # commit tất cả cùng lúc

        # Nén thư mục
        zip_name = f"{folder_name}.zip"
        zip_path = os.path.join(UPLOAD_ROOT, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files_in_folder in os.walk(folder_path):
                for f in files_in_folder:
                    path = os.path.join(root, f)
                    zipf.write(path, os.path.relpath(path, folder_path))

        return {"message": "Upload và xử lý thành công", "zip_file": zip_name}

    @staticmethod
    def map_to_schema(report: Report):
        """
        Map Report SQLAlchemy object → Pydantic schema để tránh ResponseValidationError
        """
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
