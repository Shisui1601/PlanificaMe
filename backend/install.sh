#!/bin/bash
# Script de instalación para PlanificaMe Backend en Linux/Mac

set -e

echo "═════════════════════════════════════════════════════════════"
echo "         PlanificaMe - Backend Installation Script"
echo "═════════════════════════════════════════════════════════════"
echo ""

# Check if Python is installed
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 no está instalado."
    echo "   Descárgalo desde: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 3.11 encontrado"

# Create virtual environment
if [ -d "venv" ]; then
    echo "⚠️  Entorno virtual ya existe"
else
    echo "📦 Creando entorno virtual..."
    python3.11 -m venv venv
    echo "✓ Entorno virtual creado"
fi

# Activate virtual environment
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Upgrade pip
echo "📦 Actualizando pip..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo "📦 Instalando dependencias..."
pip install -r requirements.txt
echo "✓ Dependencias instaladas"

# Setup .env file
if [ ! -f ".env" ]; then
    echo "📋 Creando archivo .env..."
    cp .env.example .env
    echo "⚠️  Edita .env con tus valores:"
    echo "   - DATABASE_URL (Supabase)"
    echo "   - REDIS_URL"
    echo "   - SMTP_USER y SMTP_PASSWORD"
    echo "   - FRONTEND_URL"
fi

echo ""
echo "═════════════════════════════════════════════════════════════"
echo "✓ Instalación completada"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Editar configuración:"
echo "   nano .env"
echo ""
echo "2. Opción A - Ejecución local:"
echo "   source venv/bin/activate  (si no está activado)"
echo "   uvicorn main:app --reload"
echo ""
echo "3. Opción B - Con Docker Compose:"
echo "   docker-compose up -d"
echo ""
echo "4. Documentación API:"
echo "   http://localhost:8000/docs"
echo ""
echo "═════════════════════════════════════════════════════════════"
