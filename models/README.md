# V.O.I.D. Local Models Directory

This directory houses all offline neural network weights, embeddings, and models for V.O.I.D.
Under the strict **4 GB VRAM (RTX 3050 Laptop GPU)** rule, models are lazily loaded and managed by `ModelManager` and `VRAMManager`.

## Subdirectories:
- `language/`: Local GGUF / PyTorch LLMs (e.g. Qwen2.5-Coder, Llama-3.2, custom checkpoints).
- `embedding/`: Local sentence transformers / embeddings (`all-MiniLM-L6-v2`, bge-small).
- `vision/`: MediaPipe models, MobileNet, YOLOv8n / face detection weights.
- `speech/`: Faster-Whisper models (small.en / base.en / tiny.en).
- `tts/`: Piper ONNX offline TTS voices.

## Discovery:
V.O.I.D. automatically detects any model files (`.pt`, `.bin`, `.gguf`, `.onnx`, `.safetensors`) placed in these folders via `model_manager.discover_local_models()`.
