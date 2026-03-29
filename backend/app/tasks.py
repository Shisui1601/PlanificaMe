"""
tasks.py — Tareas programadas de Celery para PlanificaMe
Se ejecutan automáticamente según el schedule definido en celery_app.py
"""
from celery import shared_task
from .database import SessionLocal, Event, User, Calendar, CalendarMember
from .services.mail_service import MailService
from .utils.helpers import time_to_minutes
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ════════════════════════════════════════
# 1. RECORDATORIOS (cada minuto)
# ════════════════════════════════════════

@shared_task(bind=True, max_retries=3, name="app.tasks.send_event_reminders")
def send_event_reminders(self):
    """
    Revisa cada minuto si hay eventos que necesitan recordatorio.
    Envía el correo N minutos antes de que inicie la actividad.
    """
    try:
        db = SessionLocal()
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        current_minutes = now.hour * 60 + now.minute

        events = db.query(Event).filter(
            Event.date == today,
            Event.email != None,
            Event.reminder_sent == False,
            Event.email != ""
        ).all()

        sent_count = 0
        for event in events:
            try:
                event_minutes = time_to_minutes(event.time)
                reminder_time = event_minutes - event.reminder

                if abs(current_minutes - reminder_time) < 2:
                    success = MailService.send_reminder_email(
                        event_title=event.title,
                        to_email=event.email,
                        event_date=event.date,
                        event_time=event.time,
                        reminder_minutes=event.reminder
                    )
                    if success:
                        event.reminder_sent = True
                        db.commit()
                        sent_count += 1
                        logger.info(f"✉️  Recordatorio → {event.title} ({event.email})")

            except Exception as e:
                logger.error(f"Error procesando recordatorio {event.id}: {str(e)}")
                continue

        db.close()
        return {"status": "success", "sent": sent_count}

    except Exception as exc:
        logger.error(f"Error en send_event_reminders: {str(exc)}")
        raise self.retry(countdown=60, exc=exc)


# ════════════════════════════════════════
# 2. ALERTAS DE DEADLINE (cada hora)
# ════════════════════════════════════════

@shared_task(bind=True, max_retries=3, name="app.tasks.check_upcoming_deadlines")
def check_upcoming_deadlines(self):
    """
    Revisa cada hora las fechas límite próximas o vencidas.
    Notifica en los días: 7, 3, 1, 0 (hoy) y -1 (vencido).
    """
    try:
        db = SessionLocal()
        today = datetime.today().date()

        events = db.query(Event).filter(
            Event.deadline_date != None,
            Event.email != None,
            Event.email != "",
            Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
        ).all()

        sent_count = 0
        for event in events:
            try:
                deadline = datetime.strptime(event.deadline_date, "%Y-%m-%d").date()
                days_left = (deadline - today).days

                if days_left in [7, 3, 1, 0, -1]:
                    success = MailService.send_deadline_warning_email(
                        event_title=event.title,
                        to_email=event.email,
                        days_left=days_left,
                        deadline_date=event.deadline_date
                    )
                    if success:
                        sent_count += 1
                        logger.info(f"⏳ Deadline alert → {event.title} (días: {days_left})")

            except Exception as e:
                logger.error(f"Error procesando deadline {event.id}: {str(e)}")
                continue

        db.close()
        return {"status": "success", "sent": sent_count}

    except Exception as exc:
        logger.error(f"Error en check_upcoming_deadlines: {str(exc)}")
        raise self.retry(countdown=300, exc=exc)


# ════════════════════════════════════════
# 3. NOTIFICACIÓN DE ESTADO (inmediata)
# ════════════════════════════════════════

