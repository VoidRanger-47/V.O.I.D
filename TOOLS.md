# V.O.I.D. — Central Tool Registry

All capabilities are unified under `core.tool_registry.ToolRegistry`.

## Registered Tools

### 1. `system_info`
- **Description**: Real-time system timestamp, operating system release, and date.
- **Permission**: `LEVEL_1_READ_INFO` | **Risk**: `LOW`
- **Offline**: Yes

### 2. `system_monitor`
- **Description**: Host CPU usage, RAM utilization, Disk space, and GPU VRAM telemetry.
- **Permission**: `LEVEL_1_READ_INFO` | **Risk**: `LOW`
- **Offline**: Yes

### 3. `world_state`
- **Description**: Complete local world context including active application, foreground window, active project, and hardware telemetry.
- **Permission**: `LEVEL_1_READ_INFO` | **Risk**: `LOW`
- **Offline**: Yes

### 4. `math_solver`
- **Description**: Solves equations, derivatives, integrals, and matrices via local SymPy.
- **Permission**: `LEVEL_0_CONVERSATION` | **Risk**: `LOW`
- **Offline**: Yes

### 5. `python_interpreter`
- **Description**: Evaluates Python code snippets inside an AST-verified sandbox with safe import proxying.
- **Permission**: `LEVEL_1_READ_INFO` | **Risk**: `MEDIUM`
- **Offline**: Yes

### 6. `local_document`
- **Description**: Parses and summarizes local text and PDF documents.
- **Permission**: `LEVEL_2_READ_FILES` | **Risk**: `LOW`
- **Offline**: Yes

### 7. `computer_control`
- **Description**: Launches approved desktop applications (VS Code, Notepad, Calc, Explorer, Terminal) without shell interpolation.
- **Permission**: `LEVEL_4_APP_CONTROL` | **Risk**: `MEDIUM`
- **Offline**: Yes

### 8. `nlp_toolkit`
- **Description**: Sentiment classification, summarization, and entity extraction.
- **Permission**: `LEVEL_0_CONVERSATION` | **Risk**: `LOW`
- **Offline**: Yes

### 9. `web_search`
- **Description**: Queries live web search when internet is available. Gracefully reports offline status without retrying if network is disconnected.
- **Permission**: `LEVEL_6_NETWORK` | **Risk**: `LOW`
- **Offline**: Optional Plugin

### 10. `phone_control`
- **Description**: Controls connected Android smartphone over ADB (USB or TCP/IP): unlocks screen, launches applications (JioCinema, WhatsApp, YouTube, etc.), places calls, controls media/volume, and captures device telemetry.
- **Permission**: `LEVEL_4_APP_CONTROL` | **Risk**: `MEDIUM`
- **Offline**: Yes
