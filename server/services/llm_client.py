import json
import os
import re
import requests
from typing import Optional
from common.constants import LLM_HTTP_TIMEOUT
from common.models import CommandIntent

# * Cliente de comunicación con Ollama alojado en CachyOS

SYSTEM_PROMPT = """Eres el clasificador de intenciones del asistente virtual 'Lili'.
Tu única responsabilidad es interpretar la orden del usuario y devolver EXCLUSIVAMENTE un objeto JSON válido, sin texto adicional, sin introducciones y sin formato markdown.

El esquema JSON requerido es:
{
  "intent": "<nombre_canónico_intención>",
  "target_device": "<macos | cachyos | windows>",
  "action": "<id_accion>",
  "parameters": { ... },
  "speech_response": "<respuesta_hablada_corta_en_español>"
}

Catálogo de dispositivos y acciones:
- macos:
  - action: "weather" (params: {"city": "nombre"})
  - action: "reminder" (params: {"title": "texto", "time": "hh:mm"})
  - action: "volume" (params: {"level": 0-100})
- cachyos:
  - action: "linux_script" (params: {"script_name": "nombre"})
  - action: "media_toggle" (params: {})
- windows:
  - action: "spotify_play" (params: {"query": "canción o artista"})
  - action: "youtube_play" (params: {"query": "video"})
  - action: "system_key" (params: {"key": "nombre_tecla"})

Ejemplos obligatorios:
Usuario: "sube el volumen al 70 por ciento"
{"intent": "volume", "target_device": "macos", "action": "volume", "parameters": {"level": 70}, "speech_response": "Volumen ajustado al 70 por ciento."}

Usuario: "pon música en spotify"
{"intent": "play_music", "target_device": "windows", "action": "spotify_play", "parameters": {"query": ""}, "speech_response": "Reproduciendo música en Windows."}

Usuario: "pausa la música en linux"
{"intent": "media", "target_device": "cachyos", "action": "media_toggle", "parameters": {}, "speech_response": "Música pausada en CachyOS."}
"""

class OllamaClient:
    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    def infer_intent(self, text: str) -> Optional[CommandIntent]:
        # * Envía el texto a Ollama para clasificar la intención
        endpoint = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"Orden del usuario: \"{text}\"",
            "system": SYSTEM_PROMPT,
            "stream": False,
            "format": "json"
        }

        try:
            # ! Timeout explícito para no bloquear el hilo de orquestación
            response = requests.post(
                endpoint, 
                json=payload, 
                timeout=LLM_HTTP_TIMEOUT
            )
            response.raise_for_error()
            data = response.json()
            raw_response = data.get("response", "").strip()

            # * Validar y transformar a modelo Pydantic
            return self._parse_json_intent(raw_response)

        except requests.RequestException as e:
            # ! Advertencia de caída de red o puerto no accesible
            print(f"[!] Error de conexión con Ollama ({endpoint}): {e}")
            return None
        except Exception as e:
            print(f"[!] Error procesando inferencia de Ollama: {e}")
            return None

    def _parse_json_intent(self, raw_text: str) -> Optional[CommandIntent]:
        # * Intenta parsear directamente el JSON
        try:
            parsed = json.loads(raw_text)
            return CommandIntent(**parsed)
        except Exception:
            # ? Fallback: Extraer bloque JSON si el modelo añadió texto auxiliar
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    return CommandIntent(**parsed)
                except Exception as ex:
                    print(f"[!] Falló el parseo secundario del JSON: {ex}")
            print(f"[!] Respuesta de Ollama no coincide con el esquema requerido: {raw_text}")
            return None