@shared_task(bind=True, max_retries=2, name="app.tasks.send_status_update_notification")
def send_status_update_notification(self, event_id: str, status: str, status_note: str = None):
    """
    Se llama inmediatamente cuando alguien actualiza el estado de un evento.
    Solo envía si el evento tiene email configurado.
    """
    try:
        db = SessionLocal()
        event = db.query(Event).filter(Event.id == event_id).first()

        if event and event.email:
            success = MailService.send_status_update_email(
                event_title=event.title,
                to_email=event.email,
                status=status,
                status_note=status_note
            )
            if success:
                logger.info(f"📊 Estado notificado → {event.title} = {status}")

        db.close()
        return {"status": "success", "event_id": event_id}

    except Exception as exc:
        logger.error(f"Error en send_status_update_notification: {str(exc)}")
        raise self.retry(countdown=30, exc=exc)


# ════════════════════════════════════════
# 4. RESUMEN SEMANAL (lunes a las 8am)
# ════════════════════════════════════════

@shared_task(bind=True, name="app.tasks.send_weekly_summaries")
def send_weekly_summaries(self):
    """
    Envía el resumen semanal a todos los usuarios activos cada lunes a las 8am.
    """
    try:
        db = SessionLocal()
        today = datetime.today().date()
        week_end = today + timedelta(days=7)
        week_start = today - timedelta(days=7)

        week_label = f"{today.strftime('%d/%m')} — {week_end.strftime('%d/%m/%Y')}"

        users = db.query(User).filter(
            User.is_active == True,
            User.email != None,
            User.email != ""
        ).all()

        sent_count = 0
        for user in users:
            try:
                # Eventos próximos (próximos 7 días)
                upcoming = db.query(Event).filter(
                    Event.creator_id == user.id,
                    Event.date >= today.strftime("%Y-%m-%d"),
                    Event.date <= week_end.strftime("%Y-%m-%d"),
                    Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
                ).order_by(Event.date, Event.time).all()

                # Completadas esta semana
                completed_count = db.query(Event).filter(
                    Event.creator_id == user.id,
                    Event.updated_at >= datetime.combine(week_start, datetime.min.time()),
                    Event.status.in_(["completed", "early-voluntary", "early-forced"])
                ).count()

                # Vencidas
                overdue = db.query(Event).filter(
                    Event.creator_id == user.id,
                    Event.deadline_date < today.strftime("%Y-%m-%d"),
                    Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
                ).all()

                upcoming_data = [{"title": e.title, "date": e.date, "time": e.time, "type": e.type} for e in upcoming]
                overdue_data = [{"title": e.title, "deadline_date": e.deadline_date} for e in overdue]

                success = MailService.send_weekly_summary_email(
                    to_email=user.email,
                    user_name=user.name,
                    upcoming_events=upcoming_data,
                    overdue_events=overdue_data,
                    completed_this_week=completed_count,
                    week_label=week_label
                )
                if success:
                    sent_count += 1
                    logger.info(f"📊 Resumen semanal → {user.name} ({user.email})")

            except Exception as e:
                logger.error(f"Error enviando resumen a {user.email}: {str(e)}")
                continue

        db.close()
        return {"status": "success", "sent": sent_count, "total_users": len(users)}

    except Exception as exc:
        logger.error(f"Error en send_weekly_summaries: {str(exc)}")
        return {"status": "error", "message": str(exc)}


# ════════════════════════════════════════
# 5. LIMPIEZA DE RECORDATORIOS (diario)
# ════════════════════════════════════════

@shared_task(bind=True, name="app.tasks.cleanup_old_reminders")
def cleanup_old_reminders(self):
    """Resetea reminder_sent para eventos pasados (para no dejar basura en BD)"""
    try:
        db = SessionLocal()
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        updated = db.query(Event).filter(
            Event.date < yesterday,
            Event.reminder_sent == True
        ).update({"reminder_sent": False})

        db.commit()
        db.close()
        logger.info(f"🧹 Limpieza: {updated} recordatorios reseteados")
        return {"status": "success", "reset": updated}

    except Exception as exc:
        logger.error(f"Error en cleanup_old_reminders: {str(exc)}")
        return {"status": "error", "message": str(exc)}