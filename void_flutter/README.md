# V.O.I.D. — Android Flutter Client 📱⚡

The official cross-platform Flutter Android application for **V.O.I.D. (Virtual Operator of Information & Development)**.

All Flutter-related files are completely self-contained within this `void_flutter/` directory.

---

## 🌟 Key Features

1. **Neural Chat & Prompt Console**:
   - Real-time conversation with V.O.I.D. offline neural model.
   - Skill routing pill badges (`CODING`, `MATH`, `VISION`, `PHONE_CONTROL`, `MEMORY_RAG`, `SYSTEM_MONITOR`).
   - Deep Think mode & Web Search toggles.
   - Quick action prompt chips.

2. **Live Vision & Perception HUD**:
   - Real-time MJPEG live webcam stream from V.O.I.D. Vision Subsystem.
   - Live detected objects pills with confidence ratings.
   - Enrolled owner identity badge with recognition confidence.
   - Scene analytics (environment, lighting, activity, people count).
   - Remote camera control and performance mode selection (`ECO`, `BALANCED`, `TURBO`).
   - Opt-in local facial profile enrollment.

3. **Hardware Telemetry Matrix**:
   - Real-time gauges for CPU processor load, RAM memory usage, and GPU dedicated VRAM (NVIDIA RTX 3050).

4. **Episodic Visual Memory Vault**:
   - Searchable observation logs from SQLite `observations.db` with importance scores and context tags.

5. **Phone ADB & App Automation**:
   - Remote actions: Unlock phone, lock screen, volume controls, app launcher (YouTube, WhatsApp, JioCinema).

6. **Host Server Connectivity**:
   - Configurable host IP (e.g. `http://10.0.2.2:5000` for Android Studio Emulator, or `http://192.168.x.x:5000` for physical devices on local Wi-Fi).
   - Built-in ping test and status indicators.

---

## 🚀 Quick Start Guide

### 1. Start the V.O.I.D. Backend Server
In the root `VOID/` directory:
```bash
python app.py
```
The server will start on `http://0.0.0.0:5000`.

---

### 2. Run the Flutter App

Navigate to this directory:
```bash
cd void_flutter
```

#### Run on Connected Android Device or Emulator:
```bash
flutter run
```

#### Build Release APK:
```bash
flutter build apk --release
```
The generated APK will be at:
`void_flutter/build/app/outputs/flutter-apk/app-release.apk`

---

## 📁 Architecture Overview

```
void_flutter/
├── android/                   # Native Android configuration, permissions, and Gradle setup
├── lib/
│   ├── main.dart             # App entrypoint with MultiProvider & Dark Theme
│   ├── core/
│   │   ├── constants/        # API endpoints & Cyberpunk color tokens
│   │   ├── models/           # Data models (ChatMessage, TelemetryData, VisionContext, MemoryItem)
│   │   ├── network/          # ApiService for REST backend calls & streaming
│   │   └── providers/        # State management (ChatProvider, VisionProvider, SystemProvider, SettingsProvider)
│   └── ui/
│       ├── theme/            # Cyberpunk dark theme with Outfit typography
│       ├── widgets/          # Reusable CyberCards, CyberButtons, TelemetryGauges, and ChatBubbles
│       └── screens/          # ChatScreen, VisionScreen, TelemetryScreen, MemoryScreen, PhoneControlScreen, SettingsScreen, HomeScreen
└── pubspec.yaml               # Flutter dependencies and assets configuration
```
