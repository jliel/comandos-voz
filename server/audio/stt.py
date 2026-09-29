import os
from typing import Optional

# * Módulo de Speech-to-Text (STT) con faster-whisper

class SpeechToText:
    def __init__(self, model_size: str = "base", device: str = "cpu") -> None:
        self.model_size = model_size
        self.device = device
        self._model = None

    def _ensure_model_loaded(self) -> None:
        # * Carga diferida del modelo para optimizar el arranque
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                print(f"[*] Cargando modelo faster-whisper '{self.model_size}' en {self.device}...")
                self._model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type="int8"
                )
            except ImportError:
                # ! faster-whisper no está instalado
                print("[!] faster-whisper no está disponible en este entorno.")
                self._model = None

    def transcribe_audio_file(self, audio_path: str) -> Optional[str]:
        # * Transcribe un archivo de audio WAV a texto
        self._ensure_model_loaded()
        if not self._model:
            return None

        if not os.path.exists(audio_path):
            print(f"[!] Archivo de audio no encontrado: {audio_path}")
            return None

        segments, _ = self._model.transcribe(
            audio_path, 
            language="es", 
            beam_size=5
        )
        text = " ".join([segment.text for segment in segments]).strip()
        return text if text else None
