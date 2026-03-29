"""
routes/calendars.py — Endpoints de calendarios con sistema de permisos
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import (
    CalendarCreate, CalendarResponse, ListCalendarsResponse,
    InviteCalendarMember
)
from ..services.calendar_service import CalendarService
from ..services.mail_service import MailService
from ..permissions import require_calendar_permission, get_user_calendar_role
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendars", tags=["calendars"])


@router.post("/", response_model=CalendarResponse)
def create_calendar(calendar: CalendarCreate, db: Session = Depends(get_db)):
    """Crea un nuevo calendario. El creador es automáticamente owner."""
    return CalendarService.create_calendar(db, calendar)


@router.get("/user/{user_id}", response_model=ListCalendarsResponse)
def get_user_calendars(user_id: str, db: Session = Depends(get_db)):
    """Obtiene todos los calendarios donde el usuario es miembro"""
    calendars = CalendarService.get_user_calendars(db, user_id)
    return ListCalendarsResponse(calendars=calendars, total=len(calendars))


@router.post("/{calendar_id}/members/invite", response_model=dict)
def invite_calendar_member(
    calendar_id: str,
    invite: InviteCalendarMember,
    user_id: str = Query(..., description="ID del usuario que invita"),
    db: Session = Depends(get_db)
):
    """Invita a un usuario. Solo el owner puede invitar."""
    require_calendar_permission(db, calendar_id, user_id, "owner", "invitar miembros")

    member = CalendarService.invite_member_by_email(db, calendar_id, invite.email, invite.role)
    if not member:
        raise HTTPException(status_code=404, detail="Usuario no encontrado por email")

    try:
        calendar = CalendarService.get_calendar(db, calendar_id)
        invited_user = member.user
        inviter_name = calendar.owner.name if calendar and calendar.owner else "Un colaborador"
        invited_name = invited_user.name if invited_user else invite.email
        if calendar:
            MailService.send_calendar_invite_email(
                to_email=invite.email, to_name=invited_name,
                inviter_name=inviter_name, calendar_name=calendar.name,
                calendar_color=calendar.color or "#7c5aff", role=invite.role
            )
    except Exception as e:
        logger.error(f"Error enviando correo de invitación: {str(e)}")

    return {"status": "invited", "calendar_id": calendar_id,
            "user_email": invite.email, "role": invite.role}


@router.delete("/{calendar_id}/members/{member_user_id}")
def remove_calendar_member(
    calendar_id: str,
    member_user_id: str,
    user_id: str = Query(..., description="ID del usuario que hace la acción"),
    db: Session = Depends(get_db)
):
    """Remueve un miembro. Owner puede remover a cualquiera. Un miembro puede salirse."""
    if user_id != member_user_id:
        require_calendar_permission(db, calendar_id, user_id, "owner", "remover miembros")

    success = CalendarService.remove_calendar_member(db, calendar_id, member_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    return {"status": "removed"}


@router.get("/{calendar_id}/members", response_model=list)
def get_calendar_members(
    calendar_id: str,
    user_id: str = Query(..., description="ID del usuario que consulta"),
    db: Session = Depends(get_db)
):
    """Ver miembros. Requiere ser miembro del calendario."""
    require_calendar_permission(db, calendar_id, user_id, "viewer", "ver los miembros")
    return CalendarService.get_calendar_members(db, calendar_id)


@router.patch("/{calendar_id}", response_model=CalendarResponse)
def update_calendar(
    calendar_id: str,
    user_id: str = Query(..., description="ID del usuario que actualiza"),
    name: str = None,
    description: str = None,
    color: str = None,
    db: Session = Depends(get_db)
):
    """Actualiza el calendario. Solo el owner puede modificarlo."""
    require_calendar_permission(db, calendar_id, user_id, "owner", "modificar el calendario")
    calendar = CalendarService.update_calendar(db, calendar_id, name, description, color)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendario no encontrado")
    return calendar


@router.delete("/{calendar_id}")
def delete_calendar(
    calendar_id: str,
    user_id: str = Query(..., description="ID del usuario que elimina"),
    db: Session = Depends(get_db)
):
    """Elimina el calendario. Solo el owner puede eliminarlo."""
    require_calendar_permission(db, calendar_id, user_id, "owner", "eliminar el calendario")
    success = CalendarService.delete_calendar(db, calendar_id)
    if not success:
        raise HTTPException(status_code=404, detail="Calendario no encontrado")
    return {"status": "deleted"}


@router.get("/{calendar_id}/my-role")
def get_my_role(
    calendar_id: str,
    user_id: str = Query(..., description="ID del usuario"),
    db: Session = Depends(get_db)
):
    """Devuelve el rol del usuario en el calendario."""
    role = get_user_calendar_role(db, calendar_id, user_id)
    return {
        "calendar_id": calendar_id, "user_id": user_id, "role": role,
        "can_edit": role in ["owner", "editor"],
        "can_manage_members": role == "owner",
        "can_delete_calendar": role == "owner",
    }


@router.get("/{calendar_id}", response_model=CalendarResponse)
def get_calendar(
    calendar_id: str,
    user_id: str = Query(None),
    db: Session = Depends(get_db)
):
    """Obtiene un calendario por ID."""
    calendar = CalendarService.get_calendar(db, calendar_id)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendario no encontrado")
    if user_id:
        role = get_user_calendar_role(db, calendar_id, user_id)
        if role == "none":
            raise HTTPException(status_code=403, detail="No tienes acceso a este calendario")
    return calendar