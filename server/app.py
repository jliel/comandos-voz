import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from pydantic import ValidationError

from common.constants import DeviceType
from common.models import CommandRequest, NodeRegisterRequest, HealthResponse
from common.security import require_internal_token
from server.services.registry import NodeRegistry
from server.services.llm_client import OllamaClient
from server.services.dispatcher import CommandDispatcher
from server.audio.tts import AudioFeedback

# * Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# * Inicialización de servicios del orquestador
registry = NodeRegistry()
llm_client = OllamaClient()
dispatcher = CommandDispatcher(registry)
tts = AudioFeedback()

@app.route("/api/health", methods=["GET"])
@require_internal_token
def health_check():
    # * Endpoint de comprobación de salud del orquestador
    response = HealthResponse(device=DeviceType.MACOS, version="1.0.0")
    return jsonify(response.model_dump()), 200

@app.route("/api/command", methods=["POST"])
@require_internal_token
def handle_command():
    # * Recibe el texto de la orden y coordina el flujo completo
    try:
        req = CommandRequest(**request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": "Payload inválido", "details": e.errors()}), 400

    print(f"[*] Comando recibido ({req.source}): '{req.text}'")

    # * 1. Consultar a Ollama en CachyOS para interpretar intención
    intent = llm_client.infer_intent(req.text)
    if not intent:
        error_msg = "No logré entender la instrucción o el servidor de lenguaje no respondió."
        tts.speak(error_msg)
        return jsonify({"success": False, "message": error_msg}), 502

    # * 2. Despachar acción al nodo correspondiente
    result = dispatcher.dispatch(intent)

    # * 3. Retroalimentación auditiva final
    if intent.speech_response and result.success:
        tts.speak(intent.speech_response)
    elif not result.success:
        tts.speak(f"Hubo un problema: {result.message}")

    return jsonify({
        "success": result.success,
        "intent": intent.model_dump(),
        "execution_result": result.model_dump()
    }), 200

@app.route("/api/nodes/register", methods=["POST"])
@require_internal_token
def register_node():
    # * Registro dinámico de clientes remotos (CachyOS o Windows)
    try:
        req = NodeRegisterRequest(**request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": "Datos de registro inválidos", "details": e.errors()}), 400

    node_info = registry.register_node(req)
    return jsonify({"message": "Nodo registrado con éxito", "node": node_info.model_dump()}), 200

@app.route("/api/nodes/status", methods=["GET"])
@require_internal_token
def nodes_status():
    # * Retorna el estado en tiempo real de todos los nodos en la LAN
    nodes = registry.list_nodes()
    # * Validar salud en vivo
    status_list = []
    for node in nodes:
        live_status = registry.check_node_health(node.device)
        status_list.append({
            "device": node.device.value,
            "base_url": node.base_url,
            "skills": node.skills,
            "status": live_status.value
        })

    return jsonify({
        "orchestrator": "online",
        "nodes": status_list
    }), 200

if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 5000))
    print(f"[*] Iniciando Servidor Orquestador Lili en http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
