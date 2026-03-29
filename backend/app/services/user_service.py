from sqlalchemy.orm import Session
from ..database import User
from ..schemas.schemas import UserCreate, UserResponse
from ..utils.helpers import generate_id
from typing import List, Optional


class UserService:
    """Servicio para manejar operaciones con usuarios"""
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Crea un nuevo usuario"""
        db_user = User(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_user(db: Session, user_id: str) -> Optional[User]:
        """Obtiene un usuario por ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_all_users(db: Session) -> List[User]:
        """Obtiene todos los usuarios (equipo)"""
        return db.query(User).all()
    
    @staticmethod
    def user_exists(db: Session, user_id: str) -> bool:
        """Verifica si un usuario existe"""
        return db.query(User).filter(User.id == user_id).first() is not None
    
    @staticmethod
    def delete_user(db: Session, user_id: str) -> bool:
        """Elimina un usuario"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
