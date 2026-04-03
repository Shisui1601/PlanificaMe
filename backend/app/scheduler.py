"""
scheduler.py — Tareas programadas que corren dentro del proceso FastAPI.
Usa APScheduler (BackgroundScheduler) directamente en el proceso uvicorn.
Sin necesidad de Celery worker externo — funciona en un solo contenedor.

Timezone: America/Santo_Domingo (UTC-4, sin DST)
"""
from .database import SessionLocal, Event, User
from .services.mail_service import MailService
from .utils.helpers import time_to_minutes
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

TZ = pytz.timezone("America/Santo_Domingo")


# ════════════════════════════════════════
# 1. RECORDATORIOS (cada 60 segundos)
# ════════════════════════════════════════

def run_reminders():
    """
    Revisa cada minuto si hay eventos que necesitan recordatorio.
    Compara la hora actual (hora local Santo Domingo) con la hora del evento
    para evitar el desfase de 4 horas que ocurría con utcnow().
    """
    db = SessionLocal()
    try:
        now = datetime.now(TZ)
        today = now.strftime("%Y-%m-%d")
        current_minutes = now.hour * 60 + now.minute

        events = db.query(Event).filter(
            Event.date == today,
            Event.email != None,
            Event.email != "",
            Event.reminder_sent == False,
        ).all()

        sent_count = 0
        for event in events:
            try:
                if not event.time or event.reminder is None:
                    continue

                event_minutes = time_to_minutes(event.time)
                reminder_time = event_minutes - event.reminder

                # Ventana de ±1 minuto para capturar la tarea
                if abs(current_minutes - reminder_time) <= 1:
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
                        logger.info(
                            f"✉️  Recordatorio enviado → {event.title} "
                            f"({event.email}) | hora evento: {event.time} "
                            f"| recordatorio: {event.reminder}min antes"
                        )
            except Exception as e:
                logger.error(f"Error en recordatorio {getattr(event, 'id', '?')}: {e}")

        if sent_count:
            logger.info(f"📬 {sent_count} recordatorio(s) enviado(s) a las {now.strftime('%H:%M')}")

    except Exception as e:
        logger.error(f"Error crítico en run_reminders: {e}")
    finally:
        db.close()


# ════════════════════════════════════════
# 2. ALERTAS DE DEADLINE (cada hora)
# ════════════════════════════════════════

def run_deadline_check():
    """
    Revisa cada hora las fechas límite próximas o vencidas.
    Notifica en los días: 7, 3, 1, 0 (hoy) y -1 (vencido).
    """
    db = SessionLocal()
    try:
        today = datetime.now(TZ).date()

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
                        logger.info(f"⏳ Deadline alert → {event.title} ({days_left} días)")
            except Exception as e:
                logger.error(f"Error en deadline {getattr(event, 'id', '?')}: {e}")

        if sent_count:
            logger.info(f"📬 {sent_count} alerta(s) de deadline enviada(s)")

    except Exception as e:
        logger.error(f"Error crítico en run_deadline_check: {e}")
    finally:
        db.close()


# ════════════════════════════════════════
# 3. LIMPIEZA DIARIA (2am)
# ════════════════════════════════════════

def run_cleanup():
    """Resetea reminder_sent para eventos pasados."""
    db = SessionLocal()
    try:
        yesterday = (datetime.now(TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        updated = db.query(Event).filter(
            Event.date < yesterday,
            Event.reminder_sent == True
        ).update({"reminder_sent": False})
        db.commit()
        logger.info(f"🧹 Limpieza: {updated} recordatorio(s) reseteado(s)")
    except Exception as e:
        logger.error(f"Error en run_cleanup: {e}")
    finally:
        db.close()
