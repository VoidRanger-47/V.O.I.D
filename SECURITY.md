# V.O.I.D. — Security & Sandboxing Policy

## 1. Permission Levels
V.O.I.D. enforces granular permission levels before executing any tool or command:

| Level | Name | Description | Example Tools |
| :--- | :--- | :--- | :--- |
| **0** | `LEVEL_0_CONVERSATION` | Pure language generation and conversational math | `math_solver`, `nlp_toolkit` |
| **1** | `LEVEL_1_READ_INFO` | Read-only hardware and temporal telemetry | `system_info`, `system_monitor`, `world_state` |
| **2** | `LEVEL_2_READ_FILES` | Read-only access to local documents and workspace files | `local_document` |
| **3** | `LEVEL_3_MODIFY_FILES` | Write operations to designated local directories | Note storage, script saving |
| **4** | `LEVEL_4_APP_CONTROL` | Launch desktop applications from strict allowlist | `computer_control` (VS Code, Notepad, Calc) |
| **5** | `LEVEL_5_SYSTEM_MODS` | Process management and system service adjustments | Requires explicit confirmation |
| **6** | `LEVEL_6_NETWORK` | Optional outbound web searches | `web_search` |

---

## 2. Python AST Sandbox
Unrestricted `exec()` and `eval()` are strictly banned.
Python code submitted to `python_interpreter` is evaluated by `core.security.SecurityManager`:
1. **Static AST Analysis**: Verifies that no forbidden functions (`os.system`, `subprocess.Popen`, `shutil.rmtree`, `__import__`, `eval`) or network modules (`socket`, `requests`, `urllib`) are present.
2. **Restricted Built-ins**: Code runs inside a restricted global namespace with a safe import proxy allowing only mathematical, data-science, and algorithmic standard libraries (`math`, `random`, `re`, `time`, `datetime`, `json`, `collections`, `itertools`, `numpy`, `sympy`).
3. **Execution Constraints**: Sandboxed snippets have execution timeouts and output buffer truncation.

---

## 3. Computer Control Isolation
Application launching in `skills/computer_control.py` and `core.tool_registry.py`:
- Employs a strict allowlist (`vscode`, `notepad`, `calc`, `explorer`, `terminal`).
- Disallows `shell=True` on dynamic strings to eliminate arbitrary command injection risks.

---

## 4. Emergency Stop
An instant circuit breaker is available programmatically and via `/api/emergency_stop`. When activated, all tool execution is halted immediately until reset.
