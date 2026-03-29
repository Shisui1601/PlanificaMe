"""routes/subtasks.py — Subactividades/checklist"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, Subtask, Event
from ..schemas.schemas import SubtaskCreate, SubtaskUpdate
import uuid

router = APIRouter(prefix="/api/events", tags=["subtasks"])


def _fmt(s: Subtask) -> dict:
    return {"id": s.id, "event_id": s.event_id, "title": s.title, "done": s.done, "position": s.position}


@router.get("/{event_id}/subtasks")
def get_subtasks(event_id: str, db: Session = Depends(get_db)):
    subs = db.query(Subtask).filter(Subtask.event_id == event_id).order_by(Subtask.position).all()
    total = len(subs)
    done = sum(1 for s in subs if s.done)
    return {"subtasks": [_fmt(s) for s in subs], "total": total, "done": done,
            "progress": round(done / total * 100) if total else 0}


@router.post("/{event_id}/subtasks", status_code=201)
def create_subtask(event_id: str, sub: SubtaskCreate, db: Session = Depends(get_db)):
    if not db.query(Event).filter(Event.id == event_id).first():
        raise HTTPException(404, "Evento no encontrado")
    db_sub = Subtask(id=str(uuid.uuid4()), event_id=event_id,
                     title=sub.title.strip(), position=sub.position)
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return _fmt(db_sub)


@router.patch("/{event_id}/subtasks/{sub_id}")
def update_subtask(event_id: str, sub_id: str, data: SubtaskUpdate, db: Session = Depends(get_db)):
    sub = db.query(Subtask).filter(Subtask.id == sub_id, Subtask.event_id == event_id).first()
    if not sub:
        raise HTTPException(404, "Subtarea no encontrada")
    if data.title is not None:
        sub.title = data.title.strip()
    if data.done is not None:
        sub.done = data.done
    if data.position is not None:
        sub.position = data.position
    db.commit()
    db.refresh(sub)
    # Return updated progress
    all_subs = db.query(Subtask).filter(Subtask.event_id == event_id).all()
    total = len(all_subs)
    done_count = sum(1 for s in all_subs if s.done)
    return {**_fmt(sub), "progress": round(done_count / total * 100) if total else 0,
            "total": total, "done_count": done_count}


@router.delete("/{event_id}/subtasks/{sub_id}")
def delete_subtask(event_id: str, sub_id: str, db: Session = Depends(get_db)):
    sub = db.query(Subtask).filter(Subtask.id == sub_id, Subtask.event_id == event_id).first()
    if not sub:
        raise HTTPException(404, "Subtarea no encontrada")
    db.delete(sub)
    db.commit()
    return {"message": "✓ Subtarea eliminada"}