import pytest
from pydantic import ValidationError
from common.constants import DeviceType, NodeStatus
from common.models import (
    CommandRequest, 
    CommandIntent, 
    ExecuteRequest, 
    ExecuteResponse, 
    NodeRegisterRequest
)

# * Pruebas unitarias para validación de modelos Pydantic

def test_command_intent_valid():
    # * Comprobar que una intención válida de Ollama se deserializa correctamente
    data = {
        "intent": "play_music",
        "target_device": "windows",
        "action": "spotify_play",
        "parameters": {"query": "Daft Punk", "platform": "spotify"},
        "speech_response": "Reproduciendo música en Windows"
    }
    intent = CommandIntent(**data)
    assert intent.target_device == DeviceType.WINDOWS
    assert intent.action == "spotify_play"
    assert intent.parameters["query"] == "Daft Punk"
    assert intent.speech_response == "Reproduciendo música en Windows"

def test_command_intent_invalid_device():
    # ! Validar que un dispositivo inexistente lance ValidationError
    data = {
        "intent": "play_music",
        "target_device": "smart_fridge",
        "action": "spotify_play"
    }
    with pytest.raises(ValidationError):
        CommandIntent(**data)

def test_execute_request_and_response():
    # * Validar payloads de ejecución
    req = ExecuteRequest(action="volume", parameters={"level": 80})
    assert req.action == "volume"
    assert req.parameters["level"] == 80

    res = ExecuteResponse(success=True, message="Volumen ajustado")
    assert res.success is True

def test_node_register_request():
    # * Validar registro de nodos
    reg = NodeRegisterRequest(
        device=DeviceType.CACHYOS,
        base_url="http://192.168.1.50:5001",
        skills=["linux_scripts", "media_control"]
    )
    assert reg.device == DeviceType.CACHYOS
    assert len(reg.skills) == 2
