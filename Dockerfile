# ─────────────────────────────────────────────
#  PlanificaMe — Dockerfile (raíz del proyecto)
# ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend (conserva la estructura de paquete: backend/)
COPY backend/ ./backend/

# Copiar frontend (index.html al nivel raíz del WORKDIR)
COPY index.html ./index.html

# Carpeta para archivos subidos
RUN mkdir -p ./uploads

ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

EXPOSE 8000

# Ejecutar desde /app para que los imports relativos de backend.main funcionen
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
