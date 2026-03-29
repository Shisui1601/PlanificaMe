# 🚀 Guía Completa de Despliegue - PlanificaMe

Guía paso a paso para desplegar PlanificaMe en producción con **Supabase + Railway + Vercel**.

---

## 📋 Tabla de Contenidos

1. [Preparación Previa](#preparación-previa)
2. [Configurar Supabase (Base de Datos)](#1-configurar-supabase)
3. [Configurar Railway (Backend)](#2-configurar-railway)
4. [Configurar Gmail SMTP](#3-configurar-gmail-smtp)
5. [Desplegar Frontend en Vercel](#4-desplegar-frontend)
6. [Testing y Verificación](#testing)
7. [Monitoreo](#monitoreo)

---

## Preparación Previa

### Cosas que necesitas:

1. **Cuenta en Supabase** - https://app.supabase.com (gratis)
2. **Cuenta en Railway** - https://railway.app (gratis, $5/mes mínimo)
3. **Cuenta en Vercel** - https://vercel.com (gratis)
4. **Cuenta Gmail** - Para SMTP (gratis)
5. **Repositorio GitHub** - Para conectar con Railway y Vercel
6. **Git instalado** en tu PC - https://git-scm.com

### Costos Finales:
- **Supabase**: $0 (plan gratuito) = $0/mes
- **Railway**: Mínimo $5/mes (incluye API + Redis)
- **Vercel**: $0 (plan gratuito)
- **Gmail**: $0 (gratis)
- **TOTAL: $5/mes** (renovable, escalable)

---

# 1. Configurar Supabase (PostgreSQL)

## Paso 1.1: Crear Proyecto

1. Ir a https://app.supabase.com
2. Click **"New Project"**
3. Llenar formulario:
   - **Name**: `planificame` (o tu preferencia)
   - **Database Password**: Crear contraseña fuerte
   - **Region**: Seleccionar región más cercana (ej: us-east-1)
4. Click **"Create new project"**
5. Esperar 5-10 minutos a que se cree

## Paso 1.2: Obtener Database URL

1. En el dashboard de Supabase, ir a **Settings** → **Database**
2. En la sección "Connection string", seleccionar **"PostgreSQL"**
3. Copiar la URL (formato: `postgresql://[user]:[password]@[host]:[port]/[database]`)
4. **Anotar esta URL** - La usaremos en Railroad

### URL de ejemplo:
```
postgresql://postgres:tu_contraseña@db.abcdefg.supabase.co:5432/postgres
```

## Paso 1.3: Desactivar el "Realtime" (Opcional, para ahorrar)

1. En Supabase, ir a **Replication** → Deshabilitar Realtime si no lo necesitas
2. Esto reduce costos de banda ancha

---

# 2. Configurar Railway (Backend + Redis)

## Paso 2.1: Crear Cuenta y Proyecto

1. Ir a https://railway.app
2. Click **"Start New Project"**
3. Conectar con GitHub si te lo pide

## Paso 2.2: Agregar Redis

1. En dashboard de Railway, click **"+ New"**
2. Seleccionar **"Redis"**
3. Railway automáticamente lo configura
4. Click en el servicio Redis y anotar:
   - **REDIS_URL** en la pestaña "Variables"

### Ejemplo de REDIS_URL:
```
redis://default:password@redis.railway.internal:6379
```

## Paso 2.3: Agregar PostgreSQL (Opcional - Si no usas Supabase)

Si prefieres usar PostgreSQL en Railway en lugar de Supabase:

1. Click **"+ New"**
2. Seleccionar **"PostgreSQL"**
3. Anotar la DATABASE_URL

## Paso 2.4: Desplegar FastAPI

### Opción A: Desde GitHub (Recomendado)

1. Subir tu código a GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/tu_usuario/planificame.git
   git push -u origin main
   ```

2. En Railway, click **"+ New"**
3. Seleccionar **"GitHub Repo"**
4. Autorizar GitHub y seleccionar tu repositorio

### Opción B: Desde Container Registry

1. Construir imagen Docker:
   ```bash
   docker build -t planificame-api .
   ```

2. Subir a Docker Hub o GitHub Container Registry
3. En Railway, usar "Dockerfile" como base

## Paso 2.5: Configurar Variables de Entorno

En Railway, ir a tu servicio y en la pestaña **"Variables"**:

```
DATABASE_URL=postgresql://[user]:[password]@db.abcdefg.supabase.co:5432/postgres
REDIS_URL=redis://default:password@redis.railway.internal:6379
CELERY_BROKER_URL=redis://default:password@redis.railway.internal:6379
CELERY_RESULT_BACKEND=redis://default:password@redis.railway.internal:6379
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_contraseña_app
SENDER_EMAIL=tu_email@gmail.com
SENDER_NAME=PlanificaMe
FRONTEND_URL=https://tu-proyecto.vercel.app
DEBUG=False
```

## Paso 2.6: Deploy

1. Railway automáticamente detecta el `Dockerfile` y `railway.toml`
2. Hacer push a GitHub triggerea un deployment
3. Esperar a que termine (3-10 minutos)
4. Anotar la **URL pública** (ej: `https://tu-proyecto-api.railway.app`)

### Verificar que funciona:
```
https://tu-proyecto-api.railway.app/health
```

Debería retornar:
```json
{"status": "healthy", "service": "PlanificaMe API"}
```

---

# 3. Configurar Gmail SMTP

## Paso 3.1: Activar 2FA en Google

1. Ir a https://myaccount.google.com/security
2. Buscar **"Two-Step Verification"**
3. Click y activar (agregar teléfono si no lo has hecho)

## Paso 3.2: Generar Contraseña de Aplicación

1. Una vez activado 2FA, volver a https://myaccount.google.com/security
2. Buscar **"App passwords"** (solo aparece si 2FA está activado)
3. Seleccionar:
   - **App**: "Correo"
   - **Device**: "Windows/Linux"
4. Click **"Generate"**
5. Copiar la contraseña de 16 caracteres
6. Esta será tu `SMTP_PASSWORD`

### Ejemplo:
```
Original: user@gmail.com
App Password: abcd efgh ijkl mnop
(16 caracteres)
```

---

# 4. Desplegar Frontend en Vercel

## Paso 4.1: Preparar Frontend

Crear un proyecto React o Vite y agregar la carpeta `frontend/` al repositorio:

```
frontend/
├── src/
│   ├── App.jsx
│   ├── main.jsx
│   └── ...
├── index.html
├── package.json
├── vite.config.js
└── .env.example
```

### Variables de entorno del frontend (.env):
```
VITE_API_URL=https://tu-proyecto-api.railway.app
VITE_APP_NAME=PlanificaMe
```

## Paso 4.2: Conectar con Vercel

1. Ir a https://vercel.com
2. Click **"New Project"**
3. Seleccionar tu repositorio de GitHub
4. Vercel auto-detecta que es un proyecto Vite
5. En **"Build Settings"**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
6. Agregar **Environment Variables**:
   ```
   VITE_API_URL=https://tu-proyecto-api.railway.app
   ```
7. Click **"Deploy"**
8. Esperar a que termine (2-5 minutos)
9. Anotar la URL (ej: `https://tu-proyecto.vercel.app`)

## Paso 4.3: Actualizar CORS en Backend

1. En Railway, ir a variables y actualizar:
   ```
   FRONTEND_URL=https://tu-proyecto.vercel.app
   ```

2. Hacer push a GitHub para re-desplegar

---

# Testing

## Verificar que todo funciona

### 1. Health Check API
```bash
curl https://tu-proyecto-api.railway.app/health
```

Debería retornar:
```json
{"status": "healthy", "service": "PlanificaMe API"}
```

### 2. Crear Usuario Test
```bash
curl -X POST https://tu-proyecto-api.railway.app/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-user",
    "name": "Test User",
    "email": "test@example.com",
    "role": "user"
  }'
```

### 3. Crear Evento Test
```bash
curl -X POST https://tu-proyecto-api.railway.app/api/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Event",
    "type": "personal",
    "date": "2026-03-15",
    "time": "14:00",
    "duration": 60,
    "reminder": 15,
    "creator_id": "test-user",
    "email": "tu_email@gmail.com"
  }'
```

### 4. Ver documentación interactiva
```
https://tu-proyecto-api.railway.app/docs
```

---

# Monitoreo

## Logs en Railway

1. En Railway, selecciona el servicio
2. Pestaña **"Logs"**
3. Ver logs en tiempo real

No debería haber errores como:
- `Connection refused`
- `Authentication failed`
- `SMTP error`

## Monitoreo de Supabase

1. En Supabase, ir a **"Database"** → **"Monitoring"**
2. Ver uso de conexiones, queries, etc.

## Monitoreo de Vercel

1. En Vercel, ir a **"Analytics"**
2. Ver tráfico, performance, etc.

---

# Preguntas Frecuentes

## ¿Cuánto cuesta en total?

| Servicio | Precio |
|----------|--------|
| Supabase | Gratis (hasta 500MB datos) |
| Railway | $5/mes mínimo (puedes agregar más) |
| Vercel | Gratis |
| Gmail | Gratis (500 correos/día) |
| **TOTAL** | **$5/mes** |

## ¿Y si crece mi proyecto?

- **Supabase**: Crece de $25/mes (Pro)
- **Railway**: Pagas por uso ($5+ varios servicios)
- **Vercel**: $20/mes (Pro)
- **Total escalado**: $50-100/mes

Sigue siendo muy barato comparado con un servidor dedicado.

## ¿Cómo agrego más usuarios?

En Railway:
```
DATABASE_URL = postgresql://...
```

Todos los usuarios comparten la misma base de datos.

## ¿Cómo reseteo la base de datos?

En Supabase:
1. Settings → Database → Reset
2. ⚠️ Borra todos los datos

## ¿Cómo backup de base de datos?

Supabase automáticamente hace backup diario.
También puedes:
```bash
pg_dump "postgresql://..." > backup.sql
```

---

# Troubleshooting

## Error: "Connection refused"

**Solución**: Verificar que `DATABASE_URL` está correcta en Railway

## Error: "SMTP authentication failed"

**Solución**: 
1. Verificar que 2FA está activado en Google
2. Usar contraseña de aplicación (16 caracteres), no PIN
3. Verificar que `SMTP_USER` es el email correcto

## Error: "CORS error"

**Solución**: Verificar que `FRONTEND_URL` está correcto en Railway

## Los recordatorios no llegan

**Solución**:
1. Verificar `CELERY_BROKER_URL` en Railway
2. Ver logs del worker en Railway
3. Verificar email en el evento

## Base de datos dice "read-only"

**Solución**: Supabase está en modo de mantenimiento
- Esperar 5 minutos
- O cambiar a replica de lectura

---

# Próximos Pasos

1. ✓ Supabase configurado
2. ✓ Railway configurado
3. ✓ Vercel configurado
4. ✓ SMTP configurado

Ahora:

- [ ] Subir componentes del frontend a GitHub
- [ ] Conectar Vercel
- [ ] Hacer testing
- [ ] Invitar usuarios
- [ ] Empezar a usar PlanificaMe

---

# Soporte

Si tienes problemas:

1. Revisar logs en Railway: **Logs** tab
2. Revisar logs de Supabase: **Database** → **Monitoring**
3. Revisar console de Vercel
4. Leer documentación de cada servicio

---

**¡Listo para producción! 🚀**
