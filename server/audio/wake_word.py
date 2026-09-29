import threading
import time
from typing import Callable, Optional

# * Listener continuo en segundo plano para detección de la palabra clave "Hey Lili"

class WakeWordListener:
    def __init__(self, on_wake_word_detected: Callable[[], None]) -> None:
        self.callback = on_wake_word_detected
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        # * Inicia el hilo de escucha continua en el micrófono
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[*] Módulo Wake Word escuchando 'Hey Lili'...")

    def stop(self) -> None:
        # * Detiene el listener
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            print("[*] Módulo Wake Word detenido.")

    def _listen_loop(self) -> None:
        # * Bucle de captura y detección
        # TODO: Conectar stream de micrófono (sounddevice) con openWakeWord
        while self._running:
            time.sleep(0.5)
