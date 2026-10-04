# V.O.I.D. — Voice Interaction Pipeline

## Pipeline Overview

```
       Microphone Audio
              │
              ▼
    [ Wake Word Engine ]  ─── "Hey V.O.I.D." acoustic verification
              │
              ▼
   [ Faster-Whisper STT ] ─── 100% Offline transcription
              │
              ▼
      [ V.O.I.D. Agent ]  ─── Autonomous reasoning & tool execution
              │
              ▼
     [ Piper TTS Engine ] ─── In-process neural speech synthesis
              │
              ▼
   [ Barge-In Interrupter]─── Immediate audio purge on user voice input
```

---

## Configuration (`void_voice/config/config.json`)
```json
{
    "wake_word": "hey_void",
    "wake_threshold": 800.0,
    "mic_index": null,
    "sample_rate": 16000,
    "chunk_size": 1280,
    "whisper_model": "small.en",
    "voice": "en_US-amy-medium",
    "voice_speed": 1.0,
    "use_gpu": true,
    "tts_enabled": true,
    "dsp_effect": true
}
```

---

## Features
- **100% Offline STT**: Direct in-memory processing via Faster-Whisper with zero cloud APIs.
- **In-Process Audio Playback**: Direct audio streaming on Windows via `winsound` / PCM stream, eliminating external media player popups.
- **Barge-In Interruption**: `VoiceEngine.stop_speaking()` halts TTS immediately when speech or abort commands are detected.
