import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from backend.app.config import settings

# Configuration
"""DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("SUPABASE_URL", "sqlite:///./planificame.db")
)"""

DATABASE_URL = settings.DATABASE_URL


# Convertir supabase postgresql:// a postgresql+psycopg2://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Modelo de usuario del sistema"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)  # nullable para usuarios existentes
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    events = relationship("Event", back_populates="creator", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="creator", cascade="all, delete-orphan")
    calendars = relationship("Calendar", back_populates="owner", cascade="all, delete-orphan")
    calendar_memberships = relationship("CalendarMember", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """Modelo de proyecto meta"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    color = Column(String, default="#f7a26a")
    creator_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    calendar_id = Column(String, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(String)  # Formato YYYY-MM-DD
    deadline = Column(String, nullable=True)  # Formato YYYY-MM-DD
    created_datetime = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    creator = relationship("User", back_populates="projects")
    events = relationship("Event", back_populates="project", cascade="all, delete-orphan")
    calendar = relationship("Calendar", back_populates="projects")


class Event(Base):
    """Modelo de evento/tarea"""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    type = Column(String, index=True)  # personal, team, project
    date = Column(String, index=True)  # Formato YYYY-MM-DD
    time = Column(String)  # Formato HH:MM
    duration = Column(Integer, default=60)  # en minutos
    reminder = Column(Integer, default=15)  # en minutos
    email = Column(String, nullable=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    calendar_id = Column(String, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=True)
    creator_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    color = Column(String, nullable=True)
    is_deadline = Column(Boolean, default=False, index=True)
    deadline_date = Column(String, nullable=True, index=True)  # Formato YYYY-MM-DD
    deadline_time = Column(String, nullable=True)  # Formato HH:MM
    
    # Status system
    status = Column(String, nullable=True, index=True)  # completed, early-voluntary, early-forced, extended, abandoned, pending
    status_note = Column(Text, nullable=True)
    actual_date = Column(String, nullable=True)  # Formato YYYY-MM-DD
    actual_time = Column(String, nullable=True)  # Formato HH:MM
    
    # Reminder tracking
    reminder_sent = Column(Boolean, default=False, index=True)

    # Recurrencia
    is_recurring = Column(Boolean, default=False, index=True)
    recurrence_type = Column(String, nullable=True)   # daily, weekly, monthly, weekdays
    recurrence_end = Column(String, nullable=True)    # YYYY-MM-DD — hasta cuándo repetir
    recurrence_group_id = Column(String, nullable=True, index=True)  # agrupa todas las instancias
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Relaciones
    creator = relationship("User", back_populates="events")
    project = relationship("Project", back_populates="events")
    calendar = relationship("Calendar", back_populates="events")
    files = relationship("EventFile", back_populates="event", cascade="all, delete-orphan")
    links = relationship("EventLink", back_populates="event", cascade="all, delete-orphan")
    subtasks = relationship("Subtask", back_populates="event", cascade="all, delete-orphan", order_by="Subtask.position")


class Calendar(Base):
    """Modelo de calendario/equipo"""
    __tablename__ = "calendars"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    color = Column(String, default="#7c6af7")  # Color/tema del calendario
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    owner = relationship("User", back_populates="calendars")
    members = relationship("CalendarMember", back_populates="calendar", cascade="all, delete-orphan")
    messages = relationship("CalendarMessage", back_populates="calendar", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="calendar", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="calendar", cascade="all, delete-orphan")


class CalendarMember(Base):
    """Modelo de miembros del calendario"""
    __tablename__ = "calendar_members"
    
    id = Column(String, primary_key=True, index=True)
    calendar_id = Column(String, ForeignKey("calendars.id", ondelete="CASCADE"), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role = Column(String, default="member")  # owner, editor, viewer
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    calendar = relationship("Calendar", back_populates="members")
    user = relationship("User", back_populates="calendar_memberships")


class EventFile(Base):
    """Modelo de archivos asociados a eventos"""
    __tablename__ = "event_files"
    
    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    filename = Column(String, index=True)  # Nombre original del archivo
    file_path = Column(String)  # Ruta donde se guarda en el servidor
    file_size = Column(Integer)  # Tamaño en bytes
    mime_type = Column(String)  # application/pdf, image/png, etc
    uploaded_by = Column(String, ForeignKey("users.id"))  # Quién subió el archivo
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    event = relationship("Event", back_populates="files")
    uploader = relationship("User", foreign_keys=[uploaded_by])


class EventLink(Base):
    """Links externos asociados a eventos (Google Drive, Notion, etc.)"""
    __tablename__ = "event_links"

    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    url = Column(String, nullable=False)
    label = Column(String, nullable=True)       # Nombre del enlace
    icon = Column(String, nullable=True)         # Emoji del servicio
    added_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relaciones
    event = relationship("Event", back_populates="links")
    creator = relationship("User", foreign_keys=[added_by])


# Crear tablas
Base.metadata.create_all(bind=engine)



class EventTag(Base):
    """Etiquetas personalizadas por usuario"""
    __tablename__ = "event_tags"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    color = Column(String, default="#7c5aff")
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    event_labels = relationship("EventTagAssoc", back_populates="tag", cascade="all, delete-orphan")


class EventTagAssoc(Base):
    """Asociación evento↔etiqueta"""
    __tablename__ = "event_tag_assocs"

    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    tag_id = Column(String, ForeignKey("event_tags.id", ondelete="CASCADE"), index=True)

    event = relationship("Event")
    tag = relationship("EventTag", back_populates="event_labels")


class ActivityTemplate(Base):
    """Plantillas reutilizables de actividades"""
    __tablename__ = "activity_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)         # nombre de la plantilla
    title = Column(String, nullable=False)         # título de la actividad
    type = Column(String, default="personal")
    duration = Column(Integer, default=60)
    reminder = Column(Integer, default=15)
    description = Column(Text, nullable=True)
    email = Column(String, nullable=True)
    color = Column(String, nullable=True)
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])


class Subtask(Base):
    """Subactividades/checklist de un evento"""
    __tablename__ = "subtasks"

    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    done = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="subtasks")


def get_db():
    """Dependencia para obtener la sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CalendarMessage(Base):
    """Mensajes del chat de un calendario"""
    __tablename__ = "calendar_messages"

    id = Column(String, primary_key=True, index=True)
    calendar_id = Column(String, ForeignKey("calendars.id", ondelete="CASCADE"), index=True)
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content = Column(Text, nullable=False)
    msg_type = Column(String, default="text")   # text | system
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)

    # Relaciones
    calendar = relationship("Calendar", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])