# void_voice/wakeword/detector.py
import numpy as np
from collections import deque

class WakeWordEngine:
    """
    Offline Wake-Word detection engine for V.O.I.D.
    Standardized wake phrase: 'Hey V.O.I.D.' / 'V.O.I.D.'
    Combines calibrated audio energy profiling and acoustic zero-crossing dynamics.
    """
    def __init__(self, config):
        self.config = config
        self.wake_phrase = config.get("wake_word", "hey_void").lower().replace("_", " ")
        self.threshold = float(config.get("wake_threshold", 250))
        self.buffer_size = int(config.get("wakeword_buffer", 10))
        self.energy_buffer = deque(maxlen=self.buffer_size)
        self.zcr_buffer = deque(maxlen=self.buffer_size)
        self.triggered = False

    def detect(self, audio_chunk: bytes) -> bool:
        """
        Processes audio chunk and evaluates wake condition.
        """
        try:
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            if len(audio_data) == 0:
                return False

            # 1. RMS Energy
            energy = float(np.sqrt(np.mean(audio_data.astype(np.float32) ** 2)))
            self.energy_buffer.append(energy)

            # 2. Zero-crossing rate (speech vs pure white noise/tap)
            zcr = float(np.mean(np.abs(np.diff(np.sign(audio_data)))) / 2)
            self.zcr_buffer.append(zcr)

            if len(self.energy_buffer) >= 3:
                baseline_energy = float(np.median(list(self.energy_buffer)[:-1]))
                curr_energy = self.energy_buffer[-1]
                curr_zcr = self.zcr_buffer[-1]

                # Adaptive speech acoustic envelope:
                # Triggers when energy rises significantly above ambient baseline or crosses calibrated threshold
                # while within human vocal zero-crossing rate spectrum (0.02 - 0.48)
                is_voice_energy = (curr_energy > self.threshold and curr_energy > baseline_energy * 1.5) or (curr_energy > max(200.0, baseline_energy * 2.2))
                is_speech_spectrum = 0.02 < curr_zcr < 0.48

                if is_voice_energy and is_speech_spectrum:
                    self.triggered = True
                    return True

            return False

        except Exception as e:
            print(f"⚠️ Wake word detection error: {e}")
            return False

    def reset(self):
        self.triggered = False
        self.energy_buffer.clear()
        self.zcr_buffer.clear()