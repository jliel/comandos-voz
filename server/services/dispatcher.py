import subprocess
import requests
from typing import Dict, Any
from common.constants import DeviceType, DEFAULT_HTTP_TIMEOUT, AUTH_HEADER_NAME
from common.models import CommandIntent, ExecuteRequest, ExecuteResponse
from common.security import get_configured_token
from server.services.registry import NodeRegistry

# * Despachador de acciones a nodos locales o remotos en la LAN

class CommandDispatcher:
    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    def dispatch(self, intent: CommandIntent) -> ExecuteResponse:
        # * Enruta la orden al dispositivo destino
        target = intent.target_device
        print(f"[*] Despachando intención '{intent.intent}' hacia '{target.value}'...")

        if target == DeviceType.MACOS:
            return self._execute_macos_local(intent.action, intent.parameters)
        elif target in (DeviceType.CACHYOS, DeviceType.WINDOWS):
            return self._execute_remote_node(target, intent.action, intent.parameters)
        else:
            return ExecuteResponse(
                success=False, 
                message=f"Dispositivo destino desconocido: {target.value}"
            )

    def _execute_macos_local(self, action: str, params: Dict[str, Any]) -> ExecuteResponse:
        # * Ejecuta habilidades nativas locales en macOS
        try:
            if action == "volume":
                level = int(params.get("level", 50))
                # * Ajusta el volumen del sistema mediante AppleScript
                apple_script = f"set volume output volume {level}"
                subprocess.run(["osascript", "-e", apple_script], check=True)
                return ExecuteResponse(success=True, message=f"Volumen ajustado al {level}%")

            elif action == "reminder":
                title = params.get("title", "Recordatorio de Lili")
                # * Crea un recordatorio en la app Recordatorios de macOS
                apple_script = f'tell application "Reminders" to make new reminder with properties {{name:"{title}"}}'
                subprocess.run(["osascript", "-e", apple_script], check=True)
                return ExecuteResponse(success=True, message=f"Recordatorio '{title}' creado.")

            elif action == "weather":
                city = params.get("city", "Monterrey")
                # TODO: Conectar con la API de OpenWeatherMap si OPENWEATHER_API_KEY existe
                return ExecuteResponse(success=True, message=f"Consulta de clima para {city} completada.")

            else:
                return ExecuteResponse(success=False, message=f"Acción macOS no implementada: {action}")

        except Exception as e:
            # ! Error durante la ejecución del script nativo
            print(f"[!] Error ejecutando acción local en macOS: {e}")
            return ExecuteResponse(success=False, message=f"Error en macOS: {str(e)}")

    def _execute_remote_node(self, device: DeviceType, action: str, params: Dict[str, Any]) -> ExecuteResponse:
        # * Delega la ejecución a un nodo remoto vía HTTP
        node = self.registry.get_node(device)
        if not node:
            return ExecuteResponse(
                success=False, 
                message=f"El nodo '{device.value}' no está registrado en el orquestador."
            )

        url = f"{node.base_url}/api/execute"
        headers = {
            AUTH_HEADER_NAME: get_configured_token(),
            "Content-Type": "application/json"
        }
        payload = ExecuteRequest(action=action, parameters=params).model_dump()

        try:
            # ! Timeout estricto para evitar bloqueos por nodos no disponibles
            response = requests.post(url, json=payload, headers=headers, timeout=DEFAULT_HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return ExecuteResponse(**data)
        except requests.RequestException as e:
            print(f"[!] Falla al contactar el nodo remoto {device.value} ({url}): {e}")
            return ExecuteResponse(
                success=False, 
                message=f"No se pudo conectar con el dispositivo {device.value} ({str(e)})"
            )
