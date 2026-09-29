from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from common.constants import DeviceType, NodeStatus

# * Modelos de datos y esquemas Pydantic compartidos

class CommandRequest(BaseModel):
    # * Entrada recibida tras la transcripción de audio o prueba manual
    text: str = Field(..., description="Texto del comando hablado o escrito por el usuario")
    source: str = Field(default="voice", description="Origen de la orden (voice, cli, web)")

class CommandIntent(BaseModel):
    # * Esquema estricto esperado de la inferencia de Ollama
    intent: str = Field(..., description="Nombre canónico de la intención (ej. play_music, check_weather)")
    target_device: DeviceType = Field(..., description="Nodo destino de la ejecución (macos, cachyos, windows)")
    action: str = Field(..., description="Identificador de la skill o acción a detonar")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros extraídos para la acción")
    speech_response: Optional[str] = Field(
        default=None, 
        description="Respuesta hablada corta para sintetizar por TTS"
    )

class ExecuteRequest(BaseModel):
    # * Payload enviado a los clientes ejecutores en POST /api/execute
    action: str = Field(..., description="Identificador de la acción a ejecutar")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros de la acción")

class ExecuteResponse(BaseModel):
    # * Respuesta del cliente ejecutor tras detonar la acción
    success: bool = Field(..., description="Indica si la acción se ejecutó exitosamente")
    message: str = Field(default="", description="Detalle del resultado o mensaje de error")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Datos adicionales retornados")

class NodeRegisterRequest(BaseModel):
    # * Registro que envía un nodo cliente al orquestador en la Mac
    device: DeviceType = Field(..., description="Tipo de dispositivo")
    base_url: str = Field(..., description="URL base alcanzable en la LAN (ej. http://192.168.1.50:5001)")
    skills: List[str] = Field(default_factory=list, description="Lista de habilidades soportadas por el nodo")

class NodeInfo(BaseModel):
    # * Representación en memoria de un nodo dentro del registro
    device: DeviceType
    base_url: str
    skills: List[str] = Field(default_factory=list)
    status: NodeStatus = NodeStatus.UNKNOWN
    last_seen: float = 0.0

class HealthResponse(BaseModel):
    # * Respuesta estándar del endpoint /api/health
    status: str = "ok"
    device: DeviceType
    version: str = "1.0.0"
