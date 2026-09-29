import time
from typing import Optional, Tuple
import numpy as np

# * Módulo de detección de fin de voz (VAD) para recortar grabaciones sin silencios largos

class VoiceActivityDetector:
    def __init__(
        self, 
        sample_rate: int = 16000,
        energy_threshold: float = 0.015,
        silence_timeout_seconds: float = 1.2,
        max_duration_seconds: float = 8.0
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_timeout_seconds = silence_timeout_seconds
        self.max_duration_seconds = max_duration_seconds

    def calculate_rms(self, audio_chunk: np.ndarray) -> float:
        # * Cálculo de energía cuadrática media (RMS)
        if len(audio_chunk) == 0:
            return 0.0
        # Normalizar si viene en int16
        if audio_chunk.dtype == np.int16:
            chunk = audio_chunk.astype(np.float32) / 32768.0
        else:
            chunk = audio_chunk.astype(np.float32)
        return float(np.sqrt(np.mean(chunk**2)))

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        # * Determina si el fragmento contiene voz activa basada en energía
        return self.calculate_rms(audio_chunk) > self.energy_threshold

    def record_until_silence(self, stream, chunk_size: int = 1024) -> Optional[np.ndarray]:
        # * Graba audio continuamente desde un stream de sounddevice hasta detectar silencio final
        frames = []
        speech_detected = False
        silence_start_time: Optional[float] = None
        start_time = time.time()

        while True:
            # Leer fragmento del micrófono
            data, overflowed = stream.read(chunk_size)
            if overflowed:
                # ! Advertencia de desbordamiento de buffer de audio
                pass

            chunk = data.copy()
            frames.append(chunk)

            current_time = time.time()
            elapsed_total = current_time - start_time

            # Seguridad: no exceder duración máxima
            if elapsed_total > self.max_duration_seconds:
                break

            has_speech = self.is_speech(chunk)

            if has_speech:
                speech_detected = True
                silence_start_time = None
            elif speech_detected:
                # Si ya se detectó voz antes y ahora hay silencio
                if silence_start_time is None:
                    silence_start_time = current_time
                elif current_time - silence_start_time >= self.silence_timeout_seconds:
                    # Silencio posterior superó el umbral -> cerrar grabación
                    break

        if not speech_detected:
            return None

        # Concatenar todos los fragmentos grabados
        full_audio = np.concatenate(frames, axis=0)
        return full_audio
