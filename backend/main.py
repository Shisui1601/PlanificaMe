from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .app.config import settings
from .app.database import Base, engine
from .app.routes import users, projects, events, holidays, calendars, files
from .app.routes import messages as messages_route
from .app.routes import tags as tags_route
from .app.routes import templates as templates_route
from .app.routes import subtasks as subtasks_route
from .app.routes import auth as auth_route
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear tablas
Base.metadata.create_all(bind=engine)


# ════════════════════════════════════════
# SCHEDULER — APScheduler dentro del proceso uvicorn
# No requiere Celery worker externo
# ════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia y detiene el scheduler de tareas programadas."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.events import EVENT_JOB_ERROR
        import pytz
        from .app.scheduler import run_reminders, run_deadline_check, run_cleanup

        tz = pytz.timezone("America/Santo_Domingo")
        scheduler = BackgroundScheduler(timezone=tz)

        def on_error(event):
            if event.exception:
                logger.error(f"[Scheduler] Error en tarea '{event.job_id}': {event.exception}")

        scheduler.add_listener(on_error, EVENT_JOB_ERROR)
        scheduler.add_job(run_reminders,     'interval', seconds=60,   id='reminders',  max_instances=1)
        scheduler.add_job(run_deadline_check,'interval', hours=1,      id='deadlines',  max_instances=1)
        scheduler.add_job(run_cleanup,       'cron',     hour=2, minute=0, id='cleanup',max_instances=1)
        scheduler.start()
        logger.info("🚀 APScheduler iniciado — recordatorios activos cada 60s")
    except Exception as e:
        logger.error(f"Error iniciando scheduler: {e}")
        scheduler = None

    yield

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏹  APScheduler detenido")


# Crear aplicación FastAPI
app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API para PlanificaMe - Sistema de Gestión de Tareas y Proyectos"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth_route.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(events.router)
app.include_router(holidays.router)
app.include_router(calendars.router)
app.include_router(files.router)
app.include_router(files.download_router)
app.include_router(messages_route.router)
app.include_router(tags_route.router)
app.include_router(templates_route.router)
app.include_router(subtasks_route.router)

