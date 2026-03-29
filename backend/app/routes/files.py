from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db, Event, EventFile, EventLink, User
from backend.app.schemas.schemas import FileUploadResponse, EventLinkCreate, EventLinkResponse
import os
import shutil
from pathlib import Path as PathlibPath
import mimetypes
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/events", tags=["Files"])
download_router = APIRouter(prefix="/api/files", tags=["Files"])

# Crear carpeta de uploads si no existe
UPLOAD_DIR = PathlibPath(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Tipos MIME permitidos
ALLOWED_MIMES = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'video/mp4': '.mp4',
    'video/mpeg': '.mpeg',
    'video/quicktime': '.mov',
    'audio/mpeg': '.mp3',
    'audio/wav': '.wav',
    'text/plain': '.txt',
    'text/csv': '.csv',
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/{event_id}/files", response_model=FileUploadResponse)
async def upload_file(
    event_id: str = Path(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = "u1"
):
    """Subir un archivo a un evento"""
    
    # Validar que el evento existe
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    # Validar tamaño del archivo
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande. Máximo: 20 MB"
        )
    
    # Validar tipo MIME
    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
    if mime_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: {mime_type}"
        )
    
    # Generar nombre único para el archivo
    file_extension = ALLOWED_MIMES.get(mime_type, PathlibPath(file.filename).suffix)
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / event_id
    file_path.mkdir(parents=True, exist_ok=True)
    
    full_path = file_path / unique_filename
    
    # Guardar archivo
    try:
        with open(full_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")
    
    # Guardar registro en BD
    db_file = EventFile(
        id=str(uuid.uuid4()),
        event_id=event_id,
        filename=file.filename,  # Nombre original
        file_path=str(full_path.relative_to(UPLOAD_DIR.parent)),
        file_size=len(file_content),
        mime_type=mime_type,
        uploaded_by=user_id
    )
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return FileUploadResponse(
        id=db_file.id,
        event_id=db_file.event_id,
        filename=db_file.filename,
        file_size=db_file.file_size,
        mime_type=db_file.mime_type,
        uploaded_at=db_file.created_at.isoformat() if db_file.created_at else None,
        message="✓ Archivo subido correctamente"
    )


@router.get("/{event_id}/files")
async def list_event_files(
    event_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Listar archivos de un evento"""
    
    # Validar que el evento existe
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    files = db.query(EventFile).filter(EventFile.event_id == event_id).all()
    
    return {
        "event_id": event_id,
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "file_size": f.file_size,
                "mime_type": f.mime_type,
                "uploaded_at": f.created_at.isoformat() if f.created_at else None,
                "uploaded_by": f.uploader.name if f.uploader else f.uploaded_by or "Desconocido"
            }
            for f in files
        ],
        "total": len(files)
    }


@router.delete("/{event_id}/files/{file_id}")
async def delete_file(
    event_id: str = Path(...),
    file_id: str = Path(...),
    db: Session = Depends(get_db),
    user_id: str = "u1"
):
    """Eliminar un archivo de un evento"""
    
    # Validar que el evento existe
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    # Validar que el archivo existe
    file_obj = db.query(EventFile).filter(
        EventFile.id == file_id,
        EventFile.event_id == event_id
    ).first()
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Eliminar archivo del servidor
    file_path = UPLOAD_DIR.parent / file_obj.file_path
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"Error al eliminar archivo: {e}")
    
    # Eliminar registro de BD
    db.delete(file_obj)
    db.commit()
    
    return {"message": "✓ Archivo eliminado"}


@download_router.get("/{file_id}/download")
async def download_file(
    file_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Descargar un archivo"""
    
    file_obj = db.query(EventFile).filter(EventFile.id == file_id).first()
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    file_path = UPLOAD_DIR.parent / file_obj.file_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no existe en el servidor")
    
    return FileResponse(
        path=file_path,
        filename=file_obj.filename,
        media_type=file_obj.mime_type
    )

# ════════════════════════════════════════
# LINKS EXTERNOS
# ════════════════════════════════════════

@router.post("/{event_id}/links", response_model=EventLinkResponse, status_code=201)
async def add_event_link(
    event_id: str = Path(...),
    link: EventLinkCreate = ...,
    db: Session = Depends(get_db)
):
    """Agregar un link externo a un evento"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    db_link = EventLink(
        id=str(uuid.uuid4()),
        event_id=event_id,
        url=link.url,
        label=link.label,
        icon=link.icon,
        added_by=link.added_by
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)

    added_by_name = None
    if db_link.creator:
        added_by_name = db_link.creator.name

    return EventLinkResponse(
        id=db_link.id,
        event_id=db_link.event_id,
        url=db_link.url,
        label=db_link.label,
        icon=db_link.icon,
        added_by=db_link.added_by,
        added_by_name=added_by_name,
        created_at=db_link.created_at.isoformat() if db_link.created_at else None
    )


@router.get("/{event_id}/links")
async def list_event_links(
    event_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Listar links externos de un evento"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    links = db.query(EventLink).filter(
        EventLink.event_id == event_id
    ).order_by(EventLink.created_at).all()

    return {
        "event_id": event_id,
        "links": [
            {
                "id": lnk.id,
                "url": lnk.url,
                "label": lnk.label,
                "icon": lnk.icon,
                "added_by": lnk.added_by,
                "added_by_name": lnk.creator.name if lnk.creator else None,
                "created_at": lnk.created_at.isoformat() if lnk.created_at else None
            }
            for lnk in links
        ],
        "total": len(links)
    }


@router.delete("/{event_id}/links/{link_id}")
async def delete_event_link(
    event_id: str = Path(...),
    link_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Eliminar un link externo"""
    lnk = db.query(EventLink).filter(
        EventLink.id == link_id,
        EventLink.event_id == event_id
    ).first()

    if not lnk:
        raise HTTPException(status_code=404, detail="Link no encontrado")

    db.delete(lnk)
    db.commit()
    return {"message": "✓ Link eliminado"}