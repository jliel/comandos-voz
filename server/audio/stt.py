import os
from typing import Optional, Union
import numpy as np

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
                print("[+] Modelo faster-whisper listo.")
            except ImportError:
                # ! faster-whisper no está instalado
                print("[!] faster-whisper no está disponible en este entorno.")
                self._model = None
            except Exception as e:
                print(f"[!] Error al cargar modelo faster-whisper: {e}")
                self._model = None

    def transcribe_audio_file(self, audio_path: str) -> Optional[str]:
        # * Transcribe un archivo de audio WAV a texto
        self._ensure_model_loaded()
        if not self._model:
            return None

        if not os.path.exists(audio_path):
            print(f"[!] Archivo de audio no encontrado: {audio_path}")
            return None

        try:
            segments, _ = self._model.transcribe(
                audio_path, 
                language="es", 
                beam_size=5
            )
            text = " ".join([segment.text for segment in segments]).strip()
            return text if text else None
        except Exception as e:
            print(f"[!] Error transcribiendo archivo {audio_path}: {e}")
            return None

    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        # * Transcribe un buffer de audio en memoria (numpy array) sin escribir a disco
        self._ensure_model_loaded()
        if not self._model:
            return None

        try:
            # * Asegurar formato float32 normalizado [-1.0, 1.0] para Whisper
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype != np.float32:
                audio_float = audio_data.astype(np.float32)
            else:
                audio_float = audio_data

            # * Aplanar a 1D si viene en formato (muestras, 1)
            if audio_float.ndim > 1:
                audio_float = audio_float.flatten()

            segments, _ = self._model.transcribe(
                audio_float, 
                language="es", 
                beam_size=5
            )
            text = " ".join([segment.text for segment in segments]).strip()
            return text if text else None
        except Exception as e:
            print(f"[!] Error transcribiendo buffer de audio en memoria: {e}")
            return None
