import redis, json, asyncio
from app.services.websocket_manager import manager
from app.core.celery_app import celery_app

r = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)

@celery_app.task(bind=True)
def process_uploaded_archive(self, exam_id: int, folder_path: str, file_metadata: list, username: str):
    task_id = self.request.id
    total_pdfs = len(file_metadata)

    r.sadd(f"exam:{exam_id}:tasks", task_id)
    r.hset(f"task:{task_id}", mapping={
        "exam_id": exam_id,
        "username": username,
        "status": "PENDING",
        "pdf_total": total_pdfs,
        "pdf_done": 0,
        "pdf_failed": 0,
        "pdf_pending": total_pdfs,
        "progress": 0,
    })

    # Lưu danh sách file
    for f in file_metadata:
        filename = f.get("filename")
        r.sadd(f"task:{task_id}:files", filename)
        r.hset(f"task:{task_id}:file:{filename}", mapping={
            "filename": filename,
            "status": "PENDING",
            "result": "",
            "error": ""
        })

    # Giả lập xử lý từng file PDF
    for i, pdf in enumerate(file_metadata, start=1):
        filename = pdf.get("filename")

        try:
            # TODO: xử lý thực tế
            result_text = f"Đã xử lý {filename}"
            r.hset(f"task:{task_id}:file:{filename}", mapping={
                "status": "DONE",
                "result": result_text
            })
            r.hincrby(f"task:{task_id}", "pdf_done", 1)

        except Exception as e:
            r.hset(f"task:{task_id}:file:{filename}", mapping={
                "status": "FAILED",
                "error": str(e)
            })
            r.hincrby(f"task:{task_id}", "pdf_failed", 1)

        finally:
            done = int(r.hget(f"task:{task_id}", "pdf_done"))
            failed = int(r.hget(f"task:{task_id}", "pdf_failed"))
            total = int(r.hget(f"task:{task_id}", "pdf_total"))
            pending = total - done - failed
            progress = round((done + failed) / total * 100, 2)
            r.hset(f"task:{task_id}", mapping={
                "pdf_pending": pending,
                "progress": progress,
                "status": "PROCESSING"
            })

    r.hset(f"task:{task_id}", "status", "COMPLETED")
    return {"task_id": task_id, "status": "COMPLETED"}
