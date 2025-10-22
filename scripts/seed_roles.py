from datetime import datetime
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.db import engine, Base, get_db
from app.models import User, Role
from app.models.exam import Exam
from app.models.report import Report, ReportStatus
from app.models.report_file import ReportFile

# ---------------- Password Hash ----------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# ---------------- Seed Roles ----------------
def seed_roles(db: Session):
    roles = [
        {"name": "master", "description": "Full quyền, không ai sửa được quyền"},
        {"name": "admin", "description": "Có thể xem, tạo, sửa, xóa trừ thay đổi quyền và xoá user"},
        {"name": "viewer", "description": "Chỉ có thể xem"},
    ]
    for r in roles:
        role = db.query(Role).filter(Role.name == r["name"]).first()
        if not role:
            role = Role(name=r["name"], description=r["description"])
            db.add(role)
    db.commit()
    print("Seed roles completed!")

# ---------------- Seed Users ----------------
def seed_users(db: Session):
    # Master
    master_role = db.query(Role).filter(Role.name == "master").first()
    if not db.query(User).filter(User.login_id == "master").first():
        user = User(
            first_name="Master",
            last_name="User",
            login_id="master",
            email="master@example.com",
            password=pwd_context.hash("Master123!"),
            role_id=master_role.id,
            is_delete=False,
            role = master_role
        )
        db.add(user)

    # Admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not db.query(User).filter(User.login_id == "admin").first():
        user = User(
            first_name="Admin",
            last_name="User",
            login_id="admin",
            email="admin@example.com",
            password=pwd_context.hash("Admin123!"),
            role_id=admin_role.id,
            is_delete=False
        )
        db.add(user)

    # Viewer
    viewer_role = db.query(Role).filter(Role.name == "viewer").first()
    if not db.query(User).filter(User.login_id == "viewer").first():
        user = User(
            first_name="Viewer",
            last_name="User",
            login_id="viewer",
            email="viewer@example.com",
            password=pwd_context.hash("Viewer123!"),
            role_id=viewer_role.id,
            is_delete=False
        )
        db.add(user)

    db.commit()
    print("Seed users completed!")

# ---------------- Seed Exams ----------------
def seed_exams(db: Session):
    exams_data = [
        {"code": "EXAM001", "name": "Kỳ thi 1", "start_time": datetime(2025, 10, 25, 8, 0), "end_time": datetime(2025, 10, 25, 12, 0)},
        {"code": "EXAM002", "name": "Kỳ thi 2", "start_time": datetime(2025, 10, 26, 8, 0), "end_time": datetime(2025, 10, 26, 12, 0)},
    ]
    for e in exams_data:
        exam = db.query(Exam).filter(Exam.code == e["code"]).first()
        if not exam:
            exam = Exam(**e)
            db.add(exam)
    db.commit()
    print("Seed exams completed!")

# ---------------- Seed Reports ----------------
def seed_reports(db: Session):
    exam = db.query(Exam).filter(Exam.code == "EXAM001").first()
    if not exam:
        print("Exam EXAM001 not found. Cannot seed reports.")
        return

    reports_data = [
        {"name": "Report A", "student_code": "SV001", "major": "IT", "position": "Leader",
         "strengths": "Good logic", "weaknesses": "Time management", "proposal": "Improve coding",
         "attitude_score": 8, "work_score": 9, "note": "Excellent", "status": ReportStatus.pending, "exam_id": exam.id},
        {"name": "Report B", "student_code": "SV002", "major": "CS", "position": "Member",
         "strengths": "Teamwork", "weaknesses": "Attention to detail", "proposal": "Practice more",
         "attitude_score": 7, "work_score": 8, "note": "Good", "status": ReportStatus.pending, "exam_id": exam.id},
    ]

    for r in reports_data:
        report = db.query(Report).filter(Report.student_code == r["student_code"], Report.exam_id == r["exam_id"]).first()
        if not report:
            report = Report(**r)
            db.add(report)
    db.commit()
    print("Seed reports completed!")

# ---------------- Seed ReportFiles ----------------
def seed_report_files(db: Session):
    report = db.query(Report).filter(Report.student_code == "SV001").first()
    if not report:
        print("Report SV001 not found. Cannot seed report files.")
        return

    files_data = [
        {"name_file": "report_a_file1.pdf", "path_storage": "/files/report_a_file1.pdf", "report_id": report.id},
        {"name_file": "report_a_file2.pdf", "path_storage": "/files/report_a_file2.pdf", "report_id": report.id},
    ]

    for f in files_data:
        file_record = db.query(ReportFile).filter(ReportFile.name_file == f["name_file"], ReportFile.report_id == f["report_id"]).first()
        if not file_record:
            file_record = ReportFile(**f)
            db.add(file_record)
    db.commit()
    print("Seed report files completed!")

# ---------------- Run ----------------
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    seed_roles(db)
    seed_users(db)
    seed_exams(db)
    seed_reports(db)
    seed_report_files(db)   