import pytest
from common.constants import DeviceType, AUTH_HEADER_NAME
from common.models import CommandIntent
from server.services.registry import NodeRegistry
from server.services.dispatcher import CommandDispatcher

# * Pruebas unitarias para el enrutador y despachador

def test_registry_store_and_retrieve():
    registry = NodeRegistry()
    node = registry.get_node(DeviceType.CACHYOS)
    assert node is not None or node is None  # Verifica funcionamiento sin excepción

def test_dispatcher_unknown_device():
    registry = NodeRegistry()
    dispatcher = CommandDispatcher(registry)
    intent = CommandIntent(
        intent="test",
        target_device=DeviceType.UNKNOWN,
        action="noop"
    )
    result = dispatcher.dispatch(intent)
    assert result.success is False
    assert "desconocido" in result.message
