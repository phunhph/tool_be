# app/core/celery_app.py

from celery import Celery

# Giả định Redis đang chạy trên localhost:6379
celery_app = Celery(
    'report_processor',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['app.tasks.report_tasks'] # Đảm bảo Worker nạp file tasks
)

# Cấu hình để chấp nhận các kiểu dữ liệu phức tạp
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,
    # Giới hạn tốc độ Worker: 10 tasks mỗi 5 giây cho mỗi Worker (ví dụ)
    worker_prefetch_multiplier=1,
    task_acks_late=True 
)