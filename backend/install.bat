@echo off
REM Script de instalación para PlanificaMe Backend en Windows

setlocal enabledelayedexpansion

echo ═════════════════════════════════════════════════════════════
echo.         PlanificaMe - Backend Installation Script
echo ═════════════════════════════════════════════════════════════
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no está instalado o no está en PATH.
    echo    Descárgalo desde: https://www.python.org/downloads/
    echo    ⚠️  Asegúrate de marcar "Add Python to PATH" durante la instalación
    pause
    exit /b 1
)

echo ✓ Python encontrado
python --version
echo.

REM Create virtual environment
if exist venv (
    echo ⚠️  Entorno virtual ya existe
) else (
    echo 📦 Creando entorno virtual...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo ❌ Error al crear entorno virtual
        pause
        exit /b 1
    )
    echo ✓ Entorno virtual creado
)

REM Activate virtual environment
echo 🔧 Activando entorno virtual...
call venv\Scripts\activate.bat

REM Upgrade pip
echo 📦 Actualizando pip...
python -m pip install --upgrade pip setuptools wheel

REM Install requirements
echo 📦 Instalando dependencias...
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo ❌ Error al instalar dependencias
    pause
    exit /b 1
)
echo ✓ Dependencias instaladas
echo.

REM Setup .env file
if not exist ".env" (
    echo 📋 Creando archivo .env...
    copy .env.example .env
    echo ⚠️  Edita .env con tus valores:
    echo    - DATABASE_URL (Supabase^)
    echo    - REDIS_URL
    echo    - SMTP_USER y SMTP_PASSWORD
    echo    - FRONTEND_URL
) else (
    echo ✓ Archivo .env ya existe
)

echo.
echo ═════════════════════════════════════════════════════════════
echo ✓ Instalación completada
echo.
echo Próximos pasos:
echo.
echo 1. Editar configuración:
echo    notepad .env
echo.
echo 2. Opción A - Ejecución local:
echo    venv\Scripts\activate
echo    uvicorn main:app --reload
echo.
echo 3. Opción B - Con Docker Compose:
echo    docker-compose up -d
echo.
echo 4. Documentación API:
echo    http://localhost:8000/docs
echo.
echo ═════════════════════════════════════════════════════════════
pause
