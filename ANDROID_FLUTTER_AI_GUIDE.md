# V.O.I.D. Android Flutter Client — Master AI Context & Specification Document 📱⚡

> **FOR AI ASSISTANTS (Claude, ChatGPT, Cursor, Copilot, DeepSeek, Gemini):**  
> You are reading the complete architectural, technical, and implementation specification for the **V.O.I.D. (Virtual Operator of Information & Development) Android Flutter Application**.  
> Ingest this document in full before generating code, refactoring features, fixing bugs, or designing new modules. Follow all established state management, UI design tokens, networking protocols, and Android platform rules described below.

---

## 📑 Table of Contents
1. [Executive Summary & Purpose](#1-executive-summary--purpose)
2. [High-Level Architecture & Data Flow](#2-high-level-architecture--data-flow)
3. [Complete Directory & File Map](#3-complete-directory--file-map)
4. [Tech Stack & Package Dependencies](#4-tech-stack--package-dependencies)
5. [Android Native Configuration & Permissions](#5-android-native-configuration--permissions)
6. [Design System & Theme Specification](#6-design-system--theme-specification)
7. [Core Data Models](#7-core-data-models)
8. [Networking & Backend API Contract](#8-networking--backend-api-contract)
9. [State Management Architecture (Provider)](#9-state-management-architecture-provider)
10. [Screen-by-Screen Implementation Guide](#10-screen-by-screen-implementation-guide)
11. [Build, Run & Deployment Guide](#11-build-run--deployment-guide)
12. [Strict Development Rules & Guardrails for AIs](#12-strict-development-rules--guardrails-for-ais)
13. [Copy-Paste AI Prompt Templates](#13-copy-paste-ai-prompt-templates)

---

## 1. Executive Summary & Purpose

**V.O.I.D. (Virtual Operator of Information & Development)** is an autonomous, multimodal AI desktop/server platform running an offline neural model, computer vision perception pipeline, hardware telemetry monitor, and ADB-powered Android phone automation bridge.

The **`void_flutter`** project is the official mobile client for Android (also compatible with Web & Desktop). It allows the user to:
- Chat with V.O.I.D. via real-time **Server-Sent Events (SSE) token streaming**.
- Monitor live webcam video streams with bounding box perception and facial recognition.
- View real-time hardware telemetry (CPU, RAM, GPU, VRAM).
- Execute ADB actions to automate and control an Android phone.
- Query visual episodic memory records stored in SQLite.
- Manage local Ollama offline models and switch between local and cloud AI providers.

---

## 2. High-Level Architecture & Data Flow

```mermaid
graph TD
    subgraph Flutter_Android_Client [void_flutter (Android Mobile App)]
        UI[UI Screens & Custom Cyber Widgets]
        P[ChangeNotifier Providers: Chat, Vision, System, Settings]
        API[ApiService (REST + SSE Streaming + SharedPreferences)]
    end

    subgraph Host_Server [V.O.I.D. Python Host (app.py :5000)]
        Flask[Flask Backend API]
        Ollama[Ollama / Local Transformer Engine]
        Vision[OpenCV Perception & Face Recognition]
        Telemetry[Hardware Monitor: psutil + pynvml]
        ADB[Android Debug Bridge Automation]
        DB[(SQLite Visual Memory Vault)]
    end

    UI -->|User Interactions / Events| P
    P -->|Method Calls| API
    API -->|HTTP REST / SSE Stream| Flask
    Flask --> Ollama
    Flask --> Vision
    Flask --> Telemetry
    Flask --> ADB
    Flask --> DB
    Flask -.->|SSE Stream Tokens / JSON Responses| API
    API -.->|Data Updates| P
    P -.->|notifyListeners| UI
```

---

## 3. Complete Directory & File Map

All Flutter-related files are located inside the `void_flutter/` directory:

```
void_flutter/
├── android/
│   └── app/
│       ├── build.gradle                          # Android build config (minSdkVersion, targetSdkVersion)
│       └── src/main/
│           └── AndroidManifest.xml              # Internet, Camera, Audio permissions & cleartext config
├── assets/
│   └── images/
│       └── void_symbol.png                       # V.O.I.D. geometric logo asset
├── lib/
│   ├── main.dart                                 # App entry point, MultiProvider registration, boot routing
│   │
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api_endpoints.dart                # REST/SSE endpoint constants & IP fallback logic
│   │   │   └── app_colors.dart                   # Cyberpunk / HUD color palette tokens
│   │   │
│   │   ├── models/
│   │   │   ├── chat_message.dart                 # ChatMessage entity, MessageSender enum, JSON serialization
│   │   │   ├── chat_session.dart                 # Multi-session conversation management
│   │   │   ├── telemetry_data.dart               # CPU, RAM, GPU, VRAM system stats model
│   │   │   ├── vision_context.dart               # Objects, Faces, SceneInfo, and VisionContextData
│   │   │   └── memory_item.dart                  # Episodic memory observation model from SQLite
│   │   │
│   │   ├── network/
│   │   │   └── api_service.dart                  # HTTP client, SSE stream parser, timeout handling
│   │   │
│   │   ├── providers/
│   │   │   ├── chat_provider.dart                # Chat state, sessions, streaming buffers, quick chips
│   │   │   ├── settings_provider.dart            # Base URL, Ollama models, ping latency, provider toggles
│   │   │   ├── system_provider.dart              # Telemetry polling, ADB automation commands
│   │   │   └── vision_provider.dart              # Vision status polling, snapshot capture, face enrollment
│   │   │
│   │   └── services/
│   │       ├── speech_service.dart               # Cross-platform voice dictation interface
│   │       ├── speech_service_stub.dart          # Mobile STT stub
│   │       └── speech_service_web.dart           # Web speech recognition implementation
│   │
│   └── ui/
│       ├── theme/
│       │   └── app_theme.dart                    # Dark Cyberpunk ThemeData with GoogleFonts.inter
│       │
│       ├── widgets/
│       │   ├── animated_void_assembly_logo.dart  # Geometric animation on boot
│       │   ├── chat_bubble.dart                  # Markdown chat bubbles with copy code & tool tags
│       │   ├── cyber_button.dart                 # Glowing HUD button with active states
│       │   ├── cyber_card.dart                   # Matte dark cards with hairline border
│       │   ├── hud_status_badge.dart             # Online/Offline neon badge
│       │   ├── telemetry_gauge.dart              # Circular & linear percentage meters
│       │   ├── void_attachment_action_menu.dart  # Image/file attachment bottom sheet
│       │   ├── void_logo.dart                    # Reusable glowing vector logo
│       │   └── zero_gravity_boot_screen.dart     # Boot sequence transition screen
│       │
│       └── screens/
│           ├── home_screen.dart                  # Main shell: IndexedStack + 6-tab BottomNav + Drawer
│           ├── void_neural_chat_screen.dart      # Flagship chat UI with token streaming, voice, tools
│           ├── chat_screen.dart                  # Alternate lightweight chat interface
│           ├── vision_screen.dart                # Live MJPEG feed, face enrollment, scene analytics
│           ├── telemetry_screen.dart             # Hardware matrix: CPU, RAM, GPU, VRAM
│           ├── memory_screen.dart                # Searchable visual memory vault
│           ├── phone_control_screen.dart         # Remote ADB phone actions & app launchers
│           ├── settings_screen.dart              # Host IP config, ping test, Ollama model manager
│           └── splash_screen.dart                # Initial splash loading screen
│
└── pubspec.yaml                                  # Package dependencies, SDK constraints, assets
```

---

## 4. Tech Stack & Package Dependencies

Defined in `void_flutter/pubspec.yaml`:

```yaml
name: void_flutter
description: "V.O.I.D. — Futuristic AI Companion & Neural Perception Client"
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  
  # State Management
  provider: ^6.1.2

  # Networking & HTTP
  http: ^1.2.1

  # Local Persistence
  shared_preferences: ^2.2.3

  # Typography & Icons
  google_fonts: ^6.2.1
  font_awesome_flutter: ^10.7.0

  # UI Animation & Formatting
  flutter_spinkit: ^5.2.1
  intl: ^0.19.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0
```

---

## 5. Android Native Configuration & Permissions

Located in `void_flutter/android/app/src/main/AndroidManifest.xml`:

### Required Permissions
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

### Critical Application Tag Settings
```xml
<application
    android:label="V.O.I.D."
    android:icon="@mipmap/ic_launcher"
    android:usesCleartextTraffic="true"
    android:theme="@android:style/Theme.Black.NoTitleBar">
```
> **IMPORTANT FOR LOCAL NETWORK ACCESS:** `android:usesCleartextTraffic="true"` is mandatory because local development connects via `http://` (unencrypted HTTP) to local IP addresses like `http://10.0.2.2:5000` or `http://192.168.x.x:5000`. Do NOT remove this flag.

---

## 6. Design System & Theme Specification

The application follows a **Minimalist Cyberpunk Dark HUD** aesthetic mirroring the desktop web interface.

### Color Tokens (`lib/core/constants/app_colors.dart`)

| Token | Hex Value | Purpose |
| :--- | :--- | :--- |
| `AppColors.bgApp` | `#0F0F11` | Deep canvas / matte charcoal black base |
| `AppColors.surface` | `#171719` | Surface / card container / sidebar |
| `AppColors.bgCard` | `#18181C` | Elevated card background |
| `AppColors.borderHairline` | `rgba(255,255,255,0.08)` | Subtle 1px dividers and outlines |
| `AppColors.borderStrong` | `rgba(255,255,255,0.14)` | Focused or highlighted borders |
| `AppColors.accent` | `#FF5500` | Electric Cyber Orange (Primary Brand) |
| `AppColors.accentDark` | `#E63E00` | Gradient end / active click state |
| `AppColors.accentLight` | `#FF7A2E` | Gradient start / hover state |
| `AppColors.textPrimary` | `#F0EEEB` | High-contrast off-white body text |
| `AppColors.textSecondary`| `#9E9EA4` | Neutral slate-gray labels & captions |
| `AppColors.textMuted` | `#8A8A88` | Low-priority timestamp & hint text |
| `AppColors.statusGreen` | `#10B981` | Online status, high confidence |
| `AppColors.danger` | `#E05656` | Offline status, errors, warnings |
| `AppColors.techBlue` | `#38BDF8` | Telemetry & secondary stats |

### Typography Rules
- Font Family: `GoogleFonts.inter` (primary) and `GoogleFonts.orbitron` (futuristic headers).
- Code blocks: Monospace font (`Courier New` or system mono) with `#121215` background.

---

## 7. Core Data Models

### 1. `ChatMessage` (`lib/core/models/chat_message.dart`)
```dart
enum MessageSender { user, voidAgent, system }

class ChatMessage {
  final String id;
  final String text;
  final MessageSender sender;
  final DateTime timestamp;
  final String? skillUsed;         // e.g. "CODING", "VISION", "MATH"
  final bool isStreaming;          // True while SSE tokens are arriving
  final Map<String, dynamic>? metadata;
}
```

### 2. `TelemetryData` (`lib/core/models/telemetry_data.dart`)
```dart
class TelemetryData {
  final double cpuPercent;         // e.g. 24.5
  final double ramUsedMb;          // e.g. 8192.0
  final double ramTotalMb;         // e.g. 16384.0
  final double ramPercent;         // e.g. 50.0
  final String gpuName;            // e.g. "NVIDIA GeForce RTX 3050"
  final double gpuVramUsedMb;      // e.g. 2100.0
  final double gpuVramTotalMb;     // e.g. 4096.0
  final String osName;             // e.g. "Windows 11"
  final bool isOnline;
}
```

### 3. `VisionContextData` (`lib/core/models/vision_context.dart`)
```dart
class VisionContextData {
  final bool isCameraActive;
  final String mode;               // "ECO", "BALANCED", "TURBO"
  final double actualFps;
  final List<VisionDetectedObject> objects;
  final List<VisionDetectedFace> faces;
  final VisionSceneInfo scene;     // lighting, peopleCount, activityLevel
}
```

### 4. `MemoryObservation` (`lib/core/models/memory_item.dart`)
```dart
class MemoryObservation {
  final int id;
  final String isoTime;
  final String eventType;          // e.g. "OBSERVATION"
  final String objectName;         // e.g. "laptop", "cup", "person"
  final String context;            // e.g. "workspace desk"
  final double confidence;         // e.g. 0.94
  final double importance;         // e.g. 0.80
}
```

---

## 8. Networking & Backend API Contract

### Dynamic Base URL Resolution (`lib/core/constants/api_endpoints.dart`)
- **Android Studio Emulator:** `http://10.0.2.2:5000` (maps to host localhost)
- **Physical Android Phone (Wi-Fi):** `http://<HOST_LAN_IP>:5000` (e.g. `http://192.168.1.15:5000`)
- **Web Browser (Chrome):** `http://127.0.0.1:5000`

### API Endpoints Catalog

| Endpoint | HTTP Method | Request Body | Response Format / Purpose |
| :--- | :--- | :--- | :--- |
| `/api/chat/stream` | `POST` | `{"message": str, "force_search": bool, "thinking_mode": bool, "provider": str, "model": str}` | **Server-Sent Events (SSE)**. Yields `data: {"token": "...", "done": false}` lines, ending with `data: {"done": true}`. |
| `/api/chat` | `POST` | `{"message": str, ...}` | Standard REST fallback returning `{"status": "success", "response": str, "skill": str}`. |
| `/api/health` | `GET` | _None_ | `{"status": "ok", "service": "void_core"}` (used for connection ping). |
| `/api/system/stats`| `GET` | _None_ | `{"status": "success", "stats": {"cpu": float, "ram_used": float, "ram_total": float, "gpu": str, "vram_used": float}}` |
| `/api/vision/status`| `GET` | _None_ | `{"data": {"camera": {"active": bool, "actual_fps": float}, "perception": {"objects": [...], "faces": [...]}}}` |
| `/api/vision/feed` | `GET` | _None_ | **MJPEG Live Stream** (`multipart/x-mixed-replace; boundary=frame`). Rendered in `Image.network`. |
| `/api/vision/start`| `POST` | `{"device_index": int}` | `{"status": "ok", "active": true}` |
| `/api/vision/stop` | `POST` | _None_ | `{"status": "ok", "active": false}` |
| `/api/vision/mode` | `POST` | `{"mode": "ECO"\|"BALANCED"\|"TURBO"}` | `{"status": "ok", "mode": str}` |
| `/api/vision/snapshot`| `POST`| _None_ | `{"status": "success", "image_base64": str, "timestamp": str}` |
| `/api/vision/enroll`| `POST` | `{"name": str, "samples": int}` | `{"status": "success", "message": "Face profile enrolled"}` |
| `/api/vision/memory`| `GET` | `?limit=30&object=<filter>` | `{"observations": [{"id": 1, "object": "phone", "confidence": 0.92, ...}]}` |
| `/api/phone/action`| `POST` | `{"command": "unlock"\|"lock"\|"vol_up"\|"open_youtube"}` | `{"status": "success", "output": str}` |
| `/api/ollama/status`| `GET` | _None_ | `{"ollama": {"is_available": bool, "server_running": bool, "installed_models": [str]}}` |
| `/api/ollama/switch`| `POST` | `{"model": str, "activate": bool}` | `{"status": "success", "active_model": str}` |
| `/api/ollama/pull` | `POST` | `{"model": str}` | `{"status": "success", "output": str}` |

---

## 9. State Management Architecture (Provider)

The app registers providers at the root `void_flutter/lib/main.dart` using `MultiProvider`:

```dart
MultiProvider(
  providers: [
    ChangeNotifierProvider(create: (_) => SettingsProvider(apiService)),
    ChangeNotifierProvider(create: (_) => ChatProvider(apiService)),
    ChangeNotifierProvider(create: (_) => VisionProvider(apiService)),
    ChangeNotifierProvider(create: (_) => SystemProvider(apiService)),
  ],
  child: const VoidApp(),
)
```

### Provider Responsibilities:
1. **`SettingsProvider`**:
   - Manages and saves `baseUrl` in `SharedPreferences`.
   - Executes ping test to calculate latency in milliseconds.
   - Fetches and switches Ollama local models.
   - Toggles Cloud vs. Offline neural inference modes.

2. **`ChatProvider`**:
   - Stores conversation sessions (`List<ChatSession>`) with local disk persistence.
   - Dispatches `streamChatMessage` to `ApiService`.
   - Accumulates streaming tokens in real time into the active message text and calls `notifyListeners()`.
   - Tracks `isLoading`, `forceSearch`, and `thinkingMode` toggles.

3. **`VisionProvider`**:
   - Periodically polls `/api/vision/status` (every 2.5 seconds when active).
   - Manages camera power (`startVision()`, `stopVision()`), performance mode switches.
   - Loads episodic visual memory entries from `/api/vision/memory`.
   - Dispatches facial profile enrollment.

4. **`SystemProvider`**:
   - Polling timer for `/api/system/stats` (every 3 seconds).
   - Stores current `TelemetryData`.
   - Dispatches ADB phone actions to `/api/phone/action`.

---

## 10. Screen-by-Screen Implementation Guide

### 1. `ZeroGravityBootScreen` (`lib/ui/widgets/zero_gravity_boot_screen.dart`)
- **Role:** Interactive futuristic boot sequence.
- **Visuals:** Renders `void_symbol.png` with scaling, glowing pulses, and a terminal log progress tracker.
- **Navigation:** Automatically transitions to `HomeScreen` via a smooth fade & scale `PageRouteBuilder`.

### 2. `HomeScreen` (`lib/ui/screens/home_screen.dart`)
- **Role:** App root scaffolding.
- **Architecture:** Hosts an `IndexedStack` to preserve state across 6 primary screens:
  1. `VoidNeuralChatScreen`
  2. `VisionScreen`
  3. `TelemetryScreen`
  4. `MemoryScreen`
  5. `PhoneControlScreen`
  6. `SettingsScreen`
- **Navigation:** Bottom navigation bar styled with `AppColors.surfaceContainer` and a slide-out hamburger drawer with chat history and connection status.

### 3. `VoidNeuralChatScreen` (`lib/ui/screens/void_neural_chat_screen.dart`)
- **Role:** Flagship neural interface (1900+ lines of polished UI).
- **Features:**
  - Token-by-token streaming with typing cursor.
  - Thinking mode status container with animated pulsing indicator.
  - Skill badges for routed tasks (`CODING`, `MATH`, `VISION`, `PHONE_CONTROL`).
  - Markdown formatting with syntax-highlighted code blocks and single-tap copy.
  - Speech-to-Text dictation integration via `SpeechService`.
  - Quick action prompt chips ("Analyze Vision", "System Health", "Python Script").
  - Model & Provider dropdown switcher.

### 4. `VisionScreen` (`lib/ui/screens/vision_screen.dart`)
- **Role:** Live perception HUD.
- **Features:**
  - Live MJPEG stream display connecting to `http://<HOST>:5000/api/vision/feed`.
  - Detected objects pill list with confidence percentage tags.
  - Recognized face profile badge.
  - Scene analytics card: Lighting level, people count, and activity level.
  - Mode selector buttons (`ECO`, `BALANCED`, `TURBO`).
  - Snapshot capture button and Face Enrollment dialog.

### 5. `TelemetryScreen` (`lib/ui/screens/telemetry_screen.dart`)
- **Role:** Hardware monitoring cockpit.
- **Features:**
  - Circular animated gauges for CPU usage and RAM percentage.
  - Linear meter for Dedicated GPU VRAM (e.g. RTX 3050).
  - Host OS details, host clock, and network status badge.

### 6. `MemoryScreen` (`lib/ui/screens/memory_screen.dart`)
- **Role:** Visual Memory Vault inspector.
- **Features:**
  - Search field to filter observations by object name (e.g. "laptop", "person").
  - Card list showing timestamps, context tags, and importance scores.

### 7. `PhoneControlScreen` (`lib/ui/screens/phone_control_screen.dart`)
- **Role:** ADB automation cockpit.
- **Features:**
  - Action buttons: Screen Unlock, Screen Lock, Volume Up/Down.
  - Quick app launchers: YouTube, WhatsApp, JioCinema.
  - Custom ADB command input field with terminal output console.

### 8. `SettingsScreen` (`lib/ui/screens/settings_screen.dart`)
- **Role:** Host connectivity & engine management.
- **Features:**
  - Host Server URL field with Quick Presets ("Android Emulator 10.0.2.2", "Localhost", "Wi-Fi LAN").
  - Ping test button displaying round-trip latency.
  - Ollama model selector with live pull progress.
  - Cloud vs. Offline engine toggle.

---

## 11. Build, Run & Deployment Guide

### Prerequisites
- Flutter SDK `>=3.0.0`
- Android Studio with Android SDK (API 33+ recommended)
- Java 17+ (for Gradle)
- V.O.I.D. Python backend running (`python app.py`)

### 1. Launch Backend Server
From the root `VOID/` directory:
```bash
python app.py
```
> Ensure the backend is listening on `0.0.0.0:5000`.

### 2. Configure Host Network for Android

#### If Running on Android Studio Emulator:
- The default preset `http://10.0.2.2:5000` works out of the box.

#### If Running on a Physical Android Phone via USB:
Run ADB reverse port forwarding so the phone can reach `localhost:5000`:
```bash
adb reverse tcp:5000 tcp:5000
```
Then in the app's Settings, set the Base URL to:
`http://127.0.0.1:5000`

#### If Running on a Physical Android Phone via Wi-Fi:
Find your computer's local IP (e.g. `192.168.1.50`) using `ipconfig` (Windows) or `ifconfig` (Linux/Mac).  
In the app's Settings, set the Base URL to:
`http://192.168.1.50:5000`

### 3. Run the Flutter App
Navigate to the Flutter directory:
```bash
cd void_flutter
flutter pub get
flutter run
```

### 4. Build Release APK
```bash
flutter build apk --release
```
The output APK will be located at:
`void_flutter/build/app/outputs/flutter-apk/app-release.apk`

---

## 12. Strict Development Rules & Guardrails for AIs

When modifying or expanding `void_flutter`, any AI assistant **MUST** adhere to the following rules:

1. **Do NOT Replace Provider:** The state management is strictly built on `provider: ^6.1.2`. Do not introduce Riverpod, Bloc, GetX, or MobX unless explicitly instructed by the user.
2. **Preserve the Cyberpunk Theme:** Always use `AppColors` tokens from `lib/core/constants/app_colors.dart`. Never hardcode random colors or use light-mode backgrounds. Keep the palette: Charcoal `#0F0F11`, Surface `#171719`, Accent `#FF5500`.
3. **Preserve Cleartext Traffic in AndroidManifest:** The app communicates with local development IP addresses via HTTP. Never remove `android:usesCleartextTraffic="true"`.
4. **Preserve Server-Sent Events (SSE) Parsing:** The chat streaming implementation relies on `api_service.dart` streaming `data: {...}` lines. Keep line buffering robust and handle network interruptions gracefully.
5. **Keep Screen State Alive:** The `HomeScreen` uses `IndexedStack` to prevent rebuilding tabs on navigation. Do not replace it with destructive page switches unless requested.
6. **Error Handling & Timeouts:** All HTTP calls in `api_service.dart` must have explicit `.timeout()` durations (e.g. 3-8 seconds) and return fallback models instead of throwing uncaught exceptions.
7. **Maintain Null Safety:** All Dart code must strictly comply with sound null safety (`sdk: '>=3.0.0 <4.0.0'`).

---

## 13. Copy-Paste AI Prompt Templates

Use these templates when asking another AI to work on this Flutter codebase:

### Prompt 1: Add a New Feature Screen
```text
I am working on the V.O.I.D. Android Flutter application.
Please refer to the "ANDROID_FLUTTER_AI_GUIDE.md" file for architecture, design tokens, and state management patterns.
I need to add a new screen called [SCREEN_NAME] that connects to the backend endpoint [ENDPOINT].
Please create:
1. The new model in lib/core/models/
2. The ApiService method in lib/core/network/api_service.dart
3. The Provider method in lib/core/providers/
4. The Cyberpunk-themed UI screen in lib/ui/screens/ using AppColors and CyberCard
5. Register it in HomeScreen's IndexedStack and BottomNavigationBar.
```

### Prompt 2: Fix a Bug or Connection Issue
```text
I am running the V.O.I.D. Android Flutter app on [EMULATOR / PHYSICAL PHONE].
Here is the error I am seeing:
[PASTE ERROR MESSAGE OR STACK TRACE]
Please analyze this against "ANDROID_FLUTTER_AI_GUIDE.md", specifically checking:
- ApiService base URL and timeout handling
- AndroidManifest.xml permissions and cleartext traffic
- Provider error state and UI notification
Provide the exact code fix.
```

### Prompt 3: Enhance UI / Add Custom Widget
```text
I want to enhance the V.O.I.D. Flutter UI by creating a new reusable widget called [WIDGET_NAME].
Refer to "ANDROID_FLUTTER_AI_GUIDE.md" for the Cyberpunk design system (AppColors.bgApp: #0F0F11, AppColors.accent: #FF5500, AppColors.surface: #171719, GoogleFonts.inter).
The widget should feature:
- [FEATURE 1]
- [FEATURE 2]
Provide the full Dart file ready to be placed in lib/ui/widgets/.
```
