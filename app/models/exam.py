from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.db import Base
from sqlalchemy.orm import relationship

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)  
    name = Column(String(255), nullable=False)  
    start_time = Column(DateTime, nullable=False)  
    end_time = Column(DateTime, nullable=False)    
    is_delete = Column(Boolean, default=False)     

    reports = relationship("Report", back_populates="exam", cascade="all, delete")
