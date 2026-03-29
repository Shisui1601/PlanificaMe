from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    id: str
    name: str
    email: str
    role: str = "user"


class UserCreate(BaseModel):
    id: str
    name: str
    email: str
    role: str = "user"


class UserResponse(UserBase):
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    color: str = "#f7a26a"
    created_at: str  # YYYY-MM-DD
    deadline: Optional[str] = None
    calendar_id: Optional[str] = None


class ProjectCreate(ProjectBase):
    creator_id: str


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    deadline: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    creator_id: str
    created_datetime: datetime
    calendar_id: Optional[str] = None
    creator: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: str  # personal, team, project
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    duration: int = 60  # minutos
    reminder: int = 15  # minutos
    email: Optional[str] = None
    project_id: Optional[str] = None
    color: Optional[str] = None
    is_deadline: bool = False
    deadline_date: Optional[str] = None  # YYYY-MM-DD
    deadline_time: Optional[str] = None  # HH:MM
    calendar_id: Optional[str] = None

    # Recurrencia
    is_recurring: bool = False
    recurrence_type: Optional[str] = None   # daily, weekly, monthly, weekdays
    recurrence_end: Optional[str] = None    # YYYY-MM-DD
    recurrence_group_id: Optional[str] = None


class EventCreate(EventBase):
    creator_id: str


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[int] = None
    reminder: Optional[int] = None
    email: Optional[str] = None
    project_id: Optional[str] = None
    color: Optional[str] = None
    deadline_date: Optional[str] = None
    deadline_time: Optional[str] = None
    calendar_id: Optional[str] = None


class EventStatusUpdate(BaseModel):
    status: Optional[str] = None  # completed, early-voluntary, early-forced, extended, abandoned, pending
    status_note: Optional[str] = None
    actual_date: Optional[str] = None  # YYYY-MM-DD
    actual_time: Optional[str] = None  # HH:MM
    deadline_date: Optional[str] = None  # Para extender deadline
    deadline_time: Optional[str] = None
    user_id: Optional[str] = None  # Quién cambió el estado (para notificaciones)


class EventResponse(EventBase):
    id: str
    creator_id: str
    status: Optional[str] = None
    status_note: Optional[str] = None
    actual_date: Optional[str] = None
    actual_time: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    creator: Optional[UserResponse] = None
    project: Optional[ProjectResponse] = None
    calendar: Optional['CalendarResponse'] = None
    
    class Config:
        from_attributes = True


class EventDetailResponse(EventResponse):
    """Respuesta detallada de un evento"""
    pass


class ListEventsResponse(BaseModel):
    events: List[EventResponse]
    total: int


class ListProjectsResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


class HolidayResponse(BaseModel):
    date: str
    name: str
    country: str = "DO"


class CalendarMemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    joined_at: datetime
    user: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class CalendarBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#7c6af7"


class CalendarCreate(CalendarBase):
    owner_id: str


class CalendarResponse(CalendarBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserResponse] = None
    members: List[CalendarMemberResponse] = []
    
    class Config:
        from_attributes = True


class ListCalendarsResponse(BaseModel):
    calendars: List[CalendarResponse]
    total: int


class CalendarMemberBase(BaseModel):
    user_id: str
    role: str = "member"  # owner, editor, viewer


class CalendarMemberCreate(CalendarMemberBase):
    pass


class InviteCalendarMember(BaseModel):
    email: str
    role: str = "member"  # editor, viewer

class FileUploadResponse(BaseModel):
    """Respuesta de carga de archivo"""
    id: str
    event_id: str
    filename: str
    file_size: int
    mime_type: str
    uploaded_at: Optional[str] = None
    message: str = "✓ Archivo subido correctamente"


class EventLinkCreate(BaseModel):
    """Crear un link externo"""
    url: str
    label: Optional[str] = None
    icon: Optional[str] = None
    added_by: Optional[str] = None


class EventLinkResponse(BaseModel):
    """Respuesta de un link externo"""
    id: str
    event_id: str
    url: str
    label: Optional[str] = None
    icon: Optional[str] = None
    added_by: Optional[str] = None
    added_by_name: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Crear un mensaje en el chat del calendario"""
    content: str
    sender_id: str
    msg_type: str = "text"


class MessageResponse(BaseModel):
    """Respuesta de un mensaje"""
    id: str
    calendar_id: str
    sender_id: str
    sender_name: Optional[str] = None
    sender_initial: Optional[str] = None
    content: str
    msg_type: str = "text"
    created_at: str
    edited_at: Optional[str] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True


# Rebuild de modelos para resolver referencias forward
EventResponse.model_rebuild()
CalendarResponse.model_rebuild()

# ── TAGS ──────────────────────────────────────
class TagCreate(BaseModel):
    name: str
    color: str = "#7c5aff"
    owner_id: str

class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    owner_id: str
    class Config: from_attributes = True

# ── TEMPLATES ─────────────────────────────────
class TemplateCreate(BaseModel):
    name: str
    title: str
    type: str = "personal"
    duration: int = 60
    reminder: int = 15
    description: Optional[str] = None
    email: Optional[str] = None
    color: Optional[str] = None
    owner_id: str

class TemplateResponse(BaseModel):
    id: str
    name: str
    title: str
    type: str
    duration: int
    reminder: int
    description: Optional[str] = None
    email: Optional[str] = None
    color: Optional[str] = None
    owner_id: str
    created_at: Optional[str] = None
    class Config: from_attributes = True

# ── SUBTASKS ───────────────────────────────────
class SubtaskCreate(BaseModel):
    title: str
    position: int = 0

class SubtaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None
    position: Optional[int] = None

class SubtaskResponse(BaseModel):
    id: str
    event_id: str
    title: str
    done: bool
    position: int
    class Config: from_attributes = True