from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate, CreateResponse, UpdateResponse, DeleteResponse, ExamResponse
from app.schemas.base_schemas import ListResponse, DetailResponse

def raise_error(status: int, message: str):
    raise HTTPException(status_code=status, detail={"status": status, "message": message})

class ExamService:

    @staticmethod
    def get_list(db: Session, page: int = 1, page_size: int = 20) -> ListResponse[ExamResponse]:
        query = db.query(Exam).filter(Exam.is_delete == False)
        total = query.count()
        exams = query.offset((page - 1) * page_size).limit(page_size).all()
        return ListResponse(
            data=exams,
            total=total,
            pageSize=page_size,
            pageIndex=page
        )

    @staticmethod
    def get_detail(db: Session, exam_id: int) -> DetailResponse[ExamResponse]:
        exam = db.query(Exam).filter(Exam.id == exam_id, Exam.is_delete == False).first()
        if not exam:
            raise_error(404, "Kỳ thi không tồn tại")
        return DetailResponse(
            status=True,
            data=exam
        )

    @staticmethod
    def create(db: Session, payload: ExamCreate) -> CreateResponse:
        exists = db.query(Exam).filter(Exam.code == payload.code).first()
        if exists:
            raise_error(400, "Mã kỳ thi đã tồn tại")
        exam = Exam(**payload.dict())
        db.add(exam)
        db.commit()
        db.refresh(exam)
        return CreateResponse(
            message="Tạo kỳ thi thành công",
            status=True,
            examId=exam.id
        )

    @staticmethod
    def update(db: Session, exam_id: int, payload: ExamUpdate) -> UpdateResponse:
        exam = db.query(Exam).filter(Exam.id == exam_id, Exam.is_delete == False).first()
        if not exam:
            raise_error(404, "Kỳ thi không tồn tại")
        for key, value in payload.dict(exclude_unset=True).items():
            setattr(exam, key, value)
        db.commit()
        db.refresh(exam)
        return UpdateResponse(
            message="Cập nhật kỳ thi thành công",
            status=True,
            data=exam
        )

    @staticmethod
    def delete(db: Session, exam_id: int) -> DeleteResponse:
        exam = db.query(Exam).filter(Exam.id == exam_id, Exam.is_delete == False).first()
        if not exam:
            raise_error(404, "Kỳ thi không tồn tại")
        exam.is_delete = True
        db.commit()
        return DeleteResponse(
            message="Xóa kỳ thi thành công",
            status=True,
            examId=exam.id
        )
