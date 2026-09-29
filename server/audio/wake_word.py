import threading
import time
import re
from typing import Callable, List, Optional
import numpy as np

from server.audio.vad import VoiceActivityDetector
from server.audio.stt import SpeechToText
from server.audio.tts import AudioFeedback

# * Listener continuo en segundo plano para detección de "Hey Lili" y captura de comandos

DEFAULT_TRIGGER_WORDS = ["hey lili", "oye lili", "hola lili", "lili"]

class WakeWordListener:
    def __init__(
        self, 
        on_command_detected: Callable[[str], None],
        trigger_words: Optional[List[str]] = None,
        sample_rate: int = 16000
    ) -> None:
        self.on_command = on_command_detected
        self.trigger_words = [w.lower() for w in (trigger_words or DEFAULT_TRIGGER_WORDS)]
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
        print(f"[*] Escucha continua activa en el micrófono (Palabras clave: {', '.join(self.trigger_words)})")

    def stop(self) -> None:
        # * Detiene el listener
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            print("[*] Listener de micrófono detenido.")

    def _clean_wake_word(self, text: str) -> Tuple_Extract:
        # * Verifica si el texto contiene la palabra clave y extrae el comando remanente
        text_lower = text.lower().strip()
        # Eliminar signos de puntuación iniciales
        text_clean = re.sub(r"^[¡!¿?,.\s]+", "", text_lower)

        for trigger in self.trigger_words:
            # Buscar el trigger al inicio o dentro de la frase
            pattern = rf"\b{re.escape(trigger)}\b"
            match = re.search(pattern, text_clean)
            if match:
                # Extraer lo que viene después del trigger
                remainder = text_clean[match.end():].strip()
                remainder = re.sub(r"^[¡!¿?,.\s]+", "", remainder)
                return True, remainder

        return False, ""

    def _listen_loop(self) -> None:
        # * Bucle principal de captura y procesamiento de audio
        try:
            import sounddevice as sd
        except ImportError:
            print("[!] sounddevice no está disponible. No se puede iniciar la captura de micrófono.")
            return

        chunk_size = 1024

        print("[+] Abriendo stream de micrófono...")
        try:
            with sd.InputStream(
                samplerate=self.sample_rate, 
                channels=1, 
                dtype="int16", 
                blocksize=chunk_size
            ) as stream:
                while self._running:
                    # * 1. Detectar si el usuario comienza a hablar (VAD)
                    data, _ = stream.read(chunk_size)
                    if not self.vad.is_speech(data):
                        time.sleep(0.01)
                        continue

                    # * 2. Se detectó voz: grabar la frase completa hasta el silencio final
                    recorded_audio = self.vad.record_until_silence(stream, chunk_size=chunk_size)
                    if recorded_audio is None or len(recorded_audio) < self.sample_rate * 0.5:
                        # Audio demasiado corto (< 0.5 segundos), ruido incidental
                        continue

                    # * 3. Transcribir la frase con faster-whisper
                    transcription = self.stt.transcribe_audio_data(recorded_audio, sample_rate=self.sample_rate)
                    if not transcription:
                        continue

                    print(f"[🎤 Transcripción micrófono]: \"{transcription}\"")

                    # * 4. Analizar si contiene la palabra clave
                    is_wake, remainder = self._clean_wake_word(transcription)

                    if is_wake:
                        # * Emitir chime de confirmación sonora
                        self.feedback.play_activation_chime()

                        if len(remainder) >= 3:
                            # * Modo 'One-shot': El usuario dijo "Hey Lili, sube el volumen"
                            print(f"[⚡ Comando directo detectado]: \"{remainder}\"")
                            self.on_command(remainder)
                        else:
                            # * Modo 'Conversacional': El usuario solo dijo "Hey Lili"
                            print("[?] Esperando instrucción subsecuente tras 'Hey Lili'...")
                            # Grabar el siguiente comando
                            followup_audio = self.vad.record_until_silence(stream, chunk_size=chunk_size)
                            if followup_audio is not None:
                                followup_text = self.stt.transcribe_audio_data(followup_audio, sample_rate=self.sample_rate)
                                if followup_text:
                                    print(f"[⚡ Comando subsecuente detectado]: \"{followup_text}\"")
                                    self.on_command(followup_text)

        except Exception as e:
            # ! Error accediendo al hardware de audio (ej. permisos de micrófono en macOS)
            print(f"[!] Error en el flujo de captura de audio: {e}")
            print("[!] En macOS, asegúrate de haber otorgado permisos de micrófono a Terminal / Python.")

Tuple_Extract = tuple[bool, str]
