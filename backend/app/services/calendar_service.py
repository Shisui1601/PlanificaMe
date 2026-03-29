from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from ..database import Calendar, CalendarMember, User
from ..schemas.schemas import CalendarCreate, CalendarMemberCreate


class CalendarService:
    
    @staticmethod
    def create_calendar(db: Session, calendar: CalendarCreate) -> Calendar:
        """Crea un nuevo calendario"""
        db_calendar = Calendar(
            id=f'cal_{datetime.utcnow().timestamp()}_{hash(calendar.name) % 10000}',
            name=calendar.name,
            description=calendar.description,
            color=calendar.color,
            owner_id=calendar.owner_id
        )
        db.add(db_calendar)
        
        # El owner es automáticamente miembro con rol 'owner'
        owner_member = CalendarMember(
            id=f'cm_{db_calendar.id}_{calendar.owner_id}',
            calendar_id=db_calendar.id,
            user_id=calendar.owner_id,
            role='owner'
        )
        db.add(owner_member)
        db.commit()
        db.refresh(db_calendar)
        return db_calendar
    
    @staticmethod
    def get_calendar(db: Session, calendar_id: str) -> Calendar:
        """Obtiene un calendario por ID"""
        return db.query(Calendar).filter(Calendar.id == calendar_id).first()
    
    @staticmethod
    def get_user_calendars(db: Session, user_id: str) -> list:
        """Obtiene todos los calendarios del usuario (propios + invitados)"""
        # Calendarios donde el usuario es miembro (incluyendo owner)
        calendars = db.query(Calendar).join(
            CalendarMember,
            Calendar.id == CalendarMember.calendar_id
        ).filter(CalendarMember.user_id == user_id).all()
        
        return calendars
    
    @staticmethod
    def update_calendar(db: Session, calendar_id: str, name: str = None, 
                       description: str = None, color: str = None) -> Calendar:
        """Actualiza un calendario"""
        db_calendar = CalendarService.get_calendar(db, calendar_id)
        if not db_calendar:
            return None
        
        if name:
            db_calendar.name = name
        if description is not None:
            db_calendar.description = description
        if color:
            db_calendar.color = color
        
        db_calendar.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_calendar)
        return db_calendar
    
    @staticmethod
    def delete_calendar(db: Session, calendar_id: str) -> bool:
        """Elimina un calendario"""
        db_calendar = CalendarService.get_calendar(db, calendar_id)
        if not db_calendar:
            return False
        
        db.delete(db_calendar)
        db.commit()
        return True
    
    @staticmethod
    def add_calendar_member(db: Session, calendar_id: str, user_id: str, 
                           role: str = "member") -> CalendarMember:
        """Agrega un miembro al calendario"""
        # Verificar si ya es miembro
        existing = db.query(CalendarMember).filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == user_id
        ).first()
        
        if existing:
            # Actualizar rol si ya existe
            existing.role = role
            db.commit()
            db.refresh(existing)
            return existing
        
        member = CalendarMember(
            id=f'cm_{calendar_id}_{user_id}',
            calendar_id=calendar_id,
            user_id=user_id,
            role=role
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member
    
    @staticmethod
    def remove_calendar_member(db: Session, calendar_id: str, user_id: str) -> bool:
        """Remueve un miembro del calendario"""
        member = db.query(CalendarMember).filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == user_id
        ).first()
        
        if not member:
            return False
        
        db.delete(member)
        db.commit()
        return True
    
    @staticmethod
    def get_calendar_members(db: Session, calendar_id: str) -> list:
        """Obtiene todos los miembros de un calendario"""
        return db.query(CalendarMember).filter(
            CalendarMember.calendar_id == calendar_id
        ).all()
    
    @staticmethod
    def invite_member_by_email(db: Session, calendar_id: str, email: str, 
                               role: str = "member") -> CalendarMember:
        """Invita a un usuario por email al calendario"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        return CalendarService.add_calendar_member(db, calendar_id, user.id, role)
