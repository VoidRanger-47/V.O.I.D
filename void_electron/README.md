# V.O.I.D. — Standalone Electron Desktop App

A native Windows desktop application wrapper for the **V.O.I.D. Neural Engine**.

---

## What This Does

- 🖥️ **Native Desktop Window**: Runs V.O.I.D. inside a dedicated, frameless dark-themed desktop application (not inside a browser tab).
- 🚀 **Auto-Backend Management**: Automatically launches `python app.py` on startup and gracefully terminates it on window close.
- ⚡ **Zero Setup**: 1-click launch via `launch_void_app.bat` or `launch_void_app.ps1`.

---

## How to Run

### Method 1: 1-Click Batch Launcher (Windows)
Double-click:
```cmd
launch_void_app.bat
```

### Method 2: PowerShell Launcher
```powershell
.\launch_void_app.ps1
```

### Method 3: Command Line
```bash
cd void_electron
npm start
```
