"""Celery application configuration for background task processing.

This module sets up Celery with Redis as the message broker and result backend.
All tasks must maintain tenant isolation and proper error handling.
"""

import logging
from celery import Celery
from kombu import Queue

from genreport.core.utils.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery application
celery_app = Celery(
    "genreport",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["genreport.core.tasks.parsing_tasks"],
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit

    # Retry settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,

    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory cleanup)

    # Queue settings
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="task.#"),
        Queue("parsing", routing_key="parsing.#"),
        Queue("celery", routing_key="celery.#"),
    ),

    # Routing
    task_routes={
        "genreport.core.tasks.parsing_tasks.parse_excel_file_task": {
            "queue": "parsing",
            "routing_key": "parsing.excel",
        },
    },
)

logger.info(f"Celery app initialized with broker: {settings.redis_url}")
