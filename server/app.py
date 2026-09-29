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

def process_command_internal(text: str, source: str = "voice"):
    # * Lógica centralizada para procesar cualquier comando (sea por HTTP, voz o CLI)
    print(f"[*] Procesando comando ({source}): '{text}'")

    # * 1. Consultar a Ollama en CachyOS para clasificar intención
    intent = llm_client.infer_intent(text)
    if not intent:
        error_msg = "No logré entender la instrucción o el servidor de lenguaje no respondió."
        tts.speak(error_msg)
        return False, {"success": False, "message": error_msg}, 502

    # * 2. Despachar acción al nodo correspondiente
    result = dispatcher.dispatch(intent)

    # * 3. Retroalimentación auditiva final
    if result.success:
        tts.speak(intent.speech_response or result.message or "Acción realizada con éxito.")
    else:
        tts.speak(f"Hubo un problema: {result.message}")

    return result.success, {
        "success": result.success,
        "intent": intent.model_dump(),
        "execution_result": result.model_dump()
    }, 200

@app.route("/api/health", methods=["GET"])
@require_internal_token
def health_check():
    # * Endpoint de comprobación de salud del orquestador
    response = HealthResponse(device=DeviceType.MACOS, version="1.0.0")
    return jsonify(response.model_dump()), 200

@app.route("/api/command", methods=["POST"])
@require_internal_token
def handle_command():
    # * Recibe el texto de la orden por HTTP
    try:
        req = CommandRequest(**request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": "Payload inválido", "details": e.errors()}), 400

    _, result_data, status_code = process_command_internal(req.text, source=req.source)
    return jsonify(result_data), status_code

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

def start_voice_listener():
    # * Arranca el listener de micrófono si está habilitado
    if os.getenv("ENABLE_VOICE_LISTENER", "true").lower() in ("true", "1", "yes"):
        try:
            from server.audio.wake_word import WakeWordListener
            listener = WakeWordListener(
                on_command_detected=lambda cmd: process_command_internal(cmd, source="microphone")
            )
            listener.start()
            return listener
        except Exception as e:
            print(f"[!] No se pudo iniciar el listener de micrófono: {e}")
    return None

if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 5000))
    print(f"[*] Iniciando Servidor Orquestador Lili en http://{host}:{port}")
    
    # Iniciar escucha de micrófono en segundo plano
    listener = start_voice_listener()
    
    try:
        app.run(host=host, port=port, debug=False)
    finally:
        if listener:
            listener.stop()
