from enum import Enum

# * Constantes compartidas para todo el sistema distribuido

AUTH_HEADER_NAME = "X-Internal-Token"

# ! Timeouts estrictos de red en segundos: (connect_timeout, read_timeout)
DEFAULT_HTTP_TIMEOUT = (2.0, 8.0)
LLM_HTTP_TIMEOUT = (3.0, 20.0)

class DeviceType(str, Enum):
    # * Dispositivos soportados en la arquitectura
    MACOS = "macos"
    CACHYOS = "cachyos"
    WINDOWS = "windows"
    UNKNOWN = "unknown"

class NodeStatus(str, Enum):
    # * Estados de disponibilidad de un nodo
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
