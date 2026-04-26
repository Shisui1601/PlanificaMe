"""
routes/direct_chat.py — Chat personal directo entre usuarios

POST /api/chat/contacts/request           -> enviar solicitud de contacto
GET  /api/chat/contacts?user_id=          -> listar contactos aceptados
GET  /api/chat/contacts/pending?user_id=  -> solicitudes recibidas pendientes
POST /api/chat/contacts/{cid}/accept      -> aceptar solicitud
POST /api/chat/contacts/{cid}/decline     -> rechazar solicitud
GET  /api/chat/direct/{other_id}/messages -> historial de mensajes
POST /api/chat/direct/{other_id}/messages -> enviar mensaje directo
GET  /api/chat/direct/poll               -> poll de mensajes nuevos (cualquier contacto)
"""
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from ..database import SessionLocal, User, DirectContact, DirectMessage
from ..services.mail_service import MailService
import uuid
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["direct-chat"])


# ── helpers ──────────────────────────────────────────────────────────

def _db():
    return SessionLocal()


def _fmt_contact(contact: DirectContact, my_id: str) -> dict:
    """Serializa un contacto desde la perspectiva del usuario 'my_id'."""
    is_requester = contact.requester_id == my_id
    other_user   = contact.receiver if is_requester else contact.requester
    return {
        "id":            contact.id,
        "status":        contact.status,
        "first_message": contact.first_message,
        "is_requester":  is_requester,
        "created_at":    contact.created_at.isoformat(),
        "other_user": {
            "id":    other_user.id,
            "name":  other_user.name,
            "email": other_user.email,
        } if other_user else None,
    }


def _fmt_msg(msg: DirectMessage, my_id: str) -> dict:
    sender_name = msg.sender.name if msg.sender else "Desconocido"
    return {
        "id":          msg.id,
        "sender_id":   msg.sender_id,
        "receiver_id": msg.receiver_id,
        "sender_name": sender_name,
        "content":     "[Mensaje eliminado]" if msg.is_deleted else msg.content,
        "is_deleted":  msg.is_deleted,
        "is_mine":     msg.sender_id == my_id,
        "created_at":  msg.created_at.isoformat(),
    }


def _are_contacts(db: Session, user_a: str, user_b: str) -> bool:
    """Verifica que los dos usuarios tienen una relacion aceptada."""
    return db.query(DirectContact).filter(
        DirectContact.status == "accepted",
        or_(
            and_(DirectContact.requester_id == user_a, DirectContact.receiver_id == user_b),
            and_(DirectContact.requester_id == user_b, DirectContact.receiver_id == user_a),
        )
    ).first() is not None


# ── POST /api/chat/contacts/request ─────────────────────────────────

@router.post("/contacts/request", status_code=201)
def send_contact_request(body: dict):
    """
    Envía una solicitud de contacto a un usuario identificado por email o nombre.
    body: { requester_id, identifier, first_message }
    """
    requester_id  = body.get("requester_id", "").strip()
    identifier    = body.get("identifier", "").strip().lower()
    first_message = (body.get("first_message") or "").strip()

    if not requester_id or not identifier:
        raise HTTPException(status_code=400, detail="Faltan campos requeridos")
    if not first_message:
        raise HTTPException(status_code=400, detail="El mensaje de presentacion no puede estar vacio")

    db = _db()
    try:
        requester = db.query(User).filter(User.id == requester_id).first()
        if not requester:
            raise HTTPException(status_code=404, detail="Usuario solicitante no encontrado")

        # Buscar receptor por email o nombre (case-insensitive)
        receiver = db.query(User).filter(
            or_(
                User.email.ilike(identifier),
                User.name.ilike(identifier),
            )
        ).first()

        if not receiver:
            raise HTTPException(status_code=404, detail="No se encontro ningun usuario con ese email o nombre")

        if receiver.id == requester_id:
            raise HTTPException(status_code=400, detail="No puedes enviarte una solicitud a ti mismo")

        # Verificar si ya existe una relacion
        existing = db.query(DirectContact).filter(
            or_(
                and_(DirectContact.requester_id == requester_id, DirectContact.receiver_id == receiver.id),
                and_(DirectContact.requester_id == receiver.id,  DirectContact.receiver_id == requester_id),
            )
        ).first()

        if existing:
            if existing.status == "accepted":
                raise HTTPException(status_code=409, detail="Ya son contactos")
            if existing.status == "pending":
                raise HTTPException(status_code=409, detail="Ya existe una solicitud pendiente")
            if existing.status == "declined":
                # Permitir re-enviar si fue rechazada antes
                existing.status = "pending"
                existing.first_message = first_message
                existing.updated_at = datetime.utcnow()
                db.commit()
                contact_id = existing.id
            else:
                raise HTTPException(status_code=409, detail="No se puede enviar la solicitud")
        else:
            new_contact = DirectContact(
                id=str(uuid.uuid4()),
                requester_id=requester_id,
                receiver_id=receiver.id,
                status="pending",
                first_message=first_message,
            )
            db.add(new_contact)
            db.commit()
            db.refresh(new_contact)
            contact_id = new_contact.id

        # Enviar email al receptor
        try:
            MailService.send_contact_request_email(
                requester_name=requester.name,
                to_email=receiver.email,
                receiver_name=receiver.name,
                first_message=first_message,
            )
        except Exception as e:
            logger.warning("No se pudo enviar email de solicitud: %s" % str(e))

        return {
            "status":       "sent",
            "contact_id":   contact_id,
            "receiver_name": receiver.name,
        }
    finally:
        db.close()


# ── GET /api/chat/contacts ──────────────────────────────────────────

@router.get("/contacts")
def list_contacts(user_id: str = Query(...)):
    """Lista todos los contactos aceptados del usuario."""
    db = _db()
    try:
        contacts = db.query(DirectContact).filter(
            DirectContact.status == "accepted",
            or_(
                DirectContact.requester_id == user_id,
                DirectContact.receiver_id  == user_id,
            )
        ).order_by(desc(DirectContact.updated_at)).all()

        result = []
        for c in contacts:
            fmt = _fmt_contact(c, user_id)
            if not fmt["other_user"]:
                continue
            other_id = fmt["other_user"]["id"]
            # Ultimo mensaje
            last_msg = db.query(DirectMessage).filter(
                or_(
                    and_(DirectMessage.sender_id == user_id,   DirectMessage.receiver_id == other_id),
                    and_(DirectMessage.sender_id == other_id,  DirectMessage.receiver_id == user_id),
                )
            ).order_by(desc(DirectMessage.created_at)).first()
            if last_msg:
                fmt["last_message"] = {
                    "content":    last_msg.content if not last_msg.is_deleted else "[Eliminado]",
                    "created_at": last_msg.created_at.isoformat(),
                    "is_mine":    last_msg.sender_id == user_id,
                }
            result.append(fmt)

        return {"contacts": result}
    finally:
        db.close()


# ── GET /api/chat/contacts/pending ─────────────────────────────────

@router.get("/contacts/pending")
def list_pending(user_id: str = Query(...)):
    """Lista solicitudes de contacto recibidas y pendientes de respuesta."""
    db = _db()
    try:
        pending = db.query(DirectContact).filter(
            DirectContact.receiver_id == user_id,
            DirectContact.status == "pending",
        ).order_by(desc(DirectContact.created_at)).all()

        return {"pending": [_fmt_contact(p, user_id) for p in pending]}
    finally:
        db.close()


# ── POST /api/chat/contacts/{cid}/accept ────────────────────────────