# Servir archivos estáticos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(parent_dir, "")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz de bienvenida - Sirve el archivo HTML"""
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(parent_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "message": "Bienvenido a PlanificaMe API - index.html no encontrado"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica que la API está funcionando"""
    return {
        "status": "healthy",
        "service": "PlanificaMe API",
        "version": settings.APP_VERSION
    }


@app.get("/api/debug/trigger-reminders", tags=["Debug"])
async def trigger_reminders_now():
    """Dispara el chequeo de recordatorios manualmente y muestra diagnóstico."""
    try:
        import pytz
        from datetime import datetime
        from .app.database import SessionLocal, Event
        from .app.utils.helpers import time_to_minutes

        tz = pytz.timezone("America/Santo_Domingo")
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        current_minutes = now.hour * 60 + now.minute

        # Diagnosticar eventos candidatos ANTES de ejecutar
        db = SessionLocal()
        try:
            candidates = db.query(Event).filter(
                Event.date == today,
                Event.email != None,
                Event.email != "",
                Event.reminder_sent == False,
            ).all()
            diag = []
            for ev in candidates:
                em = time_to_minutes(ev.time) if ev.time else None
                rt = em - ev.reminder if em is not None and ev.reminder is not None else None
                diff = abs(current_minutes - rt) if rt is not None else None
                diag.append({
                    "id": ev.id, "title": ev.title,
                    "time": ev.time, "reminder_min": ev.reminder,
                    "email": ev.email,
                    "event_minutes": em, "reminder_fires_at": rt,
                    "current_minutes": current_minutes,
                    "diff_minutes": diff,
                    "would_fire": diff is not None and diff <= 1
                })
        finally:
            db.close()

        # Ejecutar el recordatorio
        from .app.scheduler import run_reminders
        run_reminders()

        return {
            "status": "executed",
            "local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_minutes": current_minutes,
            "timezone": "America/Santo_Domingo",
            "today": today,
            "candidates_today": len(diag),
            "events": diag,
            "message": "Revisa los logs de Render y los eventos listados arriba para diagnosticar."
        }
    except Exception as e:
        import traceback
        return {"status": "error", "detail": str(e), "trace": traceback.format_exc()}


@app.get("/api/status", tags=["Health"])
async def api_status():
    """Estado detallado de la API"""
    return {
        "status": "operational",
        "service": "PlanificaMe API",
        "version": settings.APP_VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "features": {
            "events": True,
            "projects": True,
            "users": True,
            "holidays": True,
            "reminders": True,
            "email_notifications": True,
            "pwa":    True,
            "ics":    True,
            "digest": True,
        }
    }


# ─── PWA: servir sw.js y manifest.json desde la raíz ──────────────────────────

@app.get("/sw.js", tags=["PWA"])
async def serve_sw():
    """Serve Service Worker desde la raíz (mismo origen que la app)"""
    sw_path = os.path.join(parent_dir, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript",
                            headers={"Service-Worker-Allowed": "/"})
    return JSONResponse(status_code=404, content={"error": "sw.js no encontrado"})


@app.get("/manifest.json", tags=["PWA"])
async def serve_manifest():
    """Serve Web App Manifest"""
    manifest_path = os.path.join(parent_dir, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return JSONResponse(status_code=404, content={"error": "manifest.json no encontrado"})


# ─── Weekly Digest: trigger manual ────────────────────────────────────────────

@app.post("/api/digest/send/{user_id}", tags=["Digest"])
async def send_digest_now(user_id: str):
    """
    Envía el digest semanal de forma inmediata a un usuario específico.
    Llama al mismo servicio que el scheduler automático (lunes 8 AM).
    """
    try:
        from .app.database import SessionLocal, Event, User
        from .app.services.mail_service import MailService
        from datetime import datetime, timedelta

        db   = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            db.close()
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})
        if not user.email:
            db.close()
            return JSONResponse(status_code=400, content={"error": "El usuario no tiene email configurado"})

        today     = datetime.today().date()
        week_end  = today + timedelta(days=7)
        week_start = today - timedelta(days=7)
        week_label = f"{today.strftime('%d/%m')} — {week_end.strftime('%d/%m/%Y')}"

        upcoming = db.query(Event).filter(
            Event.creator_id == user_id,
            Event.date >= today.strftime("%Y-%m-%d"),
            Event.date <= week_end.strftime("%Y-%m-%d"),
            Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
        ).order_by(Event.date, Event.time).all()

        completed_count = db.query(Event).filter(
            Event.creator_id == user_id,
            Event.updated_at >= datetime.combine(week_start, datetime.min.time()),
            Event.status.in_(["completed", "early-voluntary", "early-forced"])
        ).count()

        overdue = db.query(Event).filter(
            Event.creator_id == user_id,
            Event.deadline_date < today.strftime("%Y-%m-%d"),
            Event.status.notin_(["completed", "early-voluntary", "early-forced", "abandoned"])
        ).all()

        upcoming_data = [{"title": e.title, "date": e.date, "time": e.time, "type": e.type} for e in upcoming]
        overdue_data  = [{"title": e.title, "deadline_date": e.deadline_date} for e in overdue]

        db.close()

        success = MailService.send_weekly_summary_email(
            to_email=user.email,
            user_name=user.name,
            upcoming_events=upcoming_data,
            overdue_events=overdue_data,
            completed_this_week=completed_count,
            week_label=week_label
        )

        if success:
            logger.info(f"📊 Digest manual enviado → {user.name} ({user.email})")
            return {"status": "sent", "email": user.email, "upcoming": len(upcoming_data), "completed": completed_count}
        else:
            return JSONResponse(status_code=500, content={"error": "Error al enviar el email"})

    except Exception as e:
        logger.error(f"Error en digest manual: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── Push Notifications: VAPID key + subscription ─────────────────────────────

@app.get("/api/push/vapid-key", tags=["Push"])
async def get_vapid_key():
    """
    Devuelve la clave pública VAPID para el frontend.
    Si no está configurada, devuelve null (se desactiva el push server-side).
    """
    vapid_public = getattr(settings, "VAPID_PUBLIC_KEY", None)
    return {"public_key": vapid_public}


@app.post("/api/push/subscribe", tags=["Push"])
async def push_subscribe(payload: dict):
    """
    Almacena la suscripción push de un usuario (endpoint + keys).
    Guarda en DB para enviar notificaciones cuando la app esté cerrada.
    """
    user_id      = payload.get("user_id")
    subscription = payload.get("subscription")
    if not user_id or not subscription:
        return JSONResponse(status_code=400, content={"error": "Faltan campos requeridos"})
    # Aquí se almacenaría en BD — por ahora retornamos OK
    # (implementación completa requiere tabla push_subscriptions + pywebpush)
    logger.info(f"🔔 Push subscription recibida para user {user_id}")
    return {"status": "subscribed", "user_id": user_id}


# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones"""
    logger.error(f"Error no manejado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc) if settings.DEBUG else "Ocurrió un error inesperado"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )