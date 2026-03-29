from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..database import Event, Project
from ..schemas.schemas import EventCreate, EventUpdate, EventStatusUpdate
from ..utils.helpers import generate_id, time_to_minutes
from typing import List, Optional, Dict
from datetime import datetime, timedelta, date as date_type


def _generate_recurrence_dates(
    start_date: str,
    recurrence_type: str,
    recurrence_end: str,
    max_occurrences: int = 365
) -> List[str]:
    """
    Genera todas las fechas de recurrencia.
    Tipos: daily, weekly, monthly, weekdays (lunes a viernes)
    Máximo 1 año o max_occurrences instancias.
    """
    dates = []
    try:
        current = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(recurrence_end, "%Y-%m-%d").date()
        end = min(end, current + timedelta(days=365))  # máximo 1 año

        count = 0
        while current <= end and count < max_occurrences:
            dates.append(current.strftime("%Y-%m-%d"))
            count += 1

            if recurrence_type == "daily":
                current += timedelta(days=1)
            elif recurrence_type == "weekly":
                current += timedelta(weeks=1)
            elif recurrence_type == "monthly":
                # Mismo día del mes siguiente
                month = current.month + 1
                year = current.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    current = current.replace(year=year, month=month)
                except ValueError:
                    # Día no existe en ese mes (ej. 31 en febrero) — saltar
                    break
            elif recurrence_type == "weekdays":
                current += timedelta(days=1)
                while current.weekday() >= 5:  # 5=Sábado, 6=Domingo
                    current += timedelta(days=1)
            else:
                break

    except Exception:
        pass

    return dates


