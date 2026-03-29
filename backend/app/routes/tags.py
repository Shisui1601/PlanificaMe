"""routes/tags.py — Etiquetas personalizadas"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, EventTag, EventTagAssoc
from ..schemas.schemas import TagCreate, TagResponse
import uuid

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
def get_tags(owner_id: str = Query(...), db: Session = Depends(get_db)):
    tags = db.query(EventTag).filter(EventTag.owner_id == owner_id).order_by(EventTag.created_at).all()
    return [{"id": t.id, "name": t.name, "color": t.color, "owner_id": t.owner_id} for t in tags]


@router.post("", status_code=201)
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    if not tag.name.strip():
        raise HTTPException(400, "El nombre no puede estar vacío")
    db_tag = EventTag(id=str(uuid.uuid4()), name=tag.name.strip(), color=tag.color, owner_id=tag.owner_id)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return {"id": db_tag.id, "name": db_tag.name, "color": db_tag.color, "owner_id": db_tag.owner_id}


@router.delete("/{tag_id}")
def delete_tag(tag_id: str, owner_id: str = Query(...), db: Session = Depends(get_db)):
    tag = db.query(EventTag).filter(EventTag.id == tag_id, EventTag.owner_id == owner_id).first()
    if not tag:
        raise HTTPException(404, "Etiqueta no encontrada")
    db.delete(tag)
    db.commit()
    return {"message": "✓ Etiqueta eliminada"}


@router.get("/event/{event_id}")
def get_event_tags(event_id: str, db: Session = Depends(get_db)):
    assocs = db.query(EventTagAssoc).filter(EventTagAssoc.event_id == event_id).all()
    return [{"id": a.tag.id, "name": a.tag.name, "color": a.tag.color} for a in assocs if a.tag]


@router.post("/event/{event_id}/{tag_id}", status_code=201)
def add_tag_to_event(event_id: str, tag_id: str, db: Session = Depends(get_db)):
    exists = db.query(EventTagAssoc).filter(
        EventTagAssoc.event_id == event_id, EventTagAssoc.tag_id == tag_id
    ).first()
    if exists:
        return {"message": "Ya asignada"}
    assoc = EventTagAssoc(id=str(uuid.uuid4()), event_id=event_id, tag_id=tag_id)
    db.add(assoc)
    db.commit()
    return {"message": "✓ Etiqueta asignada"}


@router.delete("/event/{event_id}/{tag_id}")
def remove_tag_from_event(event_id: str, tag_id: str, db: Session = Depends(get_db)):
    assoc = db.query(EventTagAssoc).filter(
        EventTagAssoc.event_id == event_id, EventTagAssoc.tag_id == tag_id
    ).first()
    if assoc:
        db.delete(assoc)
        db.commit()
    return {"message": "✓ Etiqueta removida"}