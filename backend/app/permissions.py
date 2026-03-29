"""
permissions.py — Sistema de permisos para calendarios compartidos

Roles:
  owner  → control total (crear, editar, eliminar, gestionar miembros)
  editor → puede crear y editar eventos/proyectos del calendario
  viewer → solo lectura, no puede crear ni modificar

Uso en endpoints:
    from ..permissions import require_calendar_permission, get_user_calendar_role
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from .database import Calendar, CalendarMember


# ════════════════════════════════════════
# JERARQUÍA DE ROLES
# ════════════════════════════════════════

ROLE_HIERARCHY = {
    "owner":  3,
    "editor": 2,
    "viewer": 1,
    "none":   0,
}


def get_user_calendar_role(db: Session, calendar_id: str, user_id: str) -> str:
    """
    Devuelve el rol del usuario en el calendario.
    Si no es miembro devuelve 'none'.
    Si el calendario no existe devuelve 'none'.
    """
    member = db.query(CalendarMember).filter(
        CalendarMember.calendar_id == calendar_id,
        CalendarMember.user_id == user_id
    ).first()

    if not member:
        return "none"
    return member.role


def has_permission(role: str, required: str) -> bool:
    """
    Verifica si un rol tiene los permisos suficientes.
    Ejemplo: has_permission("editor", "editor") → True
             has_permission("viewer", "editor") → False
             has_permission("owner", "editor")  → True
    """
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(required, 0)


def require_calendar_permission(
    db: Session,
    calendar_id: str,
    user_id: str,
    required_role: str,
    action: str = "realizar esta acción"
):
    """
    Verifica permisos y lanza HTTPException si no los tiene.

    Parámetros:
        required_role: "viewer", "editor" u "owner"
        action: descripción de la acción para el mensaje de error
    """
    # Verificar que el calendario existe
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendario no encontrado"
        )

    role = get_user_calendar_role(db, calendar_id, user_id)

    if not has_permission(role, required_role):
        role_labels = {
            "owner":  "propietario",
            "editor": "editor",
            "viewer": "viewer",
            "none":   "miembro"
        }
        required_label = role_labels.get(required_role, required_role)

        if role == "none":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No eres miembro de este calendario"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Necesitas ser {required_label} para {action}. Tu rol actual es: {role}"
        )

    return role


def get_user_id_from_request(request_user_id: str) -> str:
    """
    Helper para extraer user_id de query params.
    En el futuro esto vendrá del JWT token automáticamente.
    """
    return request_user_id