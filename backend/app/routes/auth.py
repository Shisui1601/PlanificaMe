"""
routes/auth.py — Endpoints de autenticación
POST /api/auth/register  → Crear cuenta nueva
POST /api/auth/login     → Iniciar sesión, devuelve token JWT
GET  /api/auth/me        → Obtener datos del usuario actual (requiere token)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from ..database import get_db, User
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..utils.helpers import generate_id
from ..services.mail_service import MailService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas específicos de auth ────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


# ════════════════════════════════════════
# REGISTER
# ════════════════════════════════════════

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Crea una cuenta nueva.
    - Verifica que el email no esté en uso
    - Hashea la contraseña con bcrypt
    - Devuelve token JWT listo para usar
    """
    # Verificar que el email no existe
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email ya está registrado"
        )

    # Validar contraseña mínima
    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )

    # Crear usuario con contraseña hasheada
    user = User(
        id=generate_id(),
        name=data.name.strip(),
        email=data.email.lower().strip(),
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generar token
    token = create_access_token(user.id, user.email, user.role)

    # Correo de bienvenida
    try:
        MailService.send_welcome_email(to_email=user.email, user_name=user.name)
    except Exception as e:
        logger.error(f'Error enviando bienvenida: {str(e)}')

    return AuthResponse(
        token=token,
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        }
    )


# ════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════

@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Inicia sesión con email y contraseña.
    - Busca el usuario por email
    - Verifica la contraseña con bcrypt
    - Devuelve token JWT
    """
    # Buscar usuario por email
    user = db.query(User).filter(
        User.email == data.email.lower().strip()
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # Verificar contraseña
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Esta cuenta no tiene contraseña configurada. Contáctate con el administrador."
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta está desactivada"
        )

    # Generar token
    token = create_access_token(user.id, user.email, user.role)

    return AuthResponse(
        token=token,
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        }
    )


# ════════════════════════════════════════
# ME — datos del usuario actual
# ════════════════════════════════════════

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """
    Devuelve los datos del usuario autenticado.
    Requiere token en el header: Authorization: Bearer <token>
    """
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat()
    }


# ════════════════════════════════════════
# CHANGE PASSWORD
# ════════════════════════════════════════

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cambia la contraseña del usuario autenticado"""
    if not verify_password(data.current_password, current_user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta"
        )

    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 6 caracteres"
        )

    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "Contraseña actualizada correctamente"}


# ════════════════════════════════════════
# SET PASSWORD — para usuarios sin contraseña
# ════════════════════════════════════════

class SetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str


@router.post("/set-password",
    summary="Asignar contraseña a usuario existente",
    description="Permite asignar contraseña a usuarios que fueron creados antes de implementar auth. Solo funciona si el usuario NO tiene contraseña aún.")
def set_password(data: SetPasswordRequest, db: Session = Depends(get_db)):
    """
    Asigna contraseña a un usuario existente que no tiene.
    Solo funciona si password_hash es NULL (usuarios viejos).
    """
    user = db.query(User).filter(
        User.email == data.email.lower().strip()
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado con ese email"
        )

    if user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuario ya tiene contraseña. Usa /change-password para cambiarla."
        )

    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )

    user.password_hash = hash_password(data.new_password)
    db.commit()

    return {
        "message": f"✓ Contraseña asignada a {user.name}",
        "email": user.email,
        "hint": "Ahora puedes iniciar sesión con POST /api/auth/login"
    }