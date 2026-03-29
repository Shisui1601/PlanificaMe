# PlanificaMe - Backend API

Backend de PlanificaMe: Sistema de gestión de tareas y proyectos con Calendario Integrado.

## Stack Tecnológico

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (Supabase)
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **Email**: SMTP (Gmail)
- **Hosting**: Railway

## Características

✅ Gestión completa de eventos/tareas  
✅ Proyectos meta con seguimiento  
✅ Sistema de estados de actividades  
✅ Recordatorios automáticos por correo  
✅ Advertencias de fechas límite  
✅ Búsqueda de eventos  
✅ Filtros por tipo y estado  
✅ Feriados de República Dominicana  

## Requisitos Previos

- Python 3.11+
- Docker (para Railway)
- Cuenta en Supabase
- Cuenta en Railway
- Cuenta Gmail (para SMTP)

## Instalación Local

### 1. Clonar y preparar entorno

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
nano .env  # Editar con tus valores
```

Variables requeridas:
- `DATABASE_URL`: PostgreSQL (Supabase)
- `REDIS_URL`: Redis para Celery
- `SMTP_USER`/`SMTP_PASSWORD`: Gmail SMTP
- `SENDER_EMAIL`: Tu correo
- `FRONTEND_URL`: URL del frontend

### 3. Ejecutar localmente

**Terminal 1 - FastAPI:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A app.celery_app worker --loglevel=info
```

**Terminal 3 - Celery Beat (Scheduler):**
```bash
celery -A app.celery_app beat --loglevel=info
```

API estará en: http://localhost:8000/docs

---

## Despliegue en Producción

### Opción 1: Railway + Supabase + Vercel

#### Paso 1: Crear base de datos en Supabase

1. Ir a https://app.supabase.com y crear nuevo proyecto
2. En Settings → Database → Connection Pooling → obtener URL
3. Copiar la URL (formato: `postgresql://...`)

#### Paso 2: Crear Redis en Railway

1. Ir a railway.app
2. New Project → Database → Redis
3. Copiar la URL de conexión

#### Paso 3: Desplegar API en Railway

1. Conectar repositorio GitHub con Railway
2. Crear nuevo servicio desde Dockerfile
3. Agregar variables de entorno:

```
DATABASE_URL=postgresql://...  # De Supabase
REDIS_URL=redis://...          # De Railway Redis
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
SENDER_EMAIL=tu_email@gmail.com
FRONTEND_URL=https://tu-proyecto.vercel.app
```

4. Railway auto-asigna un puerto. Anotar la URL pública

#### Paso 4: Configurar Gmail SMTP

1. Activar 2FA en Google Account
2. Ir a https://myaccount.google.com/apppasswords
3. Seleccionar "Correo" y "Windows/Linux"
4. Copiar la contraseña generada
5. Usar como `SMTP_PASSWORD`

#### Paso 5: Desplegar Frontend en Vercel

1. Crear proyecto React/Vite
2. Conectar repositorio con Vercel
3. Agregar variable de entorno:

```
VITE_API_URL=https://tu-railway-url.railway.app
```

4. Desplegar

---

