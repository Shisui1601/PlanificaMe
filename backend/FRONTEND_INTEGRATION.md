# 🔗 Guía de Integración Frontend - Backend

Este archivo contiene instrucciones para conectar el `index.html` frontend con la API de FastAPI.

---

## Cambios Necesarios en index.html

Actualmente, el frontend almacena datos en `localStorage`. Para conectar con el backend, necesitas:

### 1. Actualizar la URL base de la API

Al inicio de la sección `<script>` en index.html, agregar:

```javascript
// ═════════════════════════════════════════════════════════════
// CONFIGURACIÓN DE API
// ═════════════════════════════════════════════════════════════

// Cambiar según tu entorno
const API_URL = process.env.VITE_API_URL || "http://localhost:8000";

// En producción (Vercel)
// const API_URL = "https://api.railway.app";
```

### 2. Crear funciones HTTP auxiliares

Agregar estas funciones antes de las funciones principales:

```javascript
// ═════════════════════════════════════════════════════════════
// HTTP HELPERS
// ═════════════════════════════════════════════════════════════

async function apiCall(endpoint, method = "GET", data = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${API_URL}${endpoint}`, options);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error("API Call Error:", error);
    throw error;
  }
}

// GET request
async function apiGet(endpoint) {
  return apiCall(endpoint, "GET");
}

// POST request
async function apiPost(endpoint, data) {
  return apiCall(endpoint, "POST", data);
}

// PATCH request
async function apiPatch(endpoint, data) {
  return apiCall(endpoint, "PATCH", data);
}

// DELETE request
async function apiDelete(endpoint) {
  return apiCall(endpoint, "DELETE");
}
```

---

## Cambios en Funciones Principales

### saveTask() - Modificar para guardar en API

```javascript
function saveTask(){
  const title = document.getElementById('tTitle').value.trim();
  if(!title){toast('⚠️ El título es requerido');return;}
  
  const type = document.getElementById('tType').value;
  const date = document.getElementById('tDate').value;
  const time = document.getElementById('tTime').value;
  const dur = parseInt(document.getElementById('tDur').value);
  const remind = parseInt(document.getElementById('tRemind').value);
  const desc = document.getElementById('tDesc').value;
  const email = document.getElementById('tEmail').value;
  const projId = type==='project' ? '' : document.getElementById('tProj').value;
  const color = document.getElementById('tColor').value;
  const deadlineDate = document.getElementById('tDeadlineDate').value;
  const deadlineTime = document.getElementById('tDeadlineTime').value || '17:00';

  const eventData = {
    title,
    type,
    date,
    time,
    duration: dur,
    reminder: remind,
    description: desc,
    email,
    project_id: projId || null,
    color,
    deadline_date: deadlineDate || null,
    deadline_time: deadlineTime,
    creator_id: ME.id
  };

  if(S.editId){
    // ACTUALIZAR evento existente
    apiPatch(`/api/events/${S.editId}`, eventData)
      .then(updated => {
        // Actualizar en S.events
        const i = S.events.findIndex(e => e.id === S.editId);
        if(i !== -1) S.events[i] = updated;
        toast('✓ Evento actualizado');
        closeModal('taskModal');
        render();
      })
      .catch(error => {
        toast(`❌ Error: ${error.message}`);
      });
  } else {
    // CREAR nuevo evento
    apiPost('/api/events/', eventData)
      .then(created => {
        S.events.push(created);
        toast('✓ Evento creado');
        closeModal('taskModal');
        render();
      })
      .catch(error => {
        toast(`❌ Error: ${error.message}`);
      });
  }
}
```

### deleteTask() - Modificar para eliminar en API

```javascript
function deleteTask(){
  if(!S.editId) return;
  
  apiDelete(`/api/events/${S.editId}`)
    .then(() => {
      S.events = S.events.filter(e => e.id !== S.editId);
      closeModal('taskModal');
      render();
      toast('🗑 Evento eliminado');
    })
    .catch(error => {
      toast(`❌ Error: ${error.message}`);
    });
}
```

### applyStatus() - Modificar para actualizar estado

```javascript
function applyStatus(){
  const status = document.getElementById('statusValue').value;
  if(!status){toast('⚠️ Selecciona un estado');return;}
  
  const note = document.getElementById('statusNote').value;
  const actualDate = document.getElementById('actualDate').value;
  const actualTime = document.getElementById('actualTime').value;
  const extDate = document.getElementById('extDate').value;
  const extTime = document.getElementById('extTime').value;

  const statusData = {
    status,
    status_note: note || null,
    actual_date: actualDate || null,
    actual_time: actualTime || null,
    deadline_date: status === 'extended' ? extDate : null,
    deadline_time: status === 'extended' ? extTime : null
  };

  apiPatch(`/api/events/${_statusEvId}/status`, statusData)
    .then(updated => {
      const i = S.events.findIndex(e => e.id === _statusEvId);
      if(i !== -1) S.events[i] = updated;
      
      const statusMsg = {
        completed: '✅ Actividad completada',
        'early-voluntary': '⚡ Marcada como adelantada',
        'early-forced': '🔀 Adelantada por obligación',
        extended: '📅 Fecha límite extendida',
        abandoned: '🚫 Actividad abandonada',
        pending: '🕐 Restablecida a pendiente'
      };
      
      closeModal('statusModal');
      render();
      toast(statusMsg[status] || 'Estado actualizado');
    })
    .catch(error => {
      toast(`❌ Error: ${error.message}`);
    });
}
```

### Cargar eventos al iniciarse

```javascript
function init(){
  renderTeam();
  
  // Cargar eventos de la API
  apiGet('/api/events/')
    .then(response => {
      S.events = response.events || [];
      render();
      setTimeout(() => notify('👋 Bienvenido a WorkAgenda', 'Haz clic en cualquier hora para crear un evento'), 2000);
      const hol = getHoliday(dk(new Date()));
      if(hol) setTimeout(() => notify('🇩🇴 Día Festivo', hol), 3500);
    })
    .catch(error => {
      console.error("Error cargando eventos:", error);
      toast("⚠️ No se pudieron cargar los eventos. Usando datos locales.");
      render();
    });
}
```

---

## Obtener Feriados desde API

```javascript
function getHoliday(dateStr) {
  // Versión mejorada que consulta la API
  return apiGet(`/api/holidays/${dateStr}`)
    .then(holiday => holiday.name)
    .catch(() => null);
}

// Versión síncrona (para inicialización)
async function checkHolidayAsync(dateStr) {
  try {
    const response = await apiGet(`/api/holidays/${dateStr}`);
    return response.name;
  } catch {
    return null;
  }
}
```

---

## Autenticación (Opcional)

Si implementas autenticación JWT:

```javascript
// Guardar token después de login
function saveToken(token) {
  localStorage.setItem('token', token);
}

// Obtener token para requests
function getToken() {
  return localStorage.getItem('token');
}

// Actualizar apiCall para incluir token
async function apiCall(endpoint, method = "GET", data = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  const token = getToken();
  if(token) {
    options.headers.Authorization = `Bearer ${token}`;
  }

  if(data) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${API_URL}${endpoint}`, options);
    
    if(response.status === 401) {
      // Token expirado
      localStorage.removeItem('token');
      window.location.href = '/login';
      return;
    }
    
    if(!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return await response.json();
  } catch(error) {
    console.error("API Call Error:", error);
    throw error;
  }
}
```

---

## Variables de Entorno (Vite)

Si conviertes a Vite, crea `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=PlanificaMe
VITE_DEBUG=true
```

En producción `.env.production`:

```env
VITE_API_URL=https://api.railway.app
VITE_APP_NAME=PlanificaMe
VITE_DEBUG=false
```

---

## Campos de Mapeo

### Frontend → API

| Frontend | API | Tipo |
|----------|-----|------|
| ev.title | title | string |
| ev.type | type | string |
| ev.date | date | YYYY-MM-DD |
| ev.time | time | HH:MM |
| ev.dur | duration | number (min) |
| ev.remind | reminder | number (min) |
| ev.desc | description | string |
| ev.email | email | string |
| ev.projId | project_id | UUID |
| ev.color | color | #hex |
| ev.status | status | string |
| ev.statusNote | status_note | string |
| ev.actualDate | actual_date | YYYY-MM-DD |
| ev.actualTime | actual_time | HH:MM |
| ev.creatorId | creator_id | UUID |
| ev.isDeadline | is_deadline | boolean |

---

## Testing

### Test de conexión

```javascript
// En consola del navegador
fetch("http://localhost:8000/health")
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error(e));
```

Debería retornar:
```json
{"status": "healthy", "service": "PlanificaMe API"}
```

### Test de eventos

```javascript
// Crear
fetch("http://localhost:8000/api/events/", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    title: "Test",
    type: "personal",
    date: "2026-03-15",
    time: "14:00",
    duration: 60,
    reminder: 15,
    creator_id: "user-1",
    email: "test@example.com"
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

---

## Repositorio GitHub

Estructura recomendada:

```
planificame/
├── frontend/
│   ├── index.html          (modificado con API)
│   ├── vite.config.js
│   ├── .env.example
│   └── package.json
│
└── backend/
    ├── main.py
    ├── requirements.txt
    └── ... (resto de archivos)
```

---

## Despliegue en Vercel

1. Crear `Frontend` carpeta como raíz
2. Configurar build en Vercel:
   ```
   Build Command: npm run build
   Output Directory: dist
   ```
3. Agregar env var: `VITE_API_URL=https://api.railway.app`

---

## Errores Comunes

### CORS Error
**Causa**: `FRONTEND_URL` no está en CORS_ORIGINS de backend

**Solución**: Actualizar en Railway:
```
FRONTEND_URL=https://tu-dominio.vercel.app
```

### 404 Not Found
**Causa**: API_URL incorrecto

**Solución**: Verificar URL en console:
```javascript
console.log(API_URL);
```

### Network Error
**Causa**: Servidor backend no está corriendo

**Solución**: Ver logs en Railway o ejecutar localmente

---

**Listo para conectar frontend con backend! 🎉**