class EventService:
    """Servicio para manejar operaciones con eventos/tareas"""

    @staticmethod
    def create_event(db: Session, event: EventCreate) -> Event:
        """
        Crea un evento. Si es recurrente, genera todas las instancias
        y devuelve la primera.
        """
        # Determinar group_id para recurrencia
        group_id = event.recurrence_group_id or (generate_id() if event.is_recurring else None)

        # Crear el primer evento (o el único si no es recurrente)
        db_event = Event(
            id=generate_id(),
            title=event.title,
            description=event.description,
            type=event.type,
            date=event.date,
            time=event.time,
            duration=event.duration,
            reminder=event.reminder,
            email=event.email,
            project_id=event.project_id,
            creator_id=event.creator_id,
            color=event.color,
            is_deadline=event.is_deadline,
            deadline_date=event.deadline_date,
            deadline_time=event.deadline_time,
            calendar_id=event.calendar_id,
            is_recurring=event.is_recurring,
            recurrence_type=event.recurrence_type,
            recurrence_end=event.recurrence_end,
            recurrence_group_id=group_id
        )
        db.add(db_event)

        # Si es recurrente, generar el resto de instancias
        if event.is_recurring and event.recurrence_type and event.recurrence_end:
            dates = _generate_recurrence_dates(
                event.date, event.recurrence_type, event.recurrence_end
            )
            # Saltar la primera fecha (ya creada arriba)
            for d in dates[1:]:
                instance = Event(
                    id=generate_id(),
                    title=event.title,
                    description=event.description,
                    type=event.type,
                    date=d,
                    time=event.time,
                    duration=event.duration,
                    reminder=event.reminder,
                    email=event.email,
                    project_id=event.project_id,
                    creator_id=event.creator_id,
                    color=event.color,
                    is_deadline=False,
                    calendar_id=event.calendar_id,
                    is_recurring=True,
                    recurrence_type=event.recurrence_type,
                    recurrence_end=event.recurrence_end,
                    recurrence_group_id=group_id
                )
                db.add(instance)

        db.commit()
        db.refresh(db_event)
        return db_event

    @staticmethod
    def delete_recurring_group(db: Session, recurrence_group_id: str, from_date: str = None) -> int:
        """
        Elimina todas las instancias de un grupo recurrente.
        Si from_date se especifica, solo elimina desde esa fecha en adelante.
        Devuelve el número de eventos eliminados.
        """
        query = db.query(Event).filter(Event.recurrence_group_id == recurrence_group_id)
        if from_date:
            query = query.filter(Event.date >= from_date)
        count = query.count()
        query.delete()
        db.commit()
        return count

    @staticmethod
    def update_recurring_group(db: Session, recurrence_group_id: str,
                                event_update: EventUpdate, from_date: str = None) -> int:
        """
        Actualiza todas las instancias de un grupo recurrente.
        Si from_date, solo actualiza desde esa fecha.
        """
        query = db.query(Event).filter(Event.recurrence_group_id == recurrence_group_id)
        if from_date:
            query = query.filter(Event.date >= from_date)

        update_data = event_update.model_dump(exclude_unset=True)
        # No actualizar date ni recurrence_group_id en masivo
        update_data.pop("date", None)
        update_data.pop("recurrence_group_id", None)

        events = query.all()
        for ev in events:
            for field, value in update_data.items():
                setattr(ev, field, value)
            ev.updated_at = datetime.utcnow()
        db.commit()
        return len(events)


    @staticmethod
    def get_event(db: Session, event_id: str) -> Optional[Event]:
        """Obtiene un evento por ID"""
        return db.query(Event).filter(Event.id == event_id).first()
    
    @staticmethod
    def get_events_by_date(db: Session, date: str) -> List[Event]:
        """Obtiene eventos de una fecha específica"""
        return db.query(Event).filter(Event.date == date).all()
    
    @staticmethod
    def get_events_by_date_range(db: Session, start_date: str, end_date: str) -> List[Event]:
        """Obtiene eventos entre dos fechas"""
        return db.query(Event).filter(
            and_(Event.date >= start_date, Event.date <= end_date)
        ).all()
    
    @staticmethod
    def get_events_by_creator(db: Session, creator_id: str) -> List[Event]:
        """Obtiene eventos de un creador específico"""
        return db.query(Event).filter(Event.creator_id == creator_id).all()
    
    @staticmethod
    def get_events_by_type(db: Session, event_type: str) -> List[Event]:
        """Obtiene eventos de un tipo específico"""
        return db.query(Event).filter(Event.type == event_type).all()
    
    @staticmethod
    def get_all_events(db: Session) -> List[Event]:
        """Obtiene todos los eventos"""
        return db.query(Event).all()
    
    @staticmethod
    def search_events(db: Session, query: str) -> List[Event]:
        """Búsqueda de eventos por título o descripción"""
        search_term = f"%{query}%"
        return db.query(Event).filter(
            or_(
                Event.title.ilike(search_term),
                Event.description.ilike(search_term)
            )
        ).all()
    
    @staticmethod
    def update_event(db: Session, event_id: str, event_update: EventUpdate) -> Optional[Event]:
        """Actualiza un evento"""
        db_event = db.query(Event).filter(Event.id == event_id).first()
        if db_event:
            update_data = event_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_event, field, value)
            db_event.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_event)
        return db_event
    
    @staticmethod
    def update_event_status(db: Session, event_id: str, status_update: EventStatusUpdate) -> Optional[Event]:
        """Actualiza el estado de un evento"""
        db_event = db.query(Event).filter(Event.id == event_id).first()
        if db_event:
            if status_update.status:
                db_event.status = status_update.status
            if status_update.status_note:
                db_event.status_note = status_update.status_note
            if status_update.actual_date:
                db_event.actual_date = status_update.actual_date
            if status_update.actual_time:
                db_event.actual_time = status_update.actual_time
            if status_update.deadline_date and status_update.status == "extended":
                db_event.deadline_date = status_update.deadline_date
            if status_update.deadline_time and status_update.status == "extended":
                db_event.deadline_time = status_update.deadline_time
            
            db_event.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_event)
        return db_event
    
    @staticmethod
    def delete_event(db: Session, event_id: str) -> bool:
        """Elimina un evento"""
        db_event = db.query(Event).filter(Event.id == event_id).first()
        if db_event:
            db.delete(db_event)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_events_with_filters(
        db: Session,
        creator_id: Optional[str] = None,
        event_type: Optional[str] = None,
        project_id: Optional[str] = None,
        date: Optional[str] = None,
        status: Optional[str] = None,
        calendar_id: Optional[str] = None
    ) -> List[Event]:
        """Obtiene eventos con filtros aplicados"""
        query = db.query(Event)
        
        if creator_id:
            query = query.filter(Event.creator_id == creator_id)
        if event_type:
            query = query.filter(Event.type == event_type)
        if project_id:
            query = query.filter(Event.project_id == project_id)
        if date:
            query = query.filter(Event.date == date)
        if status:
            query = query.filter(Event.status == status)
        if calendar_id:
            query = query.filter(Event.calendar_id == calendar_id)
        
        return query.all()
    
    @staticmethod
    def get_deadline_events(db: Session) -> List[Event]:
        """Obtiene eventos que son fechas límite"""
        return db.query(Event).filter(Event.is_deadline == True).all()
    
    @staticmethod
    def get_overdue_events(db: Session, today: str) -> List[Event]:
        """Obtiene eventos vencidos que no están completados o abandonados"""
        return db.query(Event).filter(
            and_(
                Event.deadline_date < today,
                Event.status.notin_(["completed", "abandoned"])
            )
        ).all()
    
    @staticmethod
    def get_upcoming_events(db: Session, days: int = 7) -> List[Event]:
        """Obtiene eventos próximos a vencer (en los próximos N días)"""
        from datetime import datetime, timedelta
        today = datetime.today().strftime("%Y-%m-%d")
        future = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        return db.query(Event).filter(
            and_(
                Event.deadline_date >= today,
                Event.deadline_date <= future,
                Event.status.notin_(["completed", "abandoned"])
            )
        ).all()