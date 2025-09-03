import logging
from celery.schedules import crontab, timedelta
from app.workers.celery_app import celery_app

print("SCHEDULER: Module loaded successfully!")
logger = logging.getLogger(__name__)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    logger.info("Setting up periodic tasks...")
    
    # Fetch all filings from all companies every 1 minute for testing
    sender.add_periodic_task(
        timedelta(minutes=1),  # Every 1 minute for testing
        sender.signature('app.workers.edgar_processing.edgar_worker.fetch_all_companies_filings', kwargs={'days_back': 90}),
        name="fetch-all-filings-every-1-minute-testing"
    )
    
    # Process pending filings every 1 minute for testing
    sender.add_periodic_task(
        timedelta(minutes=1),  # Every 1 minute for testing
        sender.signature('app.workers.content_worker.process_pending_filings'),
        name="process-pending-filings-every-1-minute-testing"
    )
    
    logger.info("Periodic tasks configured successfully")
    logger.info(f"Total periodic tasks: {len(sender.conf.beat_schedule)}")
    
    # Log the schedule for debugging
    for task_name, task_config in sender.conf.beat_schedule.items():
        logger.info(f"Scheduled task: {task_name} - {task_config}")
