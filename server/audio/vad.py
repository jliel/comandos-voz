from typing import List
import numpy as np

# * Módulo de detección de fin de voz (VAD) para recortar grabaciones sin silencios largos

class VoiceActivityDetector:
    def __init__(self, silence_threshold_seconds: float = 1.2) -> None:
        self.silence_threshold_seconds = silence_threshold_seconds
        # TODO: Cargar modelo Silero VAD vía ONNX Runtime para máxima precisión

    def is_silence(self, audio_chunk: np.ndarray, threshold: float = 0.01) -> bool:
        # * Cálculo rápido de energía RMS para filtrado preliminar
        rms = np.sqrt(np.mean(audio_chunk**2))
        return bool(rms < threshold)
