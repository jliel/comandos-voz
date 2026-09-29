import subprocess
import shutil
from typing import Optional

# * Módulo de retroalimentación sonora y síntesis de voz (TTS)

class AudioFeedback:
    def __init__(self) -> None:
        # * Verifica si el comando nativo 'say' de macOS está disponible
        self.has_say = shutil.which("osascript") is not None and shutil.which("say") is not None

    def play_activation_chime(self) -> None:
        # * Emite un sonido breve al detectar la palabra clave "Hey Lili"
        try:
            if shutil.which("afplay"):
                # * Sonido de sistema estándar en macOS
                subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=False)
            else:
                print("\a", end="", flush=True)  # Bell terminal como fallback
        except Exception as e:
            # ! Error emitiendo el chime
            print(f"[!] No se pudo reproducir el chime de activación: {e}")

    def speak(self, text: Optional[str]) -> None:
        # * Sintetiza la respuesta por voz
        if not text:
            return

        print(f"[*] Lili dice: \"{text}\"")
        if self.has_say:
            try:
                # * Utiliza la voz en español predeterminada de macOS
                subprocess.run(["say", "-v", "Paulina", text], check=False)
            except Exception as e:
                print(f"[!] Error al sintetizar voz con 'say': {e}")
        else:
            # ? En entornos sin 'say' (como pruebas en Linux) solo se imprime el mensaje
            print(f"[TTS Simulado]: {text}")
