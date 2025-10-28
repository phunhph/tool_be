import asyncio
from typing import Any, Dict, List
from celery import current_task
from app.core.celery_app import celery_app
from app.services.websocket_manager import manager


# Hàm helper để Celery Worker báo cáo trạng thái lên Backend
async def update_progress(task, current_count, total_count, exam_id):
    """Cập nhật trạng thái và tiến độ lên Celery Backend VÀ WebSocket."""
    progress_percent = (current_count / total_count) * 100
    task_id = task.request.id

    # 1. Cập nhật Celery State
    task.update_state(
        state="PROGRESS",
        meta={
            "current": current_count,
            "total": total_count,
            "percent": f"{progress_percent:.2f}",
            "exam_id": exam_id,
        },
    )

    # 2. Gửi qua WebSocket
    await manager.send_update_to_client(
        task_id,
        {"progress": progress_percent, "current": current_count, "total": total_count},
    )


@celery_app.task(bind=True)
def process_uploaded_archive(self, exam_id: str, folder_path: str, file_metadata: list, username: str):
    """Tác vụ Celery chạy ngầm để xử lý toàn bộ file (đồng bộ hóa async)."""
    from app.services.report_service import ReportService  # Import ở đây để tránh vòng lặp import

    task_id = self.request.id
    total_files = len(file_metadata)

    # Gửi thông báo trạng thái ban đầu
    asyncio.run(manager.send_update_to_client(task_id, {
        "status": "PROCESSING",
        "task_id": task_id,
        "total_files": total_files,
    }))

    try:
        # CHẠY HÀM async TRONG HÀM ĐỒNG BỘ
        results = asyncio.run(
            ReportService.run_full_processing(
                self,
                exam_id,
                folder_path,
                file_metadata,
                update_progress
            )
        )

        # Gửi thông báo hoàn thành
        asyncio.run(manager.send_update_to_client(task_id, {
            "status": "COMPLETED",
            "task_id": task_id,
            "results": results["plagiarism_results"],
            "zip_file": results["zip_file"],
        }))

        return results

    except Exception as e:
        print(f"Celery Task Failed: {e}")

        asyncio.run(manager.send_update_to_client(task_id, {
            "status": "FAILED",
            "task_id": task_id,
            "error": str(e),
        }))

        raise
