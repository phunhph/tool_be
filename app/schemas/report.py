from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ReportStatus(str, Enum):
    pending = "pending"
    checked = "checked"
    plagiarized = "plagiarized"
    approved = "approved"

class ReportFileResponse(BaseModel):
    id: int
    name_file: str
    path_storage: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReportBase(BaseModel):
    name: Optional[str]
    student_code: Optional[str]
    major: Optional[str]
    position: Optional[str]
    advantage: Optional[str]
    disadvantage: Optional[str]
    suggestion: Optional[str]
    note: Optional[str]
    attitude_point: Optional[int]
    work_point: Optional[int]
    status: Optional[ReportStatus]
    exam_id: Optional[int]

class ReportCreate(ReportBase):
    status: ReportStatus = ReportStatus.pending
    pass

class ReportUpdate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    created_at: datetime
    files: List[ReportFileResponse] = []

    class Config:
        from_attributes = True

class ReportFileSchema(BaseModel):
    id: int
    name_file: str
    path_storage: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True