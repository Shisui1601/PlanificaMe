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
# HELPERS
# ════════════════════════════════════════

def _minutes_until_event(event_date: str, event_time: str) -> int:
    """
    Devuelve los minutos que faltan para que comience el evento.
    Negativo si ya comenzó.
    Usa hora local Santo Domingo (UTC-4).
    """
    try:
        event_dt = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
        now_local = datetime.utcnow() - timedelta(hours=4)
        diff = event_dt - now_local
        return int(diff.total_seconds() / 60)
    except Exception:
        return 9999


def _days_until_event(event_date: str) -> int:
    """Días que faltan para la fecha del evento. Negativo si ya pasó."""
    try:
        event_day = datetime.strptime(event_date, "%Y-%m-%d").date()
        today = (datetime.utcnow() - timedelta(hours=4)).date()
        return (event_day - today).days
    except Exception:
        return 9999


# ════════════════════════════════════════
# 1. RECORDATORIOS INTELIGENTES (cada minuto)
# ════════════════════════════════════════

@shared_task(bind=True, max_retries=3, name="app.tasks.send_event_reminders")
def send_event_reminders(self):
    """
    Revisa cada minuto si hay eventos que necesitan recordatorio.

    Lógica:
    - Si next_reminder_at es None: programa el primer envío cuando falten
      `reminder` minutos para el evento.
    - Si next_reminder_at <= ahora: envía y reprograma N minutos más tarde.
    - Si el evento ya comenzó: envía "en curso" y desactiva.
    - Si reminder_active == False: ignora.
    """
    try:
        db = SessionLocal()
        now_utc   = datetime.utcnow().replace(second=0, microsecond=0)
        now_local = now_utc - timedelta(hours=4)
        today     = now_local.strftime("%Y-%m-%d")

        # Eventos de hoy con email válido y recordatorios activos
        events = db.query(Event).filter(
            Event.date == today,
            Event.email.isnot(None),
            Event.email != "",
            Event.reminder_active.isnot(False),
            Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
        ).all()

        sent_count = 0

        for event in events:
            try:
                minutes_left = _minutes_until_event(event.date, event.time)

                # ── Caso A: inicializar next_reminder_at si no existe ──
                if event.next_reminder_at is None:
                    reminder_min = event.reminder or 15
                    # ¿Cuándo debería dispararse el primer recordatorio?
                    # = hora del evento - reminder minutos
                    first_trigger = minutes_left - reminder_min

                    if first_trigger <= 0:
                        # Ya es la hora o se pasó → disparar ahora
                        event.next_reminder_at = now_utc
                        db.commit()
                    # Si aún no, esperar al próximo ciclo
                    continue

                # ── Caso B: aún no es la hora ──
                if event.next_reminder_at > now_utc:
                    continue

                # ── Caso C: el evento terminó (pasó duración completa) ──
                duration = event.duration or 60
                if minutes_left < -(duration):
                    event.reminder_active = False
                    event.next_reminder_at = None
                    db.commit()
                    continue

                # ── Caso D: enviar recordatorio ──
                interval       = event.snooze_interval if event.snooze_interval is not None else 10
                reminder_count = (event.reminder_count or 0) + 1

                success = MailService.send_snooze_reminder_email(
                    event_title=event.title,
                    to_email=event.email,
                    event_date=event.date,
                    event_time=event.time,
                    event_id=str(event.id),
                    snooze_interval=interval,
                    reminder_count=reminder_count,
                    minutes_until_event=minutes_left,
                )

                if success:
                    event.reminder_count = reminder_count
                    event.reminder_sent  = True
                    sent_count += 1

                    if minutes_left <= 0:
                        # Actividad en curso → desactivar recordatorios
                        event.reminder_active   = False
                        event.next_reminder_at  = None
                        logger.info(f"🚨 Recordatorio 'en curso' → {event.title} ({event.email})")
                    else:
                        # Programar próximo recordatorio automático
                        event.next_reminder_at = now_utc + timedelta(minutes=interval)
                        logger.info(
                            f"✉️  Recordatorio #{reminder_count} → {event.title} "
                            f"({event.email}) | faltan {minutes_left} min | próximo en {interval} min"
                        )

                    db.commit()

            except Exception as e:
                logger.error(f"Error procesando recordatorio {event.id}: {str(e)}")
                db.rollback()
                continue

        db.close()
        return {"status": "success", "sent": sent_count}

    except Exception as exc:
        logger.error(f"Error en send_event_reminders: {str(exc)}")
        raise self.retry(countdown=60, exc=exc)


# ════════════════════════════════════════
# 2. RECORDATORIO DIARIO — actividades 2+ días (10am)
# ════════════════════════════════════════

@shared_task(bind=True, name="app.tasks.send_daily_advance_reminders")
def send_daily_advance_reminders(self):
    """
    Corre cada día a las 10:00 AM (hora Santo Domingo, UTC-4).
    Envía recordatorio diario a eventos que:
    - Faltan 2 o más días para su fecha
    - Tienen email configurado
    - reminder_active == True
    - No se les ha enviado el recordatorio diario HOY
    """
    try:
        db = SessionLocal()
        today = (datetime.utcnow() - timedelta(hours=4)).strftime("%Y-%m-%d")

        events = db.query(Event).filter(
            Event.email.isnot(None),
            Event.email != "",
            Event.reminder_active.isnot(False),
            Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
        ).all()

        sent_count = 0

        for event in events:
            try:
                days_left = _days_until_event(event.date)

                # Solo eventos que faltan 2 o más días
                if days_left < 2:
                    continue

                # No enviar si ya se mandó hoy
                if event.daily_reminder_sent_date == today:
                    continue

                success = MailService.send_daily_advance_reminder_email(
                    event_title=event.title,
                    to_email=event.email,
                    event_date=event.date,
                    event_time=event.time,
                    event_id=str(event.id),
                    days_until_event=days_left,
                )

                if success:
                    event.daily_reminder_sent_date = today
                    db.commit()
                    sent_count += 1
                    logger.info(
                        f"📆 Recordatorio diario → {event.title} "
                        f"({event.email}) | faltan {days_left} días"
                    )

            except Exception as e:
                logger.error(f"Error enviando recordatorio diario {event.id}: {str(e)}")
                db.rollback()
                continue

        db.close()
        return {"status": "success", "sent": sent_count}

    except Exception as exc:
        logger.error(f"Error en send_daily_advance_reminders: {str(exc)}")
        return {"status": "error", "message": str(exc)}


# ════════════════════════════════════════
# 3. ALERTAS DE DEADLINE (cada hora)
# ════════════════════════════════════════

@shared_task(bind=True, max_retries=3, name="app.tasks.check_upcoming_deadlines")
def check_upcoming_deadlines(self):
    """
    Revisa cada hora las fechas límite próximas o vencidas.
    Notifica en los días: 7, 3, 1, 0 (hoy) y -1 (vencido).
    """
    try:
        db = SessionLocal()
        today = (datetime.utcnow() - timedelta(hours=4)).date()

        events = db.query(Event).filter(
            Event.deadline_date.isnot(None),
            Event.email.isnot(None),
            Event.email != "",
            Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
        ).all()

        sent_count = 0
        for event in events:
            try:
                deadline  = datetime.strptime(event.deadline_date, "%Y-%m-%d").date()
                days_left = (deadline - today).days

                if days_left in [7, 3, 1, 0, -1]:
                    success = MailService.send_deadline_warning_email(
                        event_title=event.title,
                        to_email=event.email,
                        days_left=days_left,
                        deadline_date=event.deadline_date,
                        event_id=str(event.id)
                    )
                    if success:
                        sent_count += 1
                        logger.info("Deadline alert -> %s (dias: %d)" % (event.title, days_left))

            except Exception as e:
                logger.error(f"Error procesando deadline {event.id}: {str(e)}")
                continue

        db.close()
        return {"status": "success", "sent": sent_count}

    except Exception as exc:
        logger.error(f"Error en check_upcoming_deadlines: {str(exc)}")
        raise self.retry(countdown=300, exc=exc)


