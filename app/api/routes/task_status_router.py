# app/api/routes/task_status_router.py

from fastapi import APIRouter, Depends, HTTPException
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

# 🚨 ĐẢM BẢO CÁC IMPORTS NÀY KHỚP VỚI CẤU TRÚC AUTH VÀ DB CỦA BẠN 🚨
from app.db import get_db 
from app.api.routes.auth import require_role
from app.core.celery_app import celery_app 

status_router = APIRouter(prefix="/tasks")

# ... (Hàm get_task_status_by_id giữ nguyên hoặc loại bỏ nếu không dùng)

@status_router.get(
    "/status/all",
    summary="Trạng thái hàng đợi và tiến độ toàn hệ thống",
    description="Lấy danh sách các tác vụ đang hoạt động, chờ, hoặc được lên lịch. Dành cho Super Admin để giám sát hiệu suất Celery.",
    response_model=Dict[str, Any]
)
def get_all_active_task_statuses(
    db: Session = Depends(get_db), 
    _: str = Depends(require_role(["super_admin"])), # 🚨 CHỈ SUPER ADMIN MỚI XEM ĐƯỢC
):
    """Lấy danh sách và trạng thái của TẤT CẢ các tác vụ đang hoạt động/chờ."""
    
    i = celery_app.control.inspect()
    
    # 1. Lấy trạng thái từ Worker (Active, Scheduled, Reserved)
    active_tasks = i.active() or {}
    scheduled_tasks = i.scheduled() or {}
    reserved_tasks = i.reserved() or {} # Các tác vụ đang chờ được Worker xử lý
    
    # 2. Lấy các tác vụ gần đây đã hoàn thành (từ Celery Backend/Redis)
    # Vì việc query tất cả tác vụ hoàn thành là RẤT NẶNG, ta chỉ lấy các tác vụ đang hoạt động
    
    all_tasks = []

    # Hàm trích xuất thông tin từ Celery Worker
    def extract_task_info(task_dict_by_worker: Dict[str, List[Dict[str, Any]]], status_override: str):
        for worker, tasks in task_dict_by_worker.items():
            for task in tasks:
                task_id = task['id']
                result = AsyncResult(task_id, app=celery_app)
                
                # Cẩn thận khi truy vấn result.info: Dùng .info (meta) cho PROGRESS
                meta = {}
                if result.state == 'PROGRESS' and isinstance(result.info, dict):
                     meta = result.info
                
                # Mặc định: status là status_override
                current_status = result.state if result.state not in ['PENDING', 'PROGRESS'] else status_override

                all_tasks.append({
                    "task_id": task_id,
                    "status": current_status,
                    "worker": worker,
                    # Lấy thông tin tiến độ
                    "exam_id": meta.get('exam_id', 'N/A'),
                    "progress_percent": meta.get('percent', 0),
                    "total_files": meta.get('total', 'N/A'),
                    "current_file_count": meta.get('current', 0)
                })

    # 1. Tác vụ Đang Xử lý (Active - Đã được Worker nhận và đang chạy)
    extract_task_info(active_tasks, "PROCESSING")
    
    # 2. Tác vụ Đang Chờ (Scheduled - Chờ thời gian; Reserved - Chờ Worker rảnh)
    extract_task_info(scheduled_tasks, "SCHEDULED")
    extract_task_info(reserved_tasks, "QUEUED")


    return {
        "status": True,
        "total_active_tasks": len(all_tasks),
        "tasks": all_tasks
    }