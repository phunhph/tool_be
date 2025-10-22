from pydantic import BaseModel
from typing import Optional, List, Generic, TypeVar
from pydantic.generics import GenericModel
from datetime import datetime
from app.schemas.base_schemas import DetailResponse,CreateResponse, ListResponse
T = TypeVar("T")

# ==========================
# Exam schema
# ==========================
class ExamResponse(BaseModel):
    id: int
    name: str
    code: str
    start_time: datetime
    end_time: datetime

    class Config:
        from_attributes = True

class ExamCreate(BaseModel):
    name: str
    code: str
    start_time: datetime
    end_time: datetime

class ExamUpdate(BaseModel):
    name: Optional[str]
    code: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]

class CreateResponse(BaseModel):
    message: str
    status: bool
    examId: int

class UpdateResponse(BaseModel):
    message: str
    status: bool
    data: ExamResponse

class DeleteResponse(BaseModel):
    message: str
    status: bool
    examId: int
