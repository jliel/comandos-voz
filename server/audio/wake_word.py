import threading
import time
import re
from typing import Callable, List, Optional, Tuple
from collections import deque
import numpy as np

from server.audio.vad import VoiceActivityDetector
from server.audio.stt import SpeechToText
from server.audio.tts import AudioFeedback

# * Listener continuo en segundo plano para detección de "Hey Lili" y captura de comandos

# * Variaciones fonéticas comunes de cómo Whisper transcribe "Hey Lili" en español e inglés
WAKE_WORD_PATTERN = re.compile(
    r"\b(hey|oye|hola|ey|ay|ok)?\s*(lili|lily|lilly|leli|li li)\b", 
    re.IGNORECASE
)

class WakeWordListener:
    def __init__(
        self, 
        on_command_detected: Callable[[str], None],
        sample_rate: int = 16000
    ) -> None:
        self.on_command = on_command_detected
        self.sample_rate = sample_rate
        self.vad = VoiceActivityDetector(sample_rate=sample_rate)
        self.stt = SpeechToText(model_size="base")
        self.feedback = AudioFeedback()

        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        # * Inicia el hilo de escucha en segundo plano
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWordListener")
        self._thread.start()

    def stop(self) -> None:
        # * Detiene el listener
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            print("[*] Listener de micrófono detenido.")

    def _extract_wake_word(self, text: str) -> Tuple[bool, str]:
        # * Verifica si el texto contiene la palabra clave y extrae el comando remanente
        text_clean = text.strip()
        match = WAKE_WORD_PATTERN.search(text_clean)
        if match:
            # Extraer lo que viene después del trigger
            remainder = text_clean[match.end():].strip()
            # Quitar signos de puntuación iniciales (ej. comas, puntos)
            remainder = re.sub(r"^[¡!¿?,.\s]+", "", remainder).strip()
            return True, remainder
        return False, ""

    def _listen_loop(self) -> None:
        # * Bucle principal de captura y procesamiento de audio
        try:
            import sounddevice as sd
        except ImportError:
            print("[!] sounddevice no está instalado en este entorno.")
            return

        chunk_size = 1024  # ~64ms por fragmento a 16kHz
        # Buffer circular de los últimos 4 fragmentos (~250ms) para no perder el inicio del habla
        pre_buffer = deque(maxlen=4)

        print("[*] Abriendo stream de micrófono...")
        try:
            with sd.InputStream(
                samplerate=self.sample_rate, 
                channels=1, 
                dtype="int16", 
                blocksize=chunk_size
            ) as stream:
                
                print("[*] Calibrando nivel de ruido ambiental del micrófono (mantén silencio 1 segundo)...")
                self.vad.calibrate(stream, num_chunks=15, chunk_size=chunk_size)
                print("[+] ✅ Micrófono listo. Di 'Hey Lili' seguido de tu orden...")

                while self._running:
                    data, _ = stream.read(chunk_size)
                    pre_buffer.append(data.copy())

                    # * 1. Comprobar si hay actividad de voz
                    if not self.vad.is_speech(data):
                        continue

                    # * 2. Voz detectada: iniciar grabación completa
                    print("\n[🎙️ Escuchando...]")
                    initial_frames = list(pre_buffer)
                    recorded_audio = self.vad.record_until_silence(
                        stream, 
                        initial_frames=initial_frames, 
                        chunk_size=chunk_size
                    )

                    if recorded_audio is None or len(recorded_audio) < self.sample_rate * 0.4:
                        # Fragmento demasiado corto (< 0.4s), fue un chasquido o ruido breve
                        continue

                    # * 3. Transcribir con faster-whisper
                    print("[⏳ Transcribiendo voz con Whisper...]")
                    transcription = self.stt.transcribe_audio_data(
                        recorded_audio, 
                        sample_rate=self.sample_rate
                    )

                    if not transcription:
                        print("[?] No se detectó texto claro en la grabación.")
                        continue

                    print(f"[🗣️ Whisper escuchó]: \"{transcription}\"")

                    # * 4. Analizar si la frase contiene 'Hey Lili' o variantes
                    is_wake, remainder = self._extract_wake_word(transcription)

                    if is_wake:
                        print("[🔔 ¡Palabra clave 'Lili' detectada!]")
                        self.feedback.play_activation_chime()

                        if len(remainder) >= 3:
                            # * Modo 'One-shot': "Hey Lili, sube el volumen"
                            print(f"[⚡ Ejecutando comando directo]: \"{remainder}\"")
                            self.on_command(remainder)
                        else:
                            # * Modo 'Conversacional': Solo dijo "Hey Lili"
                            print("[?] Esperando tu orden tras 'Hey Lili' (habla ahora)...")
                            followup_audio = self.vad.record_until_silence(stream, chunk_size=chunk_size)
                            if followup_audio is not None:
                                followup_text = self.stt.transcribe_audio_data(
                                    followup_audio, 
                                    sample_rate=self.sample_rate
                                )
                                if followup_text:
                                    print(f"[⚡ Ejecutando comando subsecuente]: \"{followup_text}\"")
                                    self.on_command(followup_text)
                    else:
                        print("[ℹ️ Frase no dirigida a Lili (no se detectó 'Hey Lili')]\n")

        except Exception as e:
            # ! Error accediendo al hardware de audio (ej. permisos de micrófono en macOS)
            print(f"[!] Error en el flujo de captura de audio: {e}")
            print("[!] En macOS, verifica en: Preferencias del Sistema -> Seguridad y Privacidad -> Micrófono.")

