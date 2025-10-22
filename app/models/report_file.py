from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db import Base

class ReportFile(Base):
    __tablename__ = "report_files"

    id = Column(Integer, primary_key=True, index=True)
    name_file = Column(String(255), nullable=False)
    path_storage = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)

    report = relationship("Report", back_populates="files")
