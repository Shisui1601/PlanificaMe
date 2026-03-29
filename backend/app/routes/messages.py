"""
routes/messages.py — Chat de calendarios
GET  /api/calendars/{id}/messages        → obtener mensajes (con paginación)
POST /api/calendars/{id}/messages        → enviar mensaje
GET  /api/calendars/{id}/messages/poll   → polling de mensajes nuevos
DELETE /api/calendars/{id}/messages/{msg_id} → eliminar mensaje
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db, Calendar, CalendarMember, CalendarMessage
from ..schemas.schemas import MessageCreate, MessageResponse
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/calendars", tags=["messages"])


def _check_member(db: Session, calendar_id: str, user_id: str):
    """Verifica que el usuario es miembro del calendario"""
    member = db.query(CalendarMember).filter(
        CalendarMember.calendar_id == calendar_id,
        CalendarMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="No eres miembro de este calendario")
    return member


def _fmt_msg(msg: CalendarMessage) -> dict:
    sender_name = msg.sender.name if msg.sender else "Desconocido"
    sender_initial = sender_name[0].upper() if sender_name else "?"
    return {
        "id": msg.id,
        "calendar_id": msg.calendar_id,
        "sender_id": msg.sender_id,
        "sender_name": sender_name,
        "sender_initial": sender_initial,
        "content": "[Mensaje eliminado]" if msg.is_deleted else msg.content,
        "msg_type": msg.msg_type,
        "created_at": msg.created_at.isoformat(),
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        "is_deleted": msg.is_deleted,
    }


# ── GET messages ─────────────────────────────
@router.get("/{calendar_id}/messages")
def get_messages(
    calendar_id: str,
    user_id: str = Query(...),
    limit: int = Query(50, le=200),
    before: Optional[str] = Query(None, description="ISO datetime — get messages before this"),
    db: Session = Depends(get_db)
):
    _check_member(db, calendar_id, user_id)

    q = db.query(CalendarMessage).filter(
        CalendarMessage.calendar_id == calendar_id
    )
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
            q = q.filter(CalendarMessage.created_at < before_dt)
        except Exception:
            pass

    messages = q.order_by(desc(CalendarMessage.created_at)).limit(limit).all()
    messages.reverse()  # chronological order

    return {
        "calendar_id": calendar_id,
        "messages": [_fmt_msg(m) for m in messages],
        "count": len(messages)
    }


# ── POLL new messages ─────────────────────────
@router.get("/{calendar_id}/messages/poll")
def poll_messages(
    calendar_id: str,
    user_id: str = Query(...),
    since: str = Query(..., description="ISO datetime — get messages after this"),
    db: Session = Depends(get_db)
):
    """Polling endpoint — devuelve mensajes nuevos desde 'since'"""
    _check_member(db, calendar_id, user_id)

    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except Exception:
        since_dt = datetime.utcnow()

    messages = db.query(CalendarMessage).filter(
        CalendarMessage.calendar_id == calendar_id,
        CalendarMessage.created_at > since_dt
    ).order_by(CalendarMessage.created_at).all()

    return {
        "calendar_id": calendar_id,
        "messages": [_fmt_msg(m) for m in messages],
        "count": len(messages)
    }


# ── POST send message ─────────────────────────
@router.post("/{calendar_id}/messages", status_code=201)
def send_message(
    calendar_id: str,
    msg: MessageCreate,
    db: Session = Depends(get_db)
):
    _check_member(db, calendar_id, msg.sender_id)

    if not msg.content.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    db_msg = CalendarMessage(
        id=str(uuid.uuid4()),
        calendar_id=calendar_id,
        sender_id=msg.sender_id,
        content=msg.content.strip(),
        msg_type=msg.msg_type
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)

    return _fmt_msg(db_msg)


# ── DELETE message ────────────────────────────
@router.delete("/{calendar_id}/messages/{msg_id}")
def delete_message(
    calendar_id: str,
    msg_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    msg = db.query(CalendarMessage).filter(
        CalendarMessage.id == msg_id,
        CalendarMessage.calendar_id == calendar_id
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    # Solo el sender puede eliminar su mensaje
    if msg.sender_id != user_id:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios mensajes")

    msg.is_deleted = True
    db.commit()
    return {"message": "✓ Mensaje eliminado"}