@router.post("/contacts/{contact_id}/accept")
def accept_contact(contact_id: str, body: dict):
    user_id = body.get("user_id", "")
    db = _db()
    try:
        contact = db.query(DirectContact).filter(DirectContact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        if contact.receiver_id != user_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para aceptar esta solicitud")
        if contact.status != "pending":
            raise HTTPException(status_code=400, detail="La solicitud ya fue procesada")

        contact.status     = "accepted"
        contact.updated_at = datetime.utcnow()
        db.commit()

        # Guardar el primer mensaje como mensaje real en la conversacion
        if contact.first_message:
            dm = DirectMessage(
                id=str(uuid.uuid4()),
                sender_id=contact.requester_id,
                receiver_id=contact.receiver_id,
                content=contact.first_message,
            )
            db.add(dm)
            db.commit()

        return {"status": "accepted", "contact_id": contact_id}
    finally:
        db.close()


# ── POST /api/chat/contacts/{cid}/decline ───────────────────────────

@router.post("/contacts/{contact_id}/decline")
def decline_contact(contact_id: str, body: dict):
    user_id = body.get("user_id", "")
    db = _db()
    try:
        contact = db.query(DirectContact).filter(DirectContact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        if contact.receiver_id != user_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para rechazar esta solicitud")

        contact.status     = "declined"
        contact.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "declined"}
    finally:
        db.close()


# ── GET /api/chat/direct/{other_id}/messages ────────────────────────

@router.get("/direct/{other_user_id}/messages")
def get_direct_messages(
    other_user_id: str,
    user_id: str = Query(...),
    limit: int = Query(50, le=200),
    before: Optional[str] = Query(None),
):
    db = _db()
    try:
        if not _are_contacts(db, user_id, other_user_id):
            raise HTTPException(status_code=403, detail="No son contactos")

        q = db.query(DirectMessage).filter(
            or_(
                and_(DirectMessage.sender_id == user_id,      DirectMessage.receiver_id == other_user_id),
                and_(DirectMessage.sender_id == other_user_id, DirectMessage.receiver_id == user_id),
            )
        )
        if before:
            try:
                q = q.filter(DirectMessage.created_at < datetime.fromisoformat(before))
            except Exception:
                pass

        messages = q.order_by(desc(DirectMessage.created_at)).limit(limit).all()
        messages.reverse()

        return {
            "messages": [_fmt_msg(m, user_id) for m in messages],
            "count":    len(messages),
        }
    finally:
        db.close()


# ── POST /api/chat/direct/{other_id}/messages ───────────────────────

@router.post("/direct/{other_user_id}/messages", status_code=201)
def send_direct_message(other_user_id: str, body: dict):
    sender_id = body.get("sender_id", "")
    content   = (body.get("content") or "").strip()

    if not content:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio")

    db = _db()
    try:
        if not _are_contacts(db, sender_id, other_user_id):
            raise HTTPException(status_code=403, detail="No son contactos aceptados")

        dm = DirectMessage(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=other_user_id,
            content=content,
        )
        db.add(dm)
        db.commit()
        db.refresh(dm)

        return _fmt_msg(dm, sender_id)
    finally:
        db.close()


# ── GET /api/chat/direct/poll ────────────────────────────────────────

@router.get("/direct/poll")
def poll_direct_messages(
    user_id: str = Query(...),
    since: str = Query(...),
):
    """Devuelve todos los mensajes directos recibidos desde 'since'."""
    db = _db()
    try:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except Exception:
            since_dt = datetime.utcnow()

        messages = db.query(DirectMessage).filter(
            DirectMessage.receiver_id == user_id,
            DirectMessage.created_at  > since_dt,
        ).order_by(DirectMessage.created_at).all()

        return {
            "messages": [_fmt_msg(m, user_id) for m in messages],
            "count":    len(messages),
        }
    finally:
        db.close()


# ── GET /api/chat/contacts/count ────────────────────────────────────

@router.get("/contacts/count")
def count_pending(user_id: str = Query(...)):
    """Cantidad de solicitudes pendientes recibidas (para el badge del FAB)."""
    db = _db()
    try:
        n = db.query(DirectContact).filter(
            DirectContact.receiver_id == user_id,
            DirectContact.status == "pending",
        ).count()
        return {"pending_count": n}
    finally:
        db.close()