# ================================================
# 4. NOTIFICACION DE ESTADO (inmediata)
# ================================================

@shared_task(bind=True, max_retries=2, name="app.tasks.send_status_update_notification")
def send_status_update_notification(self, event_id: str, status: str, status_note: str = None):
    """Se llama cuando alguien actualiza el estado de un evento."""
    try:
        db = SessionLocal()
        event = db.query(Event).filter(Event.id == event_id).first()

        if event and event.email:
            success = MailService.send_status_update_email(
                event_title=event.title,
                to_email=event.email,
                status=status,
                status_note=status_note,
                event_id=str(event.id)
            )
            if success:
                logger.info("Estado notificado -> %s = %s" % (event.title, status))

        db.close()
        return {"status": "success", "event_id": event_id}

    except Exception as exc:
        logger.error(f"Error en send_status_update_notification: {str(exc)}")
        raise self.retry(countdown=30, exc=exc)


# ================================================
# 5. RESUMEN SEMANAL (lunes a las 8am)
# ================================================

@shared_task(bind=True, name="app.tasks.send_weekly_summaries")
def send_weekly_summaries(self):
    """Envia el resumen semanal a todos los usuarios activos cada lunes a las 8am."""
    try:
        db = SessionLocal()
        today      = (datetime.utcnow() - timedelta(hours=4)).date()
        week_end   = today + timedelta(days=7)
        week_start = today - timedelta(days=7)
        week_label = "%s - %s" % (today.strftime("%d/%m"), week_end.strftime("%d/%m/%Y"))

        users = db.query(User).filter(
            User.is_active == True,
            User.email.isnot(None),
            User.email != ""
        ).all()

        sent_count = 0
        for user in users:
            try:
                upcoming = db.query(Event).filter(
                    Event.creator_id == user.id,
                    Event.date >= today.strftime("%Y-%m-%d"),
                    Event.date <= week_end.strftime("%Y-%m-%d"),
                    Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
                ).order_by(Event.date, Event.time).all()

                completed_count = db.query(Event).filter(
                    Event.creator_id == user.id,
                    Event.updated_at >= datetime.combine(week_start, datetime.min.time()),
                    Event.status.in_(["completed", "early-voluntary", "early-forced"])
                ).count()

                overdue = db.query(Event).filter(
                    Event.creator_id == user.id,
                    Event.deadline_date < today.strftime("%Y-%m-%d"),
                    Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
                ).all()

                upcoming_data = [{"title": e.title, "date": e.date, "time": e.time, "type": e.type} for e in upcoming]
                overdue_data  = [{"title": e.title, "deadline_date": e.deadline_date} for e in overdue]

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
                    logger.info("Resumen semanal -> %s (%s)" % (user.name, user.email))

            except Exception as e:
                logger.error(f"Error enviando resumen a {user.email}: {str(e)}")
                continue

        db.close()
        return {"status": "success", "sent": sent_count, "total_users": len(users)}

    except Exception as exc:
        logger.error(f"Error en send_weekly_summaries: {str(exc)}")
        return {"status": "error", "message": str(exc)}


# ================================================
# 6. LIMPIEZA DE RECORDATORIOS (diario a las 2am)
# ================================================

@shared_task(bind=True, name="app.tasks.cleanup_old_reminders")
def cleanup_old_reminders(self):
    """Resetea los campos de recordatorio para eventos que ya pasaron."""
    try:
        db = SessionLocal()
        yesterday = ((datetime.utcnow() - timedelta(hours=4)) - timedelta(days=1)).strftime("%Y-%m-%d")

        updated = db.query(Event).filter(
            Event.date < yesterday,
            Event.reminder_sent == True
        ).update({
            "reminder_sent":            False,
            "reminder_count":           0,
            "next_reminder_at":         None,
            "reminder_active":          True,
            "daily_reminder_sent_date": None,
        })

        db.commit()
        db.close()
        logger.info("Limpieza: %d eventos reseteados" % updated)
        return {"status": "success", "reset": updated}

    except Exception as exc:
        logger.error(f"Error en cleanup_old_reminders: {str(exc)}")
        return {"status": "error", "message": str(exc)}
