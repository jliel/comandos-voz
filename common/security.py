import os
from functools import wraps
from typing import Callable, Any
from flask import request, jsonify
from common.constants import AUTH_HEADER_NAME

# * Módulo de seguridad y autenticación para comunicación inter-nodo

def get_configured_token() -> str:
    # * Obtiene el token interno desde la variable de entorno
    token = os.getenv("INTERNAL_AUTH_TOKEN", "")
    # ! Si el token no está configurado, advertir en log
    if not token:
        print("[!] ADVERTENCIA DE SEGURIDAD: INTERNAL_AUTH_TOKEN no está definido en el archivo .env")
    return token

def verify_token(provided_token: str) -> bool:
    # * Valida si el token proporcionado coincide con el token esperado
    expected_token = get_configured_token()
    if not expected_token:
        # ? En desarrollo temprano sin token configurado, podría permitirse si explícitamente se desea
        return True
    return bool(provided_token and provided_token.strip() == expected_token.strip())

def require_internal_token(f: Callable[..., Any]) -> Callable[..., Any]:
    # * Decorador Flask para proteger endpoints contra llamadas no autorizadas en la LAN
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        token = request.headers.get(AUTH_HEADER_NAME, "")
        if not verify_token(token):
            # ! Acceso no autorizado denegado
            return jsonify({
                "error": "Acceso no autorizado",
                "message": f"Cabecera {AUTH_HEADER_NAME} faltante o inválida."
            }), 401
        return f(*args, **kwargs)
    return decorated_function