## Estructura de Carpetas

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuración
│   ├── celery_app.py          # Setup de Celery
│   ├── database.py            # SQLAlchemy & modelos
│   ├── tasks.py               # Tareas asincrónicas
│   ├── models/                # Modelos ORM
│   ├── routes/                # Rutas/endpoints
│   │   ├── users.py
│   │   ├── projects.py
│   │   ├── events.py
│   │   └── holidays.py
│   ├── schemas/               # Esquemas Pydantic
│   │   └── schemas.py
│   ├── services/              # Lógica de negocio
│   │   ├── user_service.py
│   │   ├── project_service.py
│   │   ├── event_service.py
│   │   └── mail_service.py
│   └── utils/                 # Utilidades
│       └── helpers.py
├── main.py                    # Aplicación principal
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
└── README.md
```

---

## API Endpoints

### Users
- `POST /api/users/` - Crear usuario
- `GET /api/users/{id}` - Obtener usuario
- `GET /api/users/` - Listar todos

### Projects
- `POST /api/projects/` - Crear proyecto
- `GET /api/projects/{id}` - Obtener proyecto
- `GET /api/projects/` - Listar todos
- `PATCH /api/projects/{id}` - Actualizar
- `DELETE /api/projects/{id}` - Eliminar

### Events
- `POST /api/events/` - Crear evento
- `GET /api/events/{id}` - Obtener evento
- `GET /api/events/` - Listar con filtros
- `GET /api/events/by-date/{date}` - Por fecha
- `GET /api/events/search/{query}` - Buscar
- `PATCH /api/events/{id}` - Actualizar
- `PATCH /api/events/{id}/status` - Cambiar estado
- `DELETE /api/events/{id}` - Eliminar

### Holidays
- `GET /api/holidays/{date}` - Feriado de una fecha
- `GET /api/holidays/by-month/{year}/{month}` - Feriados del mes
- `GET /api/holidays/by-year/{year}` - Feriados del año

### Health
- `GET /` - Bienvenida
- `GET /health` - Health check
- `GET /api/status` - Estado detallado

---

## Modelos de Datos

### User
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "role": "user|admin",
  "created_at": "datetime"
}
```

### Project
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "color": "#hex",
  "creator_id": "uuid",
  "created_at": "YYYY-MM-DD",
  "deadline": "YYYY-MM-DD"
}
```

### Event
```json
{
  "id": "uuid",
  "title": "string",
  "type": "personal|team|project",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "duration": 60,
  "reminder": 15,
  "status": "pending|completed|extended|abandoned",
  "deadline_date": "YYYY-MM-DD",
  "creator_id": "uuid",
  "project_id": "uuid|null"
}
```

---

## Tareas Asincrónicas (Celery)

### Recordatorios
- Se ejecuta cada minuto
- Envía correo N minutos antes del evento
- Configurable por evento

### Advertencias de Deadline
- Se ejecuta cada hora
- Notifica 7, 3, 1 día, hoy y cuando venció
- Para eventos con fecha límite

### Actualización de Estado
- Se ejecuta bajo demanda
- Notifica cambios de estado al usuario

---

## Costos Estimados

| Servicio | Costo Base | Escala |
|----------|-----------|--------|
| Supabase | $0/mes | $25+/mes (Prod) |
| Railway  | $5/mes min | Desde $5 |
| Vercel   | $0/mes | $20+/mes (Pro) |
| Gmail    | $0 (500/día) | Siempre gratis* |
| **Total**| **$5/mes** | **$50+/mes (advanced)** |

*Incluido en Google Workspace

---

## Troubleshooting

### Error de conexión PostgreSQL
```
Solución: Verificar DATABASE_URL en .env
Railway lo asigna automáticamente
```

### Celery no envía correos
```
Solución: 
1. Verificar REDIS_URL
2. Revisar SMTP_USER y SMTP_PASSWORD
3. Usar contraseña de aplicación, no PIN
4. Activar acceso de apps menos seguras (si aplica)
```

### Recordatorios no llegan
```
Solución:
1. Verificar que Celery Beat está corriendo
2. Revisar logs con: redis-cli
3. Confirmar email en evento
```

### CORS error en frontend
```
Solución: Actualizar CORS_ORIGINS en config.py
Agregar URL del frontend
```

---

## Variables de Entorno Completas

Ver [.env.example](.env.example)

---

## Documentación API

Una vez ejecutando, acceder a:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Contribución

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

---

## Licencia

Este proyecto está bajo la Licencia MIT. Ver LICENSE para detalles.

---

## Soporte

Para reportar bugs o sugerencias:
- GitHub Issues: [repository/issues](https://github.com/repository/issues)
- Email: soporte@planificame.app

---

**Hecho con ❤️ en República Dominicana 🇩🇴**
