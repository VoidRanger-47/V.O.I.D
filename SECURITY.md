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

## 2. Python AST Execution Guardrail
Unrestricted `exec()` and `eval()` are banned. Python code submitted to `python_interpreter` is evaluated by `core.security.SecurityManager` as an application-level **defense-in-depth guardrail**:
1. **Static AST Analysis**: Statically parses candidate code to verify that common dangerous functions (`os.system`, `subprocess.Popen`, `shutil.rmtree`, `__import__`, `eval`) or network modules (`socket`, `requests`, `urllib`) are not referenced.
2. **Restricted Built-ins**: Code executes with a restricted global namespace proxy permitting only safe mathematical and data-science libraries (`math`, `random`, `re`, `time`, `datetime`, `json`, `collections`, `itertools`, `numpy`, `sympy`).
3. **Execution Constraints**: Snippets are executed with strict timeouts and output buffer truncation.

> **Security Advisory**: Static AST blocklists are application guardrails and can theoretically be bypassed via dynamic reflection or obscure Python runtime internals. They do not constitute hard operating system isolation. For adversarial or untrusted third-party code execution, deploy V.O.I.D. inside an OS container (Docker/Podman) with strict `cgroups`/`rlimits` or a dedicated microVM (gVisor/Firecracker).

---

## 3. Computer Control Isolation
Application launching in `skills/computer_control.py` and `core.tool_registry.py`:
- Employs a strict allowlist (`vscode`, `notepad`, `calc`, `explorer`, `terminal`).
- Disallows `shell=True` on dynamic strings to eliminate arbitrary command injection risks.

---

## 4. Emergency Stop
An instant circuit breaker is available programmatically and via `/api/emergency_stop`. When activated, all tool execution is halted immediately until reset.
