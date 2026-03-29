from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid


def generate_id() -> str:
    """Genera un ID único en formato similar al del frontend"""
    return str(uuid.uuid4())


# Definir las fechas de feriados en República Dominicana para 2026
HOLIDAYS_DO_2026 = {
    "2026-01-01": "Año Nuevo",
    "2026-01-26": "Día de Duarte",
    "2026-02-27": "Independencia",
    "2026-04-10": "Viernes Santo",
    "2026-05-01": "Día del Trabajo",
    "2026-08-16": "Restauración",
    "2026-10-12": "Día de Colón",
    "2026-11-01": "Día de Todos los Santos",
    "2026-11-09": "Día de la Independencia (feriado adicional)",
    "2026-12-25": "Navidad",
    "2026-12-24": "Nochebuena (no oficial pero observado)",
}

# Próximos años para comodidad
HOLIDAYS_DO_2027 = {
    "2027-01-01": "Año Nuevo",
    "2027-01-26": "Día de Duarte",
    "2027-02-27": "Independencia",
    "2027-03-30": "Viernes Santo",
    "2027-05-01": "Día del Trabajo",
    "2027-08-16": "Restauración",
    "2027-10-12": "Día de Colón",
    "2027-11-01": "Día de Todos los Santos",
    "2027-11-09": "Día de la Independencia",
    "2027-12-25": "Navidad",
}

HOLIDAYS_DO = {**HOLIDAYS_DO_2026, **HOLIDAYS_DO_2027}


def get_holiday(date_str: str) -> Optional[str]:
    """Retorna el nombre del feriado si existe para la fecha dada (formato YYYY-MM-DD)"""
    return HOLIDAYS_DO.get(date_str)


def is_holiday(date_str: str) -> bool:
    """Verifica si una fecha es feriado"""
    return date_str in HOLIDAYS_DO


def format_date(date_obj: datetime) -> str:
    """Formatea una fecha a YYYY-MM-DD"""
    return date_obj.strftime("%Y-%m-%d")


def format_time(hour: int, minute: int = 0) -> str:
    """Formatea hora a HH:MM"""
    return f"{hour:02d}:{minute:02d}"


def time_to_minutes(time_str: str) -> int:
    """Convierte HH:MM a minutos desde medianoche"""
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except:
        return 0


def minutes_to_time(minutes: int) -> str:
    """Convierte minutos desde medianoche a HH:MM"""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def format_12hour(time_str: str) -> str:
    """Convierte HH:MM a formato 12 horas"""
    try:
        h, m = map(int, time_str.split(":"))
        ap = "AM" if h < 12 else "PM"
        dh = 12 if h == 0 else h if h <= 12 else h - 12
        return f"{dh:02d}:{m:02d} {ap}"
    except:
        return time_str


def format_date_readable(date_str: str) -> str:
    """Formatea YYYY-MM-DD a un formato legible"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return f"{d.day} {months[d.month-1]}"
    except:
        return date_str


def get_days_until(date_str: str) -> int:
    """Retorna los días hasta una fecha (negativo si ya pasó)"""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.today()
        delta = (target - today).days
        return delta
    except:
        return 0


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse una fecha en formato YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None
