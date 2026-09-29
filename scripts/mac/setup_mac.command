#!/bin/bash
# ==============================================================================
# setup_mac.command - Instalador Automático para macOS Monterey (MacBook Air)
# Puedes ejecutarlo dando doble clic directamente desde Finder.
# ==============================================================================

set -e

# * Ubicar el directorio raíz del proyecto
DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$DIR"

echo "======================================================="
echo "  🌸 Instalador Automático de Lili para macOS"
echo "  Directorio de trabajo: $DIR"
echo "======================================================="

# * 1. Verificar dependencias nativas del sistema con Homebrew
echo ""
echo "[*] Paso 1: Verificando herramientas de sistema..."
if command -v brew >/dev/null 2>&1; then
    echo "[+] Homebrew detectado."
    if ! brew list ffmpeg >/dev/null 2>&1; then
        echo "[*] Instalando ffmpeg vía Homebrew..."
        brew install ffmpeg
    fi
    if ! brew list portaudio >/dev/null 2>&1; then
        echo "[*] Instalando portaudio vía Homebrew..."
        brew install portaudio
    fi
else
    echo "[!] Advertencia: Homebrew no está instalado."
    echo "[!] Para óptimo rendimiento de audio, se recomienda instalar 'portaudio' y 'ffmpeg'."
fi

# * 2. Comprobar Python 3
echo ""
echo "[*] Paso 2: Verificando Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] Error fatal: python3 no está instalado en esta Mac."
    read -p "Presiona Enter para salir..."
    exit 1
fi
echo "[+] Python detectado: $(python3 --version)"

# * 3. Crear entorno virtual (venv)
echo ""
echo "[*] Paso 3: Configurando entorno virtual aislado (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[+] Entorno virtual creado exitosamente."
else
    echo "[+] Entorno virtual existente detectado."
fi

# * 4. Activar venv e instalar dependencias
echo ""
echo "[*] Paso 4: Instalando dependencias Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt

# * 5. Configurar archivo de variables de entorno (.env)
echo ""
echo "[*] Paso 5: Verificando configuración .env..."
if [ ! -f ".env" ]; then
    echo "[*] Creando archivo .env a partir de .env.example..."
    cp .env.example .env
    
    echo ""
    read -p "Introduce la IP de tu PC con CachyOS (ej. 192.168.1.50) [127.0.0.1]: " CACHY_IP
    CACHY_IP=${CACHY_IP:-127.0.0.1}
    sed -i '' "s|http://192.168.1.50:11434|http://${CACHY_IP}:11434|g" .env
    sed -i '' "s|http://192.168.1.50:5001|http://${CACHY_IP}:5001|g" .env

    read -p "Introduce un Token Secreto para la LAN [lili_secret_token_123]: " SECRET_TOKEN
    SECRET_TOKEN=${SECRET_TOKEN:-lili_secret_token_123}
    sed -i '' "s|cambiar_este_token_secreto_por_uno_seguro|${SECRET_TOKEN}|g" .env
    
    echo "[+] Archivo .env configurado."
else
    echo "[+] Archivo .env ya existe."
fi

# * 6. Opción de registrar servicio launchd para auto-arranque
echo ""
read -p "¿Deseas instalar Lili como servicio en segundo plano al encender la Mac? (s/N): " INSTALL_SERVICE
if [[ "$INSTALL_SERVICE" =~ ^[sS]$ ]]; then
    PLIST_DEST="$HOME/Library/LaunchAgents/com.lili.server.plist"
    sed "s|__PROJECT_DIR__|$DIR|g" scripts/mac/com.lili.server.plist > "$PLIST_DEST"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    launchctl load "$PLIST_DEST"
    echo "[+] Servicio launchd instalado y cargado en $PLIST_DEST."
    echo "[+] Lili arrancará automáticamente al iniciar sesión."
fi

echo ""
echo "======================================================="
echo "  🎉 ¡Instalación de Lili en macOS completada con éxito!"
echo "  Para arrancar el servidor interactivamente ejecuta:"
echo "  ./scripts/mac/run_mac.command"
echo "======================================================="
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
