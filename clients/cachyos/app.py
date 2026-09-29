import os
import subprocess
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from pydantic import ValidationError

from common.constants import DeviceType
from common.models import ExecuteRequest, ExecuteResponse, HealthResponse
from common.security import require_internal_token

# * Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# * Lista blanca de acciones permitidas en CachyOS (Linux)
ALLOWED_ACTIONS = {
    "media_toggle": "playerctl play-pause",
    "media_next": "playerctl next",
    "media_previous": "playerctl previous",
}

@app.route("/api/health", methods=["GET"])
@require_internal_token
def health_check():
    # * Comprobación de salud desde la Mac
    return jsonify(HealthResponse(device=DeviceType.CACHYOS, version="1.0.0").model_dump()), 200

@app.route("/api/execute", methods=["POST"])
@require_internal_token
def execute_action():
    # * Ejecuta la acción solicitada por el orquestador
    try:
        req = ExecuteRequest(**request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": "Payload inválido", "details": e.errors()}), 400

    action = req.action
    params = req.parameters
    print(f"[*] Solicitud recibida en CachyOS: acción '{action}', params: {params}")

    if action in ALLOWED_ACTIONS:
        cmd = ALLOWED_ACTIONS[action]
        try:
            res = subprocess.run(cmd.split(), capture_output=True, text=True, check=True)
            return jsonify(ExecuteResponse(
                success=True, 
                message=f"Comando '{action}' ejecutado correctamente.",
                data={"stdout": res.stdout}
            ).model_dump()), 200
        except subprocess.CalledProcessError as e:
            # ! Error en la ejecución del comando local
            print(f"[!] Error ejecutando '{cmd}': {e.stderr}")
            return jsonify(ExecuteResponse(
                success=False, 
                message=f"Error al ejecutar: {e.stderr}"
            ).model_dump()), 500

    # ? Soporte para scripts de usuario en la carpeta /skills
    elif action == "linux_script":
        script_name = params.get("script_name")
        if not script_name:
            return jsonify(ExecuteResponse(success=False, message="Parámetro 'script_name' requerido.").model_dump()), 400

        script_path = os.path.join(os.path.dirname(__file__), "skills", f"{script_name}.sh")
        if not os.path.exists(script_path):
            return jsonify(ExecuteResponse(success=False, message=f"Script '{script_name}' no existe en lista blanca.").model_dump()), 404

        try:
            res = subprocess.run(["bash", script_path], capture_output=True, text=True, check=True)
            return jsonify(ExecuteResponse(success=True, message=f"Script '{script_name}' finalizado.", data={"stdout": res.stdout}).model_dump()), 200
        except subprocess.CalledProcessError as e:
            return jsonify(ExecuteResponse(success=False, message=f"Fallo en script: {e.stderr}").model_dump()), 500

    else:
        return jsonify(ExecuteResponse(
            success=False, 
            message=f"Acción no reconocida en CachyOS: {action}"
        ).model_dump()), 400

if __name__ == "__main__":
    port = int(os.getenv("CACHYOS_PORT", 5001))
    print(f"[*] Iniciando Cliente CachyOS en http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
