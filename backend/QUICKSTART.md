# ⚡ PlanificaMe - Quick Start Guide

Guía rápida para empezar con PlanificaMe en 5 minutos.

---

## 📦 Lo que ya tienes

✓ Backend FastAPI completo en `backend/`  
✓ Configuración para Supabase + Railway + Vercel  
✓ Sistema de recordatorios con Celery  
✓ Correos automáticos con Gmail SMTP  
✓ Frontend HTML/CSS/JS en `index.html`  

---

## 🚀 Opción 1: Despliegue Rápido (Recomendado)

### Paso 1: Preparar repositorio y GitHub

```bash
# En la carpeta PlanificaMe
git init
git add .
git commit -m "Initial commit - PlanificaMe"
git remote add origin https://github.com/tu_usuario/planificame.git
git push -u origin main
```

### Paso 2: Crear base de datos Supabase (5 min)

1. Ir a https://app.supabase.com
2. Click **"New Project"**
3. Nombre: `planificame`, Contraseña: tu contraseña
4. Copiar **DATABASE_URL** de Settings → Database

### Paso 3: Desplegar en Railway (5 min)

1. Ir a https://railway.app
2. Click **"New Project"**
3. Seleccionar tu repositorio GitHub
4. Agregar variables de entorno:

```
DATABASE_URL=tu_supabase_url
REDIS_URL=se_configura_automático
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
FRONTEND_URL=se_actualiza_después
```

5. Railway auto-deploya. **Copiar URL pública** (ej: `https://api.railway.app`)

### Paso 4: Desplegar Frontend en Vercel (5 min)

1. Abrir `index.html` y actualizar URL de API:

```javascript
// En index.html, busca:
const API_URL = "http://localhost:8000"; // Cambiar a:
const API_URL = "https://api.railway.app"; // Tu URL de Railway
```

2. Ir a https://vercel.com
3. Click **"New Project"** → Seleccionar repositorio
4. Vercel auto-detecta que es un proyecto estático
5. Deploy automático

### Listo! 🎉

Tu app estará en: `https://tu-proyecto.vercel.app`

---

## 🔧 Opción 2: Testing Local (Development)

### Instalación rápida

#### En Windows:
```bash
cd backend
install.bat
```

#### En Mac/Linux:
```bash
cd backend
bash install.sh
```

### Ejecutar servicios

**Terminal 1 - API:**
```bash
cd backend
venv\Scripts\activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
venv\Scripts\activate
celery -A app.celery_app worker --loglevel=info
```

**Terminal 3 - Celery Beat:**
```bash
cd backend
venv\Scripts\activate
celery -A app.celery_app beat --loglevel=info
```

### Documentación API:
http://localhost:8000/docs

---

## 🛠️ Configuración necesaria

### 1. Gmail SMTP (5 min)

Para que funcionen los correos de recordatorio:

1. Ir a https://myaccount.google.com/security
2. Activar **"Two-Step Verification"**
3. Ir a "App passwords"
4. Seleccionar "Correo" + "Windows/Linux"
5. Copiar la contraseña de 16 caracteres
6. En Railway, agregar como `SMTP_PASSWORD`

### 2. Variables de entorno completas

```env
# Base de datos (Supabase)
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres

# Redis (Railway crea uno automático)
REDIS_URL=redis://default:pass@redis.railway.internal:6379

# Email (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
SENDER_EMAIL=tu_email@gmail.com

# Frontend
FRONTEND_URL=https://tu-proyecto.vercel.app
```

---

## 📊 Verificar que funciona

### Health check:
```bash
curl https://api.railway.app/health
```

Debería retornar:
```json
{"status": "healthy", "service": "PlanificaMe API"}
```

### Crear un evento:
```bash
curl -X POST https://api.railway.app/api/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mi primer evento",
    "type": "personal",
    "date": "2026-03-15",
    "time": "14:00",
    "duration": 60,
    "reminder": 15,
    "creator_id": "user-123",
    "email": "tu_email@gmail.com"
  }'
```

---

## 📁 Estructura actual

```
PlanificaMe/
├── index.html                 # Frontend (HTML/CSS/JS)
└── backend/
    ├── main.py              # API FastAPI
    ├── requirements.txt
    ├── Dockerfile
    ├── docker-compose.yml
    ├── railway.toml
    ├── .env.example
    ├── app/
    │   ├── database.py      # Modelos de BD
    │   ├── config.py        # Configuración
    │   ├── celery_app.py    # Tareas asincrónicas
    │   ├── tasks.py         # Recordatorios
    │   ├── models/          # Modelos ORM
    │   ├── routes/          # Endpoints API
    │   ├── services/        # Lógica de negocio
    │   └── utils/           # Utilidades
    ├── README.md            # Documentación
    ├── DEPLOY.md            # Guía de despliegue
    └── QUICKSTART.md        # Este archivo
```

---

## 💰 Costos totales

| Servicio | Costo |
|----------|-------|
| Supabase | $0 (Gratis hasta 500MB) |
| Railway  | $5/mes |
| Vercel   | $0 (Plan gratuito) |
| Gmail    | $0 (500 correos/día) |
| **TOTAL**| **$5/mes** |

Escala a $50-100/mes si el proyecto crece significativamente.

---

## 🔐 Seguridad

- ✓ HTTPS en todos lados (Vercel + Railway)
- ✓ Variables de entorno protegidas
- ✓ CORS configurado correctamente
- ✓ Base de datos con roles y permisos
- ✓ Contraseñas hasheadas

---

## 🆘 Problemas comunes

### "Error al conectar a base de datos"
Verificar `DATABASE_URL` en Railway → Logs

### "No llegan los correos"
1. Verificar SMTP en Railway
2. Revisar logs de Celery Worker
3. Usar contraseña de app, no PIN

### "CORS error"
Verificar `FRONTEND_URL` es correcto en Railway

### "API no responde"
Hacer health check: `https://api.railway.app/health`

---

## 📚 Documentación completa

- [README.md](./backend/README.md) - Documentación técnica
- [DEPLOY.md](./backend/DEPLOY.md) - Guía paso a paso
- [Swagger UI](http://localhost:8000/docs) - API interactiva

---

## 🎯 Próximos pasos

1. ✓ Desplegar a producción (Railway + Vercel)
2. ✓ Configurar SMTP (Gmail)
3. Agregar autenticación (JWT)
4. Agregar notificaciones en tiempo real (WebSocket)
5. Mejorar UI del frontend
6. Agregar móvil (React Native)
7. Monetizar (planes premium)

---

## 👥 Equipo

Creado por: [Tu nombre]  
Contacto: [Tu email]

---

**¡Disfruta usando PlanificaMe! 🎉**

Para dudas o bugs: https://github.com/tu_usuario/planificame/issues
