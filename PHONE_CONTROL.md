# V.O.I.D. — Android Phone Voice & ADB Control Guide

This guide walks you through connecting your Android smartphone to V.O.I.D. and controlling it via voice commands and ADB automation.

---

## 1. Phone Prerequisites

1. **Enable Developer Options**:
   - Go to `Settings > About phone` and tap **Build number** 7 times until you see *"You are now a developer!"*
2. **Enable USB Debugging**:
   - Go to `Settings > System > Developer options` (or `Additional settings > Developer options`).
   - Toggle **USB Debugging** to **ON**.
3. **Allow Touch & Input Simulation (Crucial for OEM ROMs)**:
   - For **Xiaomi / MIUI / HyperOS / Oppo / Vivo / Realme / OnePlus**:
     - Enable **USB Debugging (Security settings)** or **Allow touch simulation via USB**.
     - *(Note: This allows ADB to perform swipe and PIN unlock gestures).*
4. **Authorize Your PC**:
   - Plug the phone into your PC using a USB cable.
   - On the phone's prompt *"Allow USB debugging?"*, check **"Always allow from this computer"** and tap **Allow**.

---

## 2. Testing the Connection (`test_connection.py`)

Run the automated verification suite to verify the bridge:

```powershell
# Run full connection diagnostics
python test_connection.py --diagnostics
```

### Interactive Test Suite:
```powershell
python test_connection.py
```
This opens an interactive menu where you can test:
- 🔓 **Unlock Phone**: Screen wake + swipe up + PIN entry
- 🚀 **Launch App**: Open JioCinema, YouTube, WhatsApp, Camera, etc.
- 📞 **Phone Call**: Direct call or open dialer with a contact/number
- 🔊 **Volume & Media**: Increase/decrease volume, play/pause
- 📸 **Screenshot**: Capture phone screen and save to PC
- 📶 **Wireless ADB**: Switch to WiFi mode (`adb tcpip 5555`)

### CLI Direct Actions:
```powershell
# Test unlocking
python test_connection.py --action unlock

# Test launching specific apps
python test_connection.py --action launch --app JioCinema
python test_connection.py --action launch --app YouTube
python test_connection.py --action launch --app WhatsApp

# Test calling
python test_connection.py --action call --number "1234567890"

# Test simulating a spoken phrase
python test_connection.py --simulate-voice "Void, open JioCinema"
python test_connection.py --simulate-voice "unlock my phone"
```

---

## 3. Wireless ADB Setup (No USB Cable Needed)

1. Connect your phone via USB first.
2. Enable TCP/IP mode:
   ```powershell
   python test_connection.py --tcpip 5555
   ```
3. Disconnect the USB cable.
4. Connect wirelessly over your home Wi-Fi:
   ```powershell
   python test_connection.py --connect <phone_ip_address>:5555
   ```
   *(Your phone IP address can be found in `Settings > About phone > Status` or via `test_connection.py --diagnostics`).*

---

## 4. Running the Voice Assistant (`run_phone_assistant.py`)

### Continuous Voice Mode (Microphone + Wake Word "Void"):
```powershell
python run_phone_assistant.py --voice
```
Say:
- *"Void"* ➔ *"Unlock my phone"*
- *"Void"* ➔ *"Open JioCinema"*
- *"Void"* ➔ *"Launch YouTube"*
- *"Void"* ➔ *"Call Mom"*
- *"Void"* ➔ *"Volume up"*
- *"Void"* ➔ *"Pause music"*
- *"Void"* ➔ *"Take a screenshot"*

### Interactive Text Mode:
```powershell
python run_phone_assistant.py --text
```

---

## 5. Configuration (`void_phone/phone_config.json`)

Customize your settings in `void_phone/phone_config.json`:

```json
{
  "unlock": {
    "default_pin": "1234",
    "swipe_start_y_percent": 0.85,
    "swipe_end_y_percent": 0.20,
    "swipe_duration_ms": 300
  },
  "apps": {
    "jiocinema": "com.jio.media.ondemand",
    "youtube": "com.google.android.youtube",
    "whatsapp": "com.whatsapp",
    "instagram": "com.instagram.android",
    "spotify": "com.spotify.music"
  },
  "contacts": {
    "mom": "+1234567890",
    "dad": "+1234567891"
  }
}
```
