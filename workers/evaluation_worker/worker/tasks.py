"""Tasks consumed from the evaluation queue are registered by the backend package."""

from app.jobs.queue import celery_app

__all__ = ["celery_app"]
