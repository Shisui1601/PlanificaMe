from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, CalendarMember, User, Calendar
from ..schemas.schemas import (
    EventCreate, EventUpdate, EventStatusUpdate, EventResponse,
    ListEventsResponse, HolidayResponse
)
from ..services.event_service import EventService
from ..utils.helpers import get_holiday
from ..permissions import require_calendar_permission, get_user_calendar_role
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


def _get_member_emails(db, calendar_id: str, exclude_id: str = None) -> list:
    """Retorna lista de (email, name) de miembros del calendario."""
    rows = db.query(CalendarMember).filter(CalendarMember.calendar_id == calendar_id).all()
    result = []
    for m in rows:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u and u.email and u.id != exclude_id:
            result.append((u.email, u.name or "Miembro"))
    return result


def _notify_members(db, calendar_id, exclude_id, fn):
    """Llama fn(email, name) para cada miembro del calendario."""
    if not calendar_id:
        return
    try:
        for email, name in _get_member_emails(db, calendar_id, exclude_id):
            try:
                fn(email, name)
            except Exception as ex:
                logger.error(f"Notify error {email}: {ex}")
    except Exception as ex:
        logger.error(f"Member lookup error {calendar_id}: {ex}")


# POST - CREATE
@router.post("/", response_model=EventResponse)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo evento.
    Si tiene calendar_id, verifica que el usuario sea al menos editor.
    """
    if event.calendar_id:
        require_calendar_permission(
            db, event.calendar_id, event.creator_id,
            required_role="editor",
            action="crear eventos en este calendario"
        )
    created = EventService.create_event(db, event)

    # Notificar a miembros (nunca para actividades personales)
    if event.calendar_id and event.type != "personal":
        try:
            from ..services.mail_service import MailService
            cal  = db.query(Calendar).filter(Calendar.id == event.calendar_id).first()
            usr  = db.query(User).filter(User.id == event.creator_id).first()
            c_name = usr.name  if usr  else "Alguien"
            g_name = cal.name  if cal  else "Calendario"
            g_col  = cal.color if cal  else "#7c5aff"
            def _notify_create(email, _):
                MailService.send_event_created_email(
                    to_email=email, event_title=event.title, event_type=event.type,
                    event_date=event.date, event_time=event.time, creator_name=c_name,
                    calendar_name=g_name, calendar_color=g_col,
                    description=event.description or None,
                    deadline_date=event.deadline_date or None,
                    duration_minutes=event.duration or None)
            _notify_members(db, event.calendar_id, event.creator_id, _notify_create)
        except Exception as ex:
            logger.error(f"Create notify error: {ex}")
    return created


# GET - SPECIFIC ROUTES (must come before generic /{id} routes)
@router.get("/status/overdue", response_model=ListEventsResponse)
def get_overdue_events(db: Session = Depends(get_db)):
    """Obtiene eventos vencidos"""
    from datetime import datetime
    today = datetime.today().strftime("%Y-%m-%d")
    events = EventService.get_overdue_events(db, today)
    return ListEventsResponse(events=events, total=len(events))


@router.get("/status/upcoming/{days}", response_model=ListEventsResponse)
def get_upcoming_events(days: int = 7, db: Session = Depends(get_db)):
    """Obtiene eventos próximos a vencer"""
    events = EventService.get_upcoming_events(db, days)
    return ListEventsResponse(events=events, total=len(events))


@router.get("/by-date/{date}", response_model=ListEventsResponse)
def get_events_by_date(date: str, db: Session = Depends(get_db)):
    """Obtiene eventos de una fecha específica"""
    events = EventService.get_events_by_date(db, date)
    return ListEventsResponse(events=events, total=len(events))


@router.get("/by-range/{start_date}/{end_date}", response_model=ListEventsResponse)
def get_events_by_range(start_date: str, end_date: str, db: Session = Depends(get_db)):
    """Obtiene eventos en un rango de fechas"""
    events = EventService.get_events_by_date_range(db, start_date, end_date)
    return ListEventsResponse(events=events, total=len(events))


@router.get("/search/{query}", response_model=ListEventsResponse)
def search_events(query: str, db: Session = Depends(get_db)):
    """Busca eventos por título o descripción"""
    events = EventService.search_events(db, query)
    return ListEventsResponse(events=events, total=len(events))


# GET - GENERIC (with optional filters)
@router.get("/", response_model=ListEventsResponse)
def get_all_events(
    db: Session = Depends(get_db),
    creator_id: Optional[str] = None,
    event_type: Optional[str] = None,
    project_id: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    calendar_id: Optional[str] = None
):
    """Obtiene eventos con filtros opcionales"""
    events = EventService.get_events_with_filters(
        db, creator_id=creator_id, event_type=event_type,
        project_id=project_id, date=date, status=status,
        calendar_id=calendar_id
    )
    return ListEventsResponse(events=events, total=len(events))


# GET - BY ID (must come after all specific routes)
@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Obtiene un evento por ID"""
    event = EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


