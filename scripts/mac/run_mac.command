#!/bin/bash
# ==============================================================================
# run_mac.command - Lanzador Interactivo del Servidor Lili en macOS
# Puedes ejecutarlo dando doble clic directamente desde Finder.
# ==============================================================================

DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$DIR"

echo "======================================================="
echo "  🎙️ Arrancando Asistente Virtual Lili (MacBook Air)"
echo "  Directorio: $DIR"
echo "======================================================="

# * Validar entorno virtual
if [ ! -d "venv" ]; then
    echo "[!] No se encontró el entorno 'venv'."
    echo "[!] Por favor ejecuta primero: setup_mac.command"
    read -p "Presiona Enter para salir..."
    exit 1
fi

source venv/bin/activate
export PYTHONPATH="$DIR"

echo "[+] Entorno virtual activado."
echo "[*] Iniciando servidor orquestador..."

python3 server/app.py

read -p "El servidor se ha detenido. Presiona Enter para salir..."
