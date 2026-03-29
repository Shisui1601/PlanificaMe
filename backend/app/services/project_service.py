from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..database import Project, Event
from ..schemas.schemas import ProjectCreate, ProjectUpdate
from ..utils.helpers import generate_id
from typing import List, Optional
from datetime import datetime


class ProjectService:
    """Servicio para manejar operaciones con proyectos meta"""
    
    @staticmethod
    def create_project(db: Session, project: ProjectCreate) -> Project:
        """Crea un nuevo proyecto meta"""
        db_project = Project(
            id=generate_id(),
            title=project.title,
            description=project.description,
            color=project.color,
            creator_id=project.creator_id,
            created_at=project.created_at,
            deadline=project.deadline,
            calendar_id=project.calendar_id
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    
    @staticmethod
    def get_project(db: Session, project_id: str) -> Optional[Project]:
        """Obtiene un proyecto por ID"""
        return db.query(Project).filter(Project.id == project_id).first()
    
    @staticmethod
    def get_projects_by_creator(db: Session, creator_id: str) -> List[Project]:
        """Obtiene todos los proyectos de un usuario"""
        return db.query(Project).filter(Project.creator_id == creator_id).all()
    
    @staticmethod
    def get_all_projects(db: Session) -> List[Project]:
        """Obtiene todos los proyectos"""
        return db.query(Project).all()

    @staticmethod
    def get_projects_by_calendar(db: Session, calendar_id: str) -> List[Project]:
        """Obtiene todos los proyectos de un calendario"""
        return db.query(Project).filter(Project.calendar_id == calendar_id).all()
    
    @staticmethod
    def update_project(db: Session, project_id: str, project_update: ProjectUpdate) -> Optional[Project]:
        """Actualiza un proyecto"""
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if db_project:
            update_data = project_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_project, field, value)
            db.commit()
            db.refresh(db_project)
        return db_project
    
    @staticmethod
    def delete_project(db: Session, project_id: str) -> bool:
        """Elimina un proyecto y sus eventos asociados"""
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if db_project:
            # Eliminar eventos asociados
            db.query(Event).filter(Event.project_id == project_id).delete()
            db.delete(db_project)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_project_tasks(db: Session, project_id: str) -> List[Event]:
        """Obtiene todas las tareas de un proyecto"""
        return db.query(Event).filter(Event.project_id == project_id).all()
    
    @staticmethod
    def get_project_task_count(db: Session, project_id: str) -> int:
        """Obtiene el número de tareas en un proyecto"""
        return db.query(Event).filter(Event.project_id == project_id).count()
    
    @staticmethod
    def get_project_completed_tasks(db: Session, project_id: str) -> int:
        """Obtiene el número de tareas completadas en un proyecto"""
        return db.query(Event).filter(
            and_(Event.project_id == project_id, Event.status == "completed")
        ).count()