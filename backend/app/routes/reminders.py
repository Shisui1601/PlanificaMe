"""
reminders.py — Endpoints para enviar recordatorios personalizados
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from ..database import SessionLocal, User, Event
from ..schemas.schemas import SendCustomReminderRequest, SendCustomReminderResponse
from ..services.mail_service import MailService
from ..auth import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reminders", tags=["reminders"])


# ════════════════════════════════════════
# ENVIAR RECORDATORIO PERSONALIZADO
# ════════════════════════════════════════

@router.post("/send", response_model=SendCustomReminderResponse)
def send_custom_reminder(
    reminder: SendCustomReminderRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Envía un recordatorio personalizado a uno o varios usuarios.

    **Parámetros:**
    - recipient_emails: Lista de emails destinatarios
    - subject: Asunto del recordatorio
    - message: Mensaje del recordatorio
    - reminder_type: Tipo (general, activity, task, question)
    - activity_id: ID de actividad si aplica
    - link_url: URL adicional si aplica

    **Ejemplo:**
    ```json
    {
      "recipient_emails": ["user@example.com"],
      "subject": "Revisión pendiente",
      "message": "Por favor revisa el documento que compartí",
      "reminder_type": "task",
      "activity_id": "abc123"
    }
    ```
    """
    try:
        # Validar que al menos un destinatario
        if not reminder.recipient_emails:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar al menos un destinatario"
            )

        # Validar que no haya más de 50 destinatarios
        if len(reminder.recipient_emails) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo 50 destinatarios por recordatorio"
            )

        # Validar emails (formato básico)
        for email in reminder.recipient_emails:
            if not isinstance(email, str) or "@" not in email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email inválido: {email}"
                )

        # Obtener nombre del remitente
        db = SessionLocal()
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        sender_name = user.name if user else "Un usuario de PlanificaMe"
        db.close()

        # Enviar recordatorio
        result = MailService.send_custom_reminder(
            to_emails=reminder.recipient_emails,
            subject=reminder.subject,
            message=reminder.message,
            sender_name=sender_name,
            reminder_type=reminder.reminder_type,
            activity_id=reminder.activity_id,
            activity_title=None,  # Se podría obtener de la BD si es necesario
            link_url=reminder.link_url
        )

        # Log del envío
        logger.info(
            f"📮 Recordatorio enviado por {sender_name}: "
            f"{len(result['sent_to'])} exitoso(s), "
            f"{result['total_failed']} fallido(s)"
        )

        return SendCustomReminderResponse(
            success=result["success"],
            message=f"Recordatorio enviado a {result['total_sent']} usuario(s)"
            if result["success"]
            else "No se pudo enviar el recordatorio",
            sent_to=result["sent_to"],
            failed=result.get("failed")
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error enviando recordatorio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al enviar el recordatorio"
        )


# ════════════════════════════════════════
# RECORDATORIO SOBRE ACTIVIDAD PENDIENTE
# ════════════════════════════════════════

@router.post("/activity/{activity_id}")
def send_activity_reminder(
    activity_id: str,
    reminder_request: dict,  # {"recipient_emails": [...], "message": "..."}
    current_user: dict = Depends(get_current_user)
):
    """
    Envía un recordatorio sobre una actividad específica a varios usuarios.

    **Parámetros:**
    - activity_id: ID de la actividad
    - recipient_emails: Lista de emails destinatarios
    - message: Mensaje personalizado
    """
    from ..database import Event

    try:
        db = SessionLocal()
        event = db.query(Event).filter(Event.id == activity_id).first()

        if not event:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Actividad no encontrada"
            )

        # Obtener nombre del remitente
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        sender_name = user.name if user else "Un usuario de PlanificaMe"
        db.close()

        # Enviar recordatorio
        result = MailService.send_custom_reminder(
            to_emails=reminder_request.get("recipient_emails", []),
            subject=f"Recordatorio: {event.title}",
            message=reminder_request.get("message", f"Te invito a revisar la actividad: {event.title}"),
            sender_name=sender_name,
            reminder_type="activity",
            activity_id=activity_id,
            activity_title=event.title
        )

        return {
            "success": result["success"],
            "message": f"Recordatorio enviado a {result['total_sent']} usuario(s)",
            "sent_to": result["sent_to"],
            "failed": result.get("failed")
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error enviando recordatorio de actividad: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al enviar el recordatorio"
        )


# ════════════════════════════════════════
# POSPONER RECORDATORIO (público, desde email)
# ════════════════════════════════════════

@router.get("/snooze/{event_id}", response_class=HTMLResponse)
def snooze_reminder(event_id: str):
    """
    Pospone el próximo recordatorio X minutos (según snooze_interval del evento).
    Se llama desde el botón del correo — no requiere autenticación.
    """
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()

        if not event:
            return HTMLResponse(_reminder_action_page(
                "❌ Actividad no encontrada",
                "No se encontró la actividad solicitada.",
                "#dc2626"
            ), status_code=404)

        if not event.reminder_active:
            return HTMLResponse(_reminder_action_page(
                "ℹ️ Recordatorios ya desactivados",
                f"Los recordatorios de <strong>{event.title}</strong> ya estaban desactivados.",
                "#8888aa"
            ))

        interval = event.snooze_interval or 10
        event.next_reminder_at = datetime.utcnow().replace(second=0, microsecond=0)
        from datetime import timedelta
        event.next_reminder_at = event.next_reminder_at + timedelta(minutes=interval)
        db.commit()

        logger.info(f"⏱️ Snooze aplicado: evento {event.id}, próximo en {interval} min")

        return HTMLResponse(_reminder_action_page(
            "⏱️ Recordatorio pospuesto",
            f"Te recordaremos sobre <strong>{event.title}</strong> en <strong>{interval} minutos</strong>.",
            "#7c5aff"
        ))

    except Exception as e:
        logger.error(f"Error en snooze_reminder: {e}")
        return HTMLResponse(_reminder_action_page(
            "❌ Error",
            "Ocurrió un error al posponer el recordatorio. Inténtalo nuevamente.",
            "#dc2626"
        ), status_code=500)
    finally:
        db.close()


# ════════════════════════════════════════
# DESACTIVAR RECORDATORIOS (público, desde email)
# ════════════════════════════════════════

@router.get("/disable/{event_id}", response_class=HTMLResponse)
def disable_reminder(event_id: str):
    """
    Desactiva todos los recordatorios futuros para el evento.
    Se llama desde el enlace del correo — no requiere autenticación.
    """
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()

        if not event:
            return HTMLResponse(_reminder_action_page(
                "❌ Actividad no encontrada",
                "No se encontró la actividad solicitada.",
                "#dc2626"
            ), status_code=404)

        event.reminder_active = False
        event.next_reminder_at = None
        db.commit()

        logger.info(f"🔕 Recordatorios desactivados: evento {event.id}")

        return HTMLResponse(_reminder_action_page(
            "🔕 Recordatorios desactivados",
            f"No recibirás más recordatorios automáticos de <strong>{event.title}</strong>.<br>"
            f"Puedes reactivarlos desde la aplicación si lo deseas.",
            "#10b981"
        ))

    except Exception as e:
        logger.error(f"Error en disable_reminder: {e}")
        return HTMLResponse(_reminder_action_page(
            "❌ Error",
            "Ocurrió un error al desactivar los recordatorios. Inténtalo nuevamente.",
            "#dc2626"
        ), status_code=500)
    finally:
        db.close()


# ════════════════════════════════════════
# HELPER — Página HTML de confirmación
# ════════════════════════════════════════

def _reminder_action_page(title: str, message: str, color: str = "#7c5aff") -> str:
    """Página HTML simple que se muestra al hacer clic en los botones del correo."""
    from ..config import settings
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — PlanificaMe</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f8;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; padding: 20px; }}
    .card {{ background: white; border-radius: 20px; padding: 48px 40px;
             max-width: 460px; width: 100%; text-align: center;
             box-shadow: 0 8px 32px rgba(0,0,0,0.10); }}
    .icon {{ font-size: 52px; margin-bottom: 16px; }}
    h1 {{ font-size: 22px; color: {color}; margin-bottom: 12px; font-weight: 700; }}
    p {{ font-size: 15px; color: #44446a; line-height: 1.6; margin-bottom: 28px; }}
    a.btn {{ display: inline-block; padding: 12px 28px; background: {color};
             color: white; text-decoration: none; border-radius: 10px;
             font-weight: 700; font-size: 14px; }}
    .footer {{ margin-top: 24px; font-size: 12px; color: #8888aa; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{title.split()[0]}</div>
    <h1>{' '.join(title.split()[1:])}</h1>
    <p>{message}</p>
    <a href="{settings.FRONTEND_URL}" class="btn">Ir a PlanificaMe →</a>
    <p class="footer">PlanificaMe © 2026</p>
  </div>
</body>
</html>"""
