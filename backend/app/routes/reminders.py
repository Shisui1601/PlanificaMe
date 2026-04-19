"""
reminders.py — Endpoints para enviar recordatorios personalizados
"""
from fastapi import APIRouter, Depends, HTTPException, status
from ..database import SessionLocal, User
from ..schemas.schemas import SendCustomReminderRequest, SendCustomReminderResponse
from ..services.mail_service import MailService
from ..auth import get_current_user
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