# PATCH - UPDATE
@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str,
    event_update: EventUpdate,
    user_id: str = Query(None, description="ID del usuario que edita"),
    db: Session = Depends(get_db)
):
    """
    Actualiza un evento.
    Solo el creador del evento o un editor/owner del calendario puede editarlo.
    """
    event = EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    # Verificar permisos
    if user_id:
        is_creator = event.creator_id == user_id
        if not is_creator and event.calendar_id:
            require_calendar_permission(
                db, event.calendar_id, user_id,
                required_role="editor",
                action="editar eventos de este calendario"
            )
        elif not is_creator:
            raise HTTPException(status_code=403, detail="Solo el creador puede editar este evento")

    old_title = event.title
    old_date  = event.date
    old_time  = event.time
    old_desc  = event.description or ""
    updated = EventService.update_event(db, event_id, event_update)

    if event.calendar_id and event.type != "personal":
        try:
            from ..services.mail_service import MailService
            cal = db.query(Calendar).filter(Calendar.id == event.calendar_id).first()
            usr = db.query(User).filter(User.id == user_id).first() if user_id else None
            ed_name = usr.name if usr else "Un miembro"
            g_name  = cal.name  if cal else "Calendario"
            g_col   = cal.color if cal else "#7c5aff"
            changes = []
            if event_update.title and event_update.title != old_title:
                changes.append({"field": "Título", "old": old_title, "new": event_update.title})
            if event_update.date and event_update.date != old_date:
                changes.append({"field": "Fecha", "old": old_date, "new": event_update.date})
            if event_update.time and event_update.time != old_time:
                changes.append({"field": "Hora", "old": old_time, "new": event_update.time})
            if event_update.description is not None and event_update.description != old_desc:
                changes.append({"field": "Descripción", "old": (old_desc[:60] or "—"), "new": (event_update.description or "")[:60]})
            def _notify_update(email, _):
                MailService.send_event_updated_email(
                    to_email=email, event_title=updated.title,
                    editor_name=ed_name, calendar_name=g_name,
                    calendar_color=g_col, changes=changes or None)
            _notify_members(db, event.calendar_id, user_id, _notify_update)
        except Exception as ex:
            logger.error(f"Update notify error: {ex}")
    return updated


@router.patch("/{event_id}/status", response_model=EventResponse)
def update_event_status(event_id: str, status_update: EventStatusUpdate, db: Session = Depends(get_db)):
    """Actualiza el estado de un evento y envía notificación por correo"""
    event = EventService.update_event_status(db, event_id, status_update)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    notifiable = ["completed", "early-voluntary", "early-forced", "extended", "abandoned"]
    if status_update.status in notifiable:
        try:
            from ..services.mail_service import MailService
            changer_id = getattr(status_update, "user_id", None)
            usr = db.query(User).filter(User.id == changer_id).first() if changer_id else None
            ch_name = usr.name if usr else "Un miembro"

            if event.calendar_id and event.type != "personal":
                cal = db.query(Calendar).filter(Calendar.id == event.calendar_id).first()
                g_name = cal.name  if cal else "Calendario"
                g_col  = cal.color if cal else "#7c5aff"
                def _notify_status(email, _):
                    MailService.send_status_team_email(
                        to_email=email, event_title=event.title,
                        new_status=status_update.status, changed_by=ch_name,
                        calendar_name=g_name, calendar_color=g_col,
                        status_note=status_update.status_note)
                _notify_members(db, event.calendar_id, changer_id, _notify_status)
            elif event.email:
                MailService.send_status_update_email(
                    event_title=event.title, to_email=event.email,
                    status=status_update.status, status_note=status_update.status_note)
        except Exception as ex:
            logger.error(f"Status notify error: {ex}")
    return event


# DELETE
@router.delete("/{event_id}")
def delete_event(
    event_id: str,
    user_id: str = Query(None, description="ID del usuario que elimina"),
    db: Session = Depends(get_db)
):
    """
    Elimina un evento.
    Solo el creador o un owner/editor del calendario puede eliminarlo.
    """
    event = EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if user_id:
        is_creator = event.creator_id == user_id
        if not is_creator and event.calendar_id:
            require_calendar_permission(
                db, event.calendar_id, user_id,
                required_role="editor",
                action="eliminar eventos de este calendario"
            )
        elif not is_creator:
            raise HTTPException(status_code=403, detail="Solo el creador puede eliminar este evento")

    if not EventService.delete_event(db, event_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"message": "Evento eliminado"}

# ════════════════════════════════════════
# RECURRENCIA
# ════════════════════════════════════════

from pydantic import BaseModel as PydanticBase

class RecurringUpdateRequest(PydanticBase):
    scope: str  # "this" | "this_and_future" | "all"
    title: Optional[str] = None
    description: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[int] = None
    reminder: Optional[int] = None
    color: Optional[str] = None


