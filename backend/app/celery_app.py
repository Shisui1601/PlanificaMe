"""
celery_app.py - Configuracion de Celery para PlanificaMe
"""
from celery import Celery
from celery.schedules import crontab
from .config import settings

celery_app = Celery(
    "planificame",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Santo_Domingo",
    enable_utc=False,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    beat_schedule={
        # Recordatorios cada minuto
        "send-reminders-every-minute": {
            "task": "app.tasks.send_event_reminders",
            "schedule": 60.0,
        },
        # Alertas de deadline cada hora
        "check-deadlines-hourly": {
            "task": "app.tasks.check_upcoming_deadlines",
            "schedule": 3600.0,
        },
        # Resumen semanal - lunes a las 8:00am hora local (12pm UTC)
        "weekly-summary-monday": {
            "task": "app.tasks.send_weekly_summaries",
            "schedule": crontab(hour=12, minute=0, day_of_week=1),
        },
        # Recordatorio diario para actividades 2+ dias - 10:00am hora local (14:00 UTC)
        "daily-advance-reminders": {
            "task": "app.tasks.send_daily_advance_reminders",
            "schedule": crontab(hour=14, minute=0),
        },
        # Limpieza diaria a las 2am hora local (06:00 UTC)
        "cleanup-reminders-daily": {
            "task": "app.tasks.cleanup_old_reminders",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)
