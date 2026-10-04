# core/audio_stream.py
import pyaudio
import numpy as np

class AudioStreamManager:
    """Handles the creation and management of PyAudio streams."""
    def __init__(self, config):
        self.config = config
        self.pyaudio_instance = pyaudio.PyAudio()
        self.mic_index = self._get_mic_index()
        self.rate = config.get("sample_rate", 16000)
        self.chunk_size = config.get("chunk_size", 1280)

    def _get_mic_index(self):
        """Identifies the correct microphone index based on config."""
        index = self.config.get("mic_index")
        if index is None:
            # Attempt to find default input device
            try:
                default_device = self.pyaudio_instance.get_default_input_device_info()
                print(f"🎤 Using default mic: {default_device['name']} (Index: {default_device['index']})")
                return default_device['index']
            except Exception:
                print("⚠️ Warning: Could not find default mic. Listing available devices:")
                info = self.pyaudio_instance.get_host_api_info_by_index(0)
                device_count = self.pyaudio_instance.get_device_count()
                
                mic_found = False
                for i in range(device_count):
                    device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, i)
                    if (device_info.get('maxInputChannels') > 0):
                        print(f"   [{i}] {device_info['name']}")
                        if not mic_found:
                            # Use first available input device as fallback
                            index = i
                            mic_found = True
                if index is None:
                    raise Exception("❌ No audio input device found.")
                return index
        return index

    def open_input_stream(self):
        """Opens and returns the input stream for wake word detection."""
        return self.pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.mic_index
        )

    def close(self):
        """Terminates the PyAudio instance."""
        self.pyaudio_instance.terminate()