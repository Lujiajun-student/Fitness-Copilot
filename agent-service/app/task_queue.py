"""Celery broker configuration; imported by API and the independent worker."""

import os
from celery import Celery
from app.config import get_settings

# config imports .env before reading broker settings.
TASK_TIMEOUT = int(os.getenv("PLAN_TASK_TIMEOUT_SECONDS", "1800"))
celery_app = Celery("fitness_plans", broker=os.getenv("REDIS_URL") or "redis://127.0.0.1:6379/0",
                    include=["app.worker"])
celery_app.conf.update(
    task_serializer="json", accept_content=["json"],
    task_default_queue="fitness-plans", task_ignore_result=True,
    task_acks_late=True, task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": TASK_TIMEOUT + 120},
    task_publish_retry=False,
    broker_connection_timeout=3,
)


def enqueue_plan(user_id, task_id, state):
    celery_app.send_task("fitness.generate_plan", args=[user_id, task_id, state], task_id=task_id)
