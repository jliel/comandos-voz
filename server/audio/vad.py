import time
from typing import List, Optional, Tuple
import numpy as np

# * Módulo de detección de fin de voz (VAD) para recortar grabaciones sin silencios largos

class VoiceActivityDetector:
    def __init__(
        self, 
        sample_rate: int = 16000,
        energy_threshold: float = 0.005,
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

    def calibrate(self, stream, num_chunks: int = 20, chunk_size: int = 1024) -> None:
        # * Mide el ruido ambiental durante ~1 segundo para calibrar el umbral dinámicamente
        rms_values = []
        try:
            for _ in range(num_chunks):
                data, _ = stream.read(chunk_size)
                rms_values.append(self.calculate_rms(data))
            
            if rms_values:
                ambient_rms = float(np.mean(rms_values))
                # El umbral de habla se coloca al menos 2.2x por encima del ruido de fondo
                self.energy_threshold = max(0.004, ambient_rms * 2.2)
                print(f"[🎙️ Calibración de micrófono]: Ruido base: {ambient_rms:.4f} -> Umbral de habla: {self.energy_threshold:.4f}")
        except Exception as e:
            print(f"[!] No se pudo calibrar micrófono: {e}, usando umbral por defecto: {self.energy_threshold}")

    def record_until_silence(
        self, 
        stream, 
        initial_frames: Optional[List[np.ndarray]] = None,
        chunk_size: int = 1024
    ) -> Optional[np.ndarray]:
        # * Graba audio continuamente desde sounddevice incluyendo los fragmentos iniciales
        frames = list(initial_frames) if initial_frames else []
        speech_detected = bool(frames)
        silence_start_time: Optional[float] = None
        start_time = time.time()

        while True:
            data, overflowed = stream.read(chunk_size)
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
                if silence_start_time is None:
                    silence_start_time = current_time
                elif current_time - silence_start_time >= self.silence_timeout_seconds:
                    # Silencio posterior detectado -> terminar toma
                    break

        if not speech_detected or len(frames) == 0:
            return None

        # Concatenar todos los fragmentos
        full_audio = np.concatenate(frames, axis=0)
        return full_audio
