from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "opening_bell_workers",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(['app.workers'])

# Import scheduler after Celery app is configured to register periodic tasks
# This avoids circular imports by importing after the app is fully set up
try:
    import app.workers.scheduler
    print("CELERY APP: Scheduler module imported successfully")
except Exception as e:
    print(f"CELERY APP: Error importing scheduler: {e}")
