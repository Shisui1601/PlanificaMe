from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ListProjectsResponse
from ..services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/", response_model=ListProjectsResponse)
def get_all_projects(db: Session = Depends(get_db), calendar_id: Optional[str] = None):
    """Obtiene todos los proyectos, con filtro opcional por calendario"""
    if calendar_id:
        projects = ProjectService.get_projects_by_calendar(db, calendar_id)
    else:
        projects = ProjectService.get_all_projects(db)
    return ListProjectsResponse(projects=projects, total=len(projects))


@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Crea un nuevo proyecto meta"""
    return ProjectService.create_project(db, project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Obtiene un proyecto por ID"""
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.get("/creator/{creator_id}", response_model=ListProjectsResponse)
def get_projects_by_creator(creator_id: str, db: Session = Depends(get_db)):
    """Obtiene los proyectos de un creador"""
    projects = ProjectService.get_projects_by_creator(db, creator_id)
    return ListProjectsResponse(projects=projects, total=len(projects))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """Actualiza un proyecto"""
    project = ProjectService.update_project(db, project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Elimina un proyecto y sus eventos asociados"""
    if not ProjectService.delete_project(db, project_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"message": "Proyecto eliminado"}