import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from pydantic import ValidationError

from common.constants import DeviceType
from common.models import ExecuteRequest, ExecuteResponse, HealthResponse
from common.security import require_internal_token

# * Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# * Importar pyautogui con fallback seguro si no está instalado
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[!] PyAutoGUI no está instalado en este entorno de Windows.")

@app.route("/api/health", methods=["GET"])
@require_internal_token
def health_check():
    # * Comprobación de salud desde la Mac
    return jsonify(HealthResponse(device=DeviceType.WINDOWS, version="1.0.0").model_dump()), 200

@app.route("/api/execute", methods=["POST"])
@require_internal_token
def execute_action():
    # * Ejecuta la acción en Windows (multimedia, atajos, etc.)
    try:
        req = ExecuteRequest(**request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": "Payload inválido", "details": e.errors()}), 400

    action = req.action
    params = req.parameters
    print(f"[*] Solicitud recibida en Windows: acción '{action}', params: {params}")

    if not PYAUTOGUI_AVAILABLE:
        return jsonify(ExecuteResponse(
            success=False, 
            message="PyAutoGUI no está disponible en este cliente."
        ).model_dump()), 500

    try:
        if action == "spotify_play" or action == "media_play_pause":
            # * Tecla multimedia global de Play/Pause en Windows
            pyautogui.press("playpause")
            return jsonify(ExecuteResponse(success=True, message="Comando multimedia enviado a Windows.").model_dump()), 200

        elif action == "media_next":
            pyautogui.press("nexttrack")
            return jsonify(ExecuteResponse(success=True, message="Pista siguiente enviada a Windows.").model_dump()), 200

        elif action == "media_prev":
            pyautogui.press("prevtrack")
            return jsonify(ExecuteResponse(success=True, message="Pista anterior enviada a Windows.").model_dump()), 200

        elif action == "system_key":
            key = params.get("key")
            if not key:
                return jsonify(ExecuteResponse(success=False, message="Parámetro 'key' requerido.").model_dump()), 400
            pyautogui.press(key)
            return jsonify(ExecuteResponse(success=True, message=f"Tecla '{key}' presionada.").model_dump()), 200

        else:
            return jsonify(ExecuteResponse(
                success=False, 
                message=f"Acción no soportada en Windows: {action}"
            ).model_dump()), 400

    except Exception as e:
        print(f"[!] Error ejecutando acción en Windows: {e}")
        return jsonify(ExecuteResponse(success=False, message=f"Error en Windows: {str(e)}").model_dump()), 500

if __name__ == "__main__":
    port = int(os.getenv("WINDOWS_PORT", 5002))
    print(f"[*] Iniciando Cliente Windows en http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
