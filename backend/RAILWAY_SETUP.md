# Railway Quick Setup

Este archivo contiene instrucciones rápidas para desplegar en Railway.

## Opción 1: Desplegar desde GitHub (Recomendado)

### 1. Crear un repositorio en GitHub

```bash
git clone https://github.com/tu_usuario/planificame.git
cd planificame/backend
```

### 2. Subir código a GitHub

```bash
git add .
git commit -m "Add backend with FastAPI"
git push origin main
```

### 3. Conectar con Railway

1. Ir a https://railway.app
2. Click "New Project" 
3. Seleccionar "Deploy from GitHub"
4. Seleccionar el repositorio `planificame`
5. Railway detecta el Dockerfile automáticamente

### 4. Agregar variables de entorno en Railway

En variables, agregar:

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
SENDER_EMAIL=tu_email@gmail.com
FRONTEND_URL=https://tu-frontend.vercel.app
DEBUG=False
```

### 5. Deploy

Railway automáticamente hace build y deploy cuando haces push a GitHub.

---

## Opción 2: Railway CLI (Local)

### 1. Instalar Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Conectar con Railway

```bash
railway login
railway init
```

### 3. Configurar variables

```bash
railway variables set DATABASE_URL "postgresql://..."
railway variables set REDIS_URL "redis://..."
# ... agregar más variables
```

### 4. Deploy

```bash
railway up
```

---

## Monitoreo

### Ver logs

```bash
railway logs
```

o en el dashboard de Railway

### Ver status

```bash
railway status
```

---

## Troubleshooting

### Error: "Build failed"

1. Revisar que Dockerfile está en la raíz
2. Revisar `requirements.txt` tiene todas las dependencias
3. Revisar logs en Railway dashboard

### Error: "Port already in use"

Railway automáticamente asigna un puerto. Revisar variables:
- No hardcodear puerto 8000
- Usar `$PORT` en la configuración

### Error: "Cannot connect to database"

1. Verificar `DATABASE_URL` está correcta
2. Verificar que Supabase permite conexiones desde Railway
3. Agregar IP de Railway a whitelist (si aplica)

---

## Costo

- Mínimo: $5/mes
- Incluye: API + Redis
- Puedes agregar más servicios

---

Para más detalles, ver [DEPLOY.md](./DEPLOY.md)
