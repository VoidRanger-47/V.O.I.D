# ☁️ V.O.I.D. Host-Only Cloud Engine (Gemini 2.0)

The **Host-Only Cloud Engine** gives V.O.I.D. the ability to switch between its 100% offline local PyTorch transformer model and Google Gemini 2.0 cloud models for ultra-intelligent streaming token generation.

---

## 🔒 Security Guarantee
- **Host-Device Only**: Cloud token generation can **only** be turned ON/OFF and configured directly from the host console or host filesystem. Remote clients, LAN connections, or connected mobile devices cannot flip the switch or expose your API keys.
- **Auto-Fallback**: If the cloud API loses connectivity or hits rate limits, V.O.I.D. automatically falls back to the local PyTorch model.

---

## 💻 Command Line Interface (CLI)

From your project root, you can manage the cloud switch:

### 1. Check Status & Test Connection
```bash
python -m void_cloud.cli status
```

### 2. Configure Your Gemini API Key
```bash
python -m void_cloud.cli set-key AIzaSyYourGeminiApiKeyHere
```

### 3. Turn Cloud Generation ON
```bash
python -m void_cloud.cli on
```

### 4. Turn Cloud Generation OFF (Revert to 100% Offline PyTorch Model)
```bash
python -m void_cloud.cli off
```

### 5. Change Active Model
```bash
python -m void_cloud.cli set-model gemini-2.0-flash
# or
python -m void_cloud.cli set-model gemini-2.0-pro-exp
```

### 6. Test Live Token Streaming
```bash
python -m void_cloud.cli test "Explain what V.O.I.D. is in 2 sentences"
```

---

## 📁 Configuration File
Settings are saved locally in [`void_cloud/config.json`](file:///c:/Users/kbven/OneDrive/Documents/VOID/void_cloud/config.json).
