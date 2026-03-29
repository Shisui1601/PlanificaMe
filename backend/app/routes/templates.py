"""routes/templates.py — Plantillas de actividades"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, ActivityTemplate
from ..schemas.schemas import TemplateCreate
import uuid

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _fmt(t: ActivityTemplate) -> dict:
    return {
        "id": t.id, "name": t.name, "title": t.title,
        "type": t.type, "duration": t.duration, "reminder": t.reminder,
        "description": t.description, "email": t.email, "color": t.color,
        "owner_id": t.owner_id,
        "created_at": t.created_at.isoformat() if t.created_at else None
    }


@router.get("")
def get_templates(owner_id: str = Query(...), db: Session = Depends(get_db)):
    tpls = db.query(ActivityTemplate).filter(
        ActivityTemplate.owner_id == owner_id
    ).order_by(ActivityTemplate.created_at.desc()).all()
    return [_fmt(t) for t in tpls]


@router.post("", status_code=201)
def create_template(tpl: TemplateCreate, db: Session = Depends(get_db)):
    if not tpl.name.strip() or not tpl.title.strip():
        raise HTTPException(400, "Nombre y título requeridos")
    db_tpl = ActivityTemplate(
        id=str(uuid.uuid4()), name=tpl.name.strip(), title=tpl.title.strip(),
        type=tpl.type, duration=tpl.duration, reminder=tpl.reminder,
        description=tpl.description, email=tpl.email, color=tpl.color,
        owner_id=tpl.owner_id
    )
    db.add(db_tpl)
    db.commit()
    db.refresh(db_tpl)
    return _fmt(db_tpl)


@router.delete("/{tpl_id}")
def delete_template(tpl_id: str, owner_id: str = Query(...), db: Session = Depends(get_db)):
    tpl = db.query(ActivityTemplate).filter(
        ActivityTemplate.id == tpl_id, ActivityTemplate.owner_id == owner_id
    ).first()
    if not tpl:
        raise HTTPException(404, "Plantilla no encontrada")
    db.delete(tpl)
    db.commit()
    return {"message": "✓ Plantilla eliminada"}


@router.put("/{tpl_id}")
def update_template(tpl_id: str, data: TemplateCreate, db: Session = Depends(get_db)):
    tpl = db.query(ActivityTemplate).filter(ActivityTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(404, "Plantilla no encontrada")
    for k, v in data.model_dump(exclude={"owner_id"}).items():
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return _fmt(tpl)