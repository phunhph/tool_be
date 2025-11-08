import redis
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.db import get_db
from app.api.routes.auth import require_role
from app.core.celery_app import celery_app
from app.schemas.report import TaskStatusResponse

logger = logging.getLogger(__name__)

r = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)

status_router = APIRouter(prefix="/tasks", tags=["Tasks"])


@status_router.get(
    "/status/all",
    summary="Thống kê tiến độ xử lý PDF từ Redis",
    response_model=Dict[str, Any]
)
def get_all_active_task_statuses(
    db: Session = Depends(get_db),
    _: str = Depends(require_role(["super_admin"]))
):
    """Lấy danh sách và thống kê tiến độ của các task hiện có trong Redis."""

    task_keys = [
        key for key in r.scan_iter(match="task:*")
        if not any(s in key for s in [":file:", ":files"])
    ]

    all_tasks = []
    total_pdf = 0
    total_done = 0
    total_failed = 0
    total_pending = 0

    for key in task_keys:
        key_type = r.type(key)
        if key_type != 'hash':
            logger.warning(f"Key {key} không phải hash, bỏ qua type={key_type}")
            continue

        task_info = r.hgetall(key)
        if not task_info:
            continue

        task_id = key.split(":")[1]
        files = list(r.smembers(f"task:{task_id}:files"))
        file_results = []

        for fname in files:
            file_key = f"task:{task_id}:file:{fname}"
            file_type = r.type(file_key)
            if file_type != 'hash':
                logger.warning(f"File key {file_key} không phải hash, bỏ qua type={file_type}")
                continue

            fdata = r.hgetall(file_key)
            if fdata:
                # Parse result nếu là JSON
                result = fdata.get("result", "")
                if result:
                    try:
                        result = json.loads(result)
                    except:
                        pass

                file_results.append({
                    "filename": fdata.get("filename", ""),
                    "status": fdata.get("status", "PENDING"),
                    "result": result if result else None,
                    "error": fdata.get("error") or None
                })

        # Cộng dồn thống kê tổng
        pdf_total = int(task_info.get("pdf_total", 0))
        pdf_done = int(task_info.get("pdf_done", 0))
        pdf_failed = int(task_info.get("pdf_failed", 0))
        pdf_pending = int(task_info.get("pdf_pending", 0))

        total_pdf += pdf_total
        total_done += pdf_done
        total_failed += pdf_failed
        total_pending += pdf_pending

        all_tasks.append({
            "task_id": task_id,
            "exam_id": task_info.get("exam_id"),
            "username": task_info.get("username"),
            "status": task_info.get("status"),
            "progress": float(task_info.get("progress", 0)),
            "pdf_total": pdf_total,
            "pdf_done": pdf_done,
            "pdf_failed": pdf_failed,
            "pdf_pending": pdf_pending,
            "files": file_results
        })

    return {
        "status": True,
        "summary": {
            "total_tasks": len(all_tasks),
            "total_pdf": total_pdf,
            "done": total_done,
            "failed": total_failed,
            "pending": total_pending
        },
        "tasks": all_tasks
    }



@status_router.get(
    "/status/{task_id}",
    summary="Lấy trạng thái chi tiết của một task theo task_id",
    response_model=TaskStatusResponse
)
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_role(["admin", "master", "viewer"]))
):
    """
    Lấy trạng thái chi tiết của task xử lý PDF theo task_id.
    Trả về thông tin tiến độ, danh sách file, và kết quả xử lý.
    """
    # Lấy thông tin task từ Redis
    task_info = r.hgetall(f"task:{task_id}")
    
    if not task_info:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    
    # Lấy danh sách file
    files = list(r.smembers(f"task:{task_id}:files"))
    file_results = []
    
    for fname in files:
        fdata = r.hgetall(f"task:{task_id}:file:{fname}")
        if fdata:
            # Parse result nếu là JSON
            result = fdata.get("result", "")
            if result:
                try:
                    result = json.loads(result)
                except:
                    pass
            
            file_results.append({
                "filename": fdata.get("filename", ""),
                "status": fdata.get("status", "PENDING"),
                "result": result if result else None,
                "error": fdata.get("error") or None
            })
    
    # Lấy kết quả đạo văn nếu có
    plagiarism_data = r.get(f"task:{task_id}:plagiarism")
    plagiarism_results = []
    if plagiarism_data:
        try:
            plagiarism_list = json.loads(plagiarism_data)
            plagiarism_results = [
                {
                    "report_id_1": item.get("report_id_1"),
                    "report_id_2": item.get("report_id_2"),
                    "filename_1": item.get("filename_1", ""),
                    "filename_2": item.get("filename_2", ""),
                    "similarity": float(item.get("similarity", 0))
                }
                for item in plagiarism_list
            ]
        except Exception as e:
            logger.error(f"Lỗi parse plagiarism data: {e}")
    
    # Lấy thông tin từ Celery nếu có
    celery_state = "UNKNOWN"
    try:
        celery_task = celery_app.AsyncResult(task_id)
        celery_state = celery_task.state
    except Exception as e:
        logger.error(f"Lỗi lấy Celery state: {e}")
    
    return TaskStatusResponse(
        status=True,
        task_id=task_id,
        exam_id=task_info.get("exam_id", ""),
        username=task_info.get("username", ""),
        task_status=task_info.get("status", "UNKNOWN"),
        celery_state=celery_state,
        progress=float(task_info.get("progress", 0)),
        pdf_total=int(task_info.get("pdf_total", 0)),
        pdf_done=int(task_info.get("pdf_done", 0)),
        pdf_failed=int(task_info.get("pdf_failed", 0)),
        pdf_pending=int(task_info.get("pdf_pending", 0)),
        plagiarism_count=int(task_info.get("plagiarism_count", 0)),
        started_at=task_info.get("started_at"),
        completed_at=task_info.get("completed_at"),
        failed_at=task_info.get("failed_at"),
        error=task_info.get("error"),
        files=file_results,
        plagiarism_results=plagiarism_results,
    )
