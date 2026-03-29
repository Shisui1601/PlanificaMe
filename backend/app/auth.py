"""
auth.py — Utilidades de autenticación
- Hash de contraseñas con bcrypt
- Creación y verificación de tokens JWT
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db, User

# ── Configuración ──────────────────────────────────────────
SECRET_KEY = "planificame-secret-key-cambiar-en-produccion-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24  # El token dura 24 horas

# ── bcrypt context para hashear contraseñas ────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Esquema de seguridad HTTP Bearer ──────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


# ════════════════════════════════════════
# CONTRASEÑAS
# ════════════════════════════════════════

def hash_password(plain_password: str) -> str:
    """Convierte una contraseña legible en un hash seguro"""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que una contraseña coincide con su hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ════════════════════════════════════════
# TOKENS JWT
# ════════════════════════════════════════

def create_access_token(user_id: str, email: str, role: str) -> str:
    """
    Crea un JWT token con los datos del usuario.
    El token expira en ACCESS_TOKEN_EXPIRE_HOURS horas.
    """
    payload = {
        "sub": user_id,           # subject = id del usuario
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica y verifica un JWT token.
    Devuelve el payload si es válido, None si es inválido o expirado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ════════════════════════════════════════
# DEPENDENCIA FastAPI — get_current_user
# ════════════════════════════════════════

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependencia FastAPI que extrae y valida el token de cada request.
    Uso: agregar `current_user: User = Depends(get_current_user)` a un endpoint.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Igual que get_current_user pero no lanza error si no hay token.
    Útil para endpoints que funcionan con o sin autenticación.
    """
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("sub")).first()