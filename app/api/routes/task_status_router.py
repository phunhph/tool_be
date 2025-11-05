import redis
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db import get_db
from app.api.routes.auth import require_role
from app.core.celery_app import celery_app

r = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)

status_router = APIRouter(prefix="/tasks")


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

    task_keys = [key for key in r.scan_iter(match="task:*") if not any(s in key for s in [":file:", ":files"])]

    all_tasks = []
    total_pdf = 0
    total_done = 0
    total_failed = 0
    total_pending = 0

    for key in task_keys:
        task_info = r.hgetall(key)
        if not task_info:
            continue

        task_id = key.split(":")[1]
        files = list(r.smembers(f"task:{task_id}:files"))
        file_results = []

        for fname in files:
            fdata = r.hgetall(f"task:{task_id}:file:{fname}")
            if fdata:
                file_results.append(fdata)

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