@router.get("/recurring/{group_id}", response_model=ListEventsResponse)
def get_recurring_group(group_id: str, db: Session = Depends(get_db)):
    """Obtiene todas las instancias de un grupo recurrente"""
    from ..database import Event as EventModel
    events = db.query(EventModel).filter(
        EventModel.recurrence_group_id == group_id
    ).order_by(EventModel.date).all()
    return ListEventsResponse(events=events, total=len(events))


@router.delete("/recurring/{group_id}")
def delete_recurring_group(
    group_id: str,
    scope: str = Query("all", description="'all' o 'this_and_future'"),
    from_date: Optional[str] = Query(None, description="Fecha desde la que eliminar (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Elimina instancias de un grupo recurrente.
    scope='all' → elimina todas
    scope='this_and_future' → elimina desde from_date
    """
    if scope == "this_and_future" and not from_date:
        raise HTTPException(status_code=400, detail="from_date requerido para scope 'this_and_future'")

    date_filter = from_date if scope == "this_and_future" else None
    count = EventService.delete_recurring_group(db, group_id, date_filter)
    return {"deleted": count, "group_id": group_id}


@router.patch("/recurring/{group_id}")
def update_recurring_group(
    group_id: str,
    update: RecurringUpdateRequest,
    from_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Actualiza instancias de un grupo recurrente.
    update.scope='all' → actualiza todas
    update.scope='this_and_future' → actualiza desde from_date
    """
    date_filter = from_date if update.scope == "this_and_future" else None
    event_update = EventUpdate(
        title=update.title,
        description=update.description,
        time=update.time,
        duration=update.duration,
        reminder=update.reminder,
        color=update.color
    )
    count = EventService.update_recurring_group(db, group_id, event_update, date_filter)
    return {"updated": count, "group_id": group_id}

# ════════════════════════════════════════
# POLLING — cambios recientes para notificaciones
# ════════════════════════════════════════

@router.get("/poll/changes")
def poll_changes(
    calendar_ids: str = Query(..., description="IDs de calendarios separados por coma"),
    since: str = Query(..., description="ISO datetime — eventos modificados después de esto"),
    user_id: str = Query(..., description="ID del usuario que hace polling (excluir sus propios cambios)"),
    db: Session = Depends(get_db)
):
    """
    Devuelve eventos creados o modificados después de 'since' en los calendarios dados.
    Excluye cambios del propio usuario para no notificarse a sí mismo.
    Usado por el frontend cada 15 segundos para detectar cambios de otros.
    """
    from ..database import Event as EventModel
    from datetime import datetime

    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except Exception:
        since_dt = datetime.utcnow()

    cal_list = [c.strip() for c in calendar_ids.split(',') if c.strip()]
    if not cal_list:
        return {"changes": [], "count": 0}

    changes = db.query(EventModel).filter(
        EventModel.calendar_id.in_(cal_list),
        EventModel.updated_at > since_dt,
        EventModel.creator_id != user_id          # excluir propios cambios
    ).order_by(EventModel.updated_at.desc()).limit(20).all()

    result = []
    for ev in changes:
        creator = ev.creator
        result.append({
            "id": ev.id,
            "title": ev.title,
            "date": ev.date,
            "time": ev.time,
            "type": ev.type,
            "creator_name": creator.name if creator else "Alguien",
            "calendar_id": ev.calendar_id,
            "updated_at": ev.updated_at.isoformat(),
            "is_new": (ev.updated_at - ev.created_at).total_seconds() < 10
        })

    return {"changes": result, "count": len(result)}

# ── MENTION NOTIFY ────────────────────────────────────────
from pydantic import BaseModel as _BaseModel

class _MentionNotifyBody(_BaseModel):
    to_email: str
    event_title: str
    sender_name: str = "Alguien"

@router.post("/{event_id}/mention-notify")
async def mention_notify(
    event_id: str,
    body: _MentionNotifyBody,
    db: Session = Depends(get_db)
):
    """Envía correo de notificación cuando alguien te menciona en una actividad"""
    from ..services.mail_service import MailService

    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto;background:#0f0f1a;color:#e2e8f0;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#7c5aff,#5b3acc);padding:28px 32px;">
        <h2 style="margin:0;color:white;font-size:22px;">💬 Te mencionaron en PlanificaMe</h2>
      </div>
      <div style="padding:28px 32px;">
        <p style="margin:0 0 16px;font-size:15px;color:#cbd5e1;">
          <strong style="color:#a78bfa">{body.sender_name}</strong> te mencionó en la actividad:
        </p>
        <div style="background:#1e1b4b;border-left:4px solid #7c5aff;border-radius:8px;padding:14px 18px;margin:0 0 20px;">
          <span style="font-size:16px;font-weight:700;color:#e2e8f0;">📋 {body.event_title}</span>
        </div>
        <p style="margin:0;font-size:13px;color:#64748b;">
          Ingresa a PlanificaMe para ver la actividad completa.
        </p>
      </div>
    </div>
    """

    success = MailService.send_email(
        to_email=body.to_email,
        subject=f"💬 {body.sender_name} te mencionó en «{body.event_title}»",
        html_content=html
    )

    return {"sent": success, "to": body.to_email}