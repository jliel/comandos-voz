import time
import os
import requests
from typing import Dict, List, Optional
from common.constants import DeviceType, NodeStatus, DEFAULT_HTTP_TIMEOUT, AUTH_HEADER_NAME
from common.models import NodeInfo, NodeRegisterRequest
from common.security import get_configured_token

# * Servicio de registro, rastreo y estado de nodos en la red local

class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: Dict[DeviceType, NodeInfo] = {}
        # * Cargar configuraciones por defecto desde .env si existen
        self._load_fallback_nodes()

    def _load_fallback_nodes(self) -> None:
        # * Registra URLs preconfiguradas en variables de entorno como fallback
        cachy_url = os.getenv("CACHYOS_CLIENT_URL")
        if cachy_url:
            self.register_node(NodeRegisterRequest(
                device=DeviceType.CACHYOS,
                base_url=cachy_url,
                skills=["linux_scripts", "media_control"]
            ))

        win_url = os.getenv("WINDOWS_CLIENT_URL")
        if win_url:
            self.register_node(NodeRegisterRequest(
                device=DeviceType.WINDOWS,
                base_url=win_url,
                skills=["spotify", "youtube_music", "gui_automation"]
            ))

    def register_node(self, request: NodeRegisterRequest) -> NodeInfo:
        # * Registra o actualiza el estado de un nodo cliente
        node_info = NodeInfo(
            device=request.device,
            base_url=request.base_url.rstrip("/"),
            skills=request.skills,
            status=NodeStatus.ONLINE,
            last_seen=time.time()
        )
        self._nodes[request.device] = node_info
        print(f"[+] Nodo registrado: {request.device.value} en {node_info.base_url}")
        return node_info

    def get_node(self, device: DeviceType) -> Optional[NodeInfo]:
        # * Obtiene los detalles de un nodo específico
        return self._nodes.get(device)

    def list_nodes(self) -> List[NodeInfo]:
        # * Devuelve todos los nodos registrados
        return list(self._nodes.values())

    def check_node_health(self, device: DeviceType) -> NodeStatus:
        # * Valida la conectividad directa con el nodo cliente
        node = self.get_node(device)
        if not node:
            return NodeStatus.OFFLINE

        health_url = f"{node.base_url}/api/health"
        headers = {AUTH_HEADER_NAME: get_configured_token()}
        try:
            # ! Timeout explícito estricto para no colapsar el orquestador
            response = requests.get(health_url, headers=headers, timeout=DEFAULT_HTTP_TIMEOUT)
            if response.status_code == 200:
                node.status = NodeStatus.ONLINE
                node.last_seen = time.time()
                return NodeStatus.ONLINE
            else:
                node.status = NodeStatus.DEGRADED
                return NodeStatus.DEGRADED
        except requests.RequestException as e:
            # ! Fallo de conexión de red
            node.status = NodeStatus.OFFLINE
            print(f"[!] Nodo {device.value} fuera de línea ({health_url}): {e}")
            return NodeStatus.OFFLINE
