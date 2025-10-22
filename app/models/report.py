from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, func
from sqlalchemy.orm import relationship
import enum
from app.db import Base

class ReportStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    plagiarized = "plagiarized"

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    student_code = Column(String(50), nullable=False)
    major = Column(String(255))
    position = Column(String(255))
    strengths = Column(Text)
    weaknesses = Column(Text)
    proposal = Column(Text)
    attitude_score = Column(Integer)
    work_score = Column(Integer)
    note = Column(Text)
    status = Column(
        Enum(ReportStatus, native_enum=False, create_type=False),
        default=ReportStatus.pending,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100))
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)

    exam = relationship("Exam", back_populates="reports")
    files = relationship("ReportFile", back_populates="report", cascade="all, delete")
