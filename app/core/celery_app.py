# app/core/celery_app.py
from celery import Celery
from kombu import Queue

REDIS_BROKER = "redis://localhost:6379/0"
REDIS_BACKEND = "redis://localhost:6379/0"

celery_app = Celery(
    "report_processor",
    broker=REDIS_BROKER,
    backend=REDIS_BACKEND,
    include=["app.tasks.report_tasks"],
)
celery_app.autodiscover_tasks(["app.tasks"])
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,  # 1h timeout nếu task k hoàn tất
    },
    result_backend_transport_options={
        "retry_policy": {"timeout": 10.0}
    },

    # Cho phép task gửi dữ liệu tiến độ (state custom)
    task_track_started=True,
    task_ignore_result=False,
    result_expires=3600 * 6,  # 6 tiếng

    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,

    # Đặt queue riêng nếu muốn chia loại tác vụ
    task_queues=(
        Queue("default"),
        Queue("report"),
    ),
    task_default_queue="report",
)
