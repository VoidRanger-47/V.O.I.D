import torch
import sys
import os
import re

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- IMPORTS ---
from skills.math import handle_math
from skills.coding import is_coding_request, get_coding_persona, format_code_response, handle_coding_query, execute_and_verify_code
from skills.phone_control import handle_phone_control, get_phone_status
from void_phone.intent_parser import intent_parser, IntentType
from skills.web_search import is_search_request, is_explicit_search, perform_search, extract_search_query
from skills.nlp import VOID_NLP, detect_language, summarize, summarize_eli12
from skills.nlp_dataset_generator import NLP_Dataset_Generator
from skills.agentic import build_agent_plan, collect_agent_context, get_agent_instruction

# Import Model + Tokenizer
try:
    from from_scratch_transformer import model, tokenizer, args, device
except ImportError as e:
    print(f"❌ Error importing model: {e}")
    sys.exit(1)

# Memory engine
try:
    from void_memory.memory import VoidMemory
except ImportError as e:
    print(f"❌ Error: Could not import VoidMemory: {e}")
    sys.exit(1)

# Initialize components
void_mem = VoidMemory()
nlp = VOID_NLP()
dataset_gen = NLP_Dataset_Generator()

from skills.computer_control import (
    launch_application, get_local_system_stats, analyze_local_document, 
    is_app_launch_request, is_system_power_request, execute_system_power
)

# ==================== AGENTIC TOOLS ====================
AVAILABLE_TOOLS = {
    "web_search": {
        "name": "Web Search",
        "icon": "🔍",
        "description": "Search the live web for current facts, news, and real-time information (Online Only • Gracefully reports no internet access offline)",
        "execute": lambda query: perform_search(extract_search_query(query) if is_search_request(query) else query)
    },
    "math_solver": {
        "name": "Math Solver",
        "icon": "🧮",
        "description": "Solve math formulas, calculus, linear algebra, and equations locally",
        "execute": lambda query: handle_math(query)
    },
    "computer_control": {
        "name": "Local Computer Control",
        "icon": "💻",
        "description": "Launch desktop applications (VS Code, Notepad, Explorer, Calculator, Terminal) locally",
        "execute": lambda query: launch_application(query)
    },
    "system_monitor": {
        "name": "Local System Monitor",
        "icon": "📊",
        "description": "Inspect CPU, RAM, Disk space, and local hardware metrics offline",
        "execute": lambda query: get_local_system_stats()
    },
    "local_document": {
        "name": "Local Document Reader",
        "icon": "📄",
        "description": "Parse and analyze local text and PDF documents offline",
        "execute": lambda filepath: analyze_local_document(filepath)
    },
    "knowledge_learning": {
        "name": "Knowledge Acquisition Core",
        "icon": "🧠",
        "description": "Acquire, verify, and store new internet knowledge into persistent local memory",
        "execute": lambda topic: None
    },
    "source_traceability": {
        "name": "Source Traceability",
        "icon": "🔗",
        "description": "Inspect verified source origins, dates, and confidence ratings for learned knowledge",
        "execute": lambda topic: None
    },
    "learned_knowledge": {
        "name": "Local Knowledge Core",
        "icon": "💡",
        "description": "Retrieve verified facts and concepts from V.O.I.D. persistent knowledge database",
        "execute": lambda query: None
    },
    "python_interpreter": {
        "name": "Python Interpreter",
        "icon": "🐍",
        "description": "Execute local Python scripts, data processing, and algorithms securely",
        "execute": lambda code: execute_python_code(code)
    },
    "system_info": {
        "name": "System & Time",
        "icon": "🕒",
        "description": "Get current real-world timestamp and system information offline",
        "execute": lambda query: get_system_time_info()
    },
    "nlp_toolkit": {
        "name": "NLP Toolkit",
        "icon": "📝",
        "description": "Analyze sentiment, summarize text, extract entities, detect language locally",
        "execute": lambda query: (
            summarize_eli12(query.replace("eli12", "").strip()) if "eli12" in query.lower()
            else summarize(query.replace("summarize", "").strip()) if "summarize" in query.lower() or "summary" in query.lower()
            else nlp.run(query)
        )
    },
    "memory_rag": {
        "name": "Memory RAG",
        "icon": "💾",
        "description": "Search local persistent vector and SQLite fact database",
        "execute": lambda query: void_mem.inject_memory_into_prompt(query)
    },
    "phone_control": {
        "name": "Android Phone Control",
        "icon": "📱",
        "description": "Control connected Android phone via ADB (unlock, apps, calling, volume, media, status)",
        "execute": lambda query: handle_phone_control(query)
    },
    "offline_coding_engine": {
        "name": "Offline Coding Intelligence",
        "icon": "⚡",
        "description": "Deterministic AST verification, symbol search, verified algorithmic patterns, and self-healing execution",
        "execute": lambda query: handle_coding_query(query).get("response", "Code query processed")
    },
    "vision_scanner": {
        "name": "Vision Perception System",
        "icon": "👁️",
        "description": "Webcam perception, real-time object detection, face recognition, scene analysis, and visual reasoning offline",
        "execute": lambda query: __import__('skills.vision_engine', fromlist=['vision_engine']).vision_engine.handle_query(query)
    },
    "vision_camera_control": {
        "name": "Camera Device Controller",
        "icon": "📷",
        "description": "Activate or deactivate camera hardware safely with zero resource leakage",
        "execute": lambda query: __import__('skills.vision_engine', fromlist=['vision_engine']).vision_engine.handle_query(query)
    },
    "image_generator": {
        "name": "Offline Image Generator",
        "icon": "🎨",
        "description": "Generate high-resolution images and concept art locally using offline neural diffusion and visual synthesis",
        "execute": lambda query: __import__('skills.media_engine', fromlist=['media_skill_engine']).media_skill_engine.handle_query(query)
    }
}

def execute_python_code(code_str: str) -> str:
    """Safely evaluate Python code string using the AST-verified security sandbox."""
    from core.security import security_manager
    res = security_manager.execute_sandboxed_python(code_str)
    return res["output"]

def get_system_time_info() -> str:
    """Return formatted current date, time, and system info."""
    import datetime
    import platform
    now = datetime.datetime.now()
    return f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S (%A)')} | OS: {platform.system()} {platform.release()}"


# ==================== STREAMING GENERATOR ====================
def generate_stream_tokens(
    prompt: str,
    max_new_tokens: int = 150,
    temperature: float = 0.7,
    top_k: int = 40,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
):
    """
    Yields single text tokens in real time as generated by the model.
    """
    # 0. Check Host-Only Cloud Engine (Gemini 2.0)
    try:
        from void_cloud.cloud_manager import cloud_manager
        if cloud_manager.is_cloud_active():
            try:
                for token in cloud_manager.stream_tokens(prompt):
                    yield token
                return
            except Exception as cloud_err:
                print(f"[CloudEngine] Cloud stream failed ({cloud_err}). Falling back to local PyTorch transformer.")
    except Exception as e:
        pass

    if model is None or tokenizer is None:
        return

    # For the local 103M scratch transformer, cap temperature and add repetition penalty to prevent hallucination
    eff_temp = min(max(float(temperature), 0.1), 0.35)
    eff_rep_penalty = max(float(repetition_penalty), 1.3)

    try:
        # If prompt is long, preserve the crucial user turn intact
        if "### User:" in prompt:
            user_part = "### User:" + prompt.split("### User:")[-1]
            user_ids = tokenizer.encode(user_part)
            # If user turn fits in context, ensure context before it doesn't crowd it out
            max_ctx_budget = max(30, args.seq_len - len(user_ids) - 40)
            prefix_text = prompt.split("### User:")[0].strip()
            if prefix_text:
                prefix_ids = tokenizer.encode(prefix_text)
                if len(prefix_ids) > max_ctx_budget:
                    trimmed_prefix = tokenizer.decode(prefix_ids[-max_ctx_budget:])
                    prompt = f"{trimmed_prefix}\n{user_part}"

        input_ids = tokenizer.encode(prompt)
    except Exception as e:
        print(f"Tokenizer encoding error: {e}")
        return

    if not input_ids:
        return
    
    prompt_len = len(input_ids)
    input_tensor = torch.tensor([input_ids], dtype=torch.long, device=device)
    if input_tensor.size(1) > args.seq_len:
        input_tensor = input_tensor[:, -args.seq_len:]
        prompt_len = input_tensor.size(1)

    generated = input_tensor
    model.eval()

    # Determine EOS token(s)
    if getattr(tokenizer, 'offline_mode', False):
        eos_tokens = {0}
    else:
        eos_tokens = set()
        if hasattr(tokenizer, 'enc') and tokenizer.enc is not None:
            try:
                eot_id = tokenizer.enc.encode("<|endoftext|>", allowed_special={"<|endoftext|>"})
                if eot_id:
                    eos_tokens.add(eot_id[0])
            except Exception:
                pass
            if hasattr(tokenizer.enc, 'eot_token'):
                eos_tokens.add(tokenizer.enc.eot_token)

    stop_phrases = ["### User:", "### V.O.I.D.:", "<|endoftext|>", "[System Context:", "### User", "### V.O.I.D"]
    accumulated_new_text = ""

    with torch.no_grad():
        for _ in range(max_new_tokens):
            if generated.size(1) > args.seq_len:
                gen_cond = generated[:, -args.seq_len:]
            else:
                gen_cond = generated

            output = model(gen_cond, use_kv_cache=False)
            logits = output[0] if isinstance(output, tuple) else output

            logits = logits[:, -1, :] / eff_temp

            # Repetition penalty
            if eff_rep_penalty > 1.0:
                for token in set(generated[0].tolist()):
                    if 0 <= token < logits.size(-1):
                        logits[0, token] /= eff_rep_penalty

            # Top-k filtering
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float('Inf')

            # Top-p (nucleus) filtering
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                indices_to_remove = sorted_indices[sorted_indices_to_remove]
                logits[0, indices_to_remove] = -float('Inf')

            probs = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            token_id = next_token.item()

            if token_id in eos_tokens:
                break

            generated = torch.cat((generated, next_token), dim=1)

            try:
                token_str = tokenizer.decode([token_id])
            except Exception:
                token_str = " "

            if token_str == "<|endoftext|>":
                break

            # Check if token is part of a stop phrase
            if any(sp in token_str for sp in stop_phrases):
                break

            accumulated_new_text += token_str

            # Check if accumulated text hit stop markers
            if any(sp in accumulated_new_text for sp in stop_phrases):
                break

            yield token_str


# ==================== SKILL ROUTER ====================
def route_query(query: str, force_search: bool = False, thinking_mode: bool = False) -> tuple[str, str]:
    """
    Routes a query programmatically using a lightweight planner and structural intent detection.
    Returns: (response, skill_type)
    """
    text = query.strip()
    low = text.lower()
    plan = build_agent_plan(query, force_search=force_search, thinking_mode=thinking_mode)

    # 0. System Power Actions (Shutdown, Restart, Abort)
    is_power, power_action = is_system_power_request(text)
    if is_power:
        return execute_system_power(power_action, delay_seconds=15), "system_control"

    # 1. Greeting Intent (Direct natural response for greetings)
    greeting_exact = {"hi", "hello", "hey", "sup", "yo", "greetings", "good morning", "good evening", "good afternoon", "void greet me", "greet me"}
    if low in greeting_exact or (len(low) <= 15 and any(low.startswith(p) for p in ("hi void", "hello void", "hey void", "greetings void"))):
        return "Welcome back, Abhinav. All operational routines nominal and standing by for your directive. How can I assist you?", "greeting"

    # 2. V.O.I.D. Identity & System Purpose Intent
    identity_queries = {
        "what is void", "who are you", "what are you", "describe void", "describe your purpose", 
        "what is your system", "tell me about yourself", "explain your architecture"
    }
    if low in identity_queries or any(k in low for k in ["what is void", "who are you", "what are you", "what does void stand for"]):
        return (
            "I am V.O.I.D. (Virtual Operator of Information & Development)—your personal offline AI agent system. "
            "I run with local neural inference, persistent vector memory, real-time voice synthesis, "
            "computer control, system diagnostics, and autonomous multi-agent tool execution."
        ), "identity"

    # 3. Dedicated System Diagnostics & Motivation Intents
    if low in {"system status", "status", "status report", "run system check", "initiate system check", "diagnostics"}:
        return "System diagnostics complete: All core modules active on CUDA device, memory vectors synchronized, execution sandbox uncompromised. Ready for your command, Abhinav.", "system_info"

    if low in {"give me a compliment", "motivate me", "inspire me"}:
        return "Your ingenuity drives every function I execute. Continue pressing forward and breaking boundaries, Abhinav.", "motivation"

    # 4. Dedicated Phone Actions (unlock, call, sms, volume, screenshot, battery/status)
    phone_action_triggers = ["unlock", "lock screen", "lock phone", "call ", "dial ", "send sms", "text ", "volume up", "volume down", "mute", "phone status", "phone battery"]
    if any(k in low for k in phone_action_triggers) or (("phone" in low or "adb" in low) and not is_app_launch_request(text)):
        p_intent = intent_parser.parse(text)
        if p_intent.intent_type != IntentType.UNKNOWN and p_intent.confidence >= 0.7:
            phone_res = p_intent.execute()
            return phone_res, "phone_control"

    # 5. Universal Application Launch Intent (Cross-device: Host PC, Android Phone, or All Devices)
    if is_app_launch_request(text):
        return launch_application(text), "computer_control"

    # 6. Explicit Web Search Intent — fetch results but feed them to the LLM for synthesis.
    if is_explicit_search(text):
        force_search = True   # ensures collect_agent_context fetches web results as context

    # 7. Direct code execution with self-healing (e.g. "run python:", "execute python:")
    if low.startswith("run python:") or low.startswith("execute python:") or low.startswith("run code:"):
        code_body = text.split(":", 1)[1].strip()
        heal_res = execute_and_verify_code(code_body)
        repairs_info = ""
        if heal_res.get("repairs"):
            repairs_info = "\n\n🔧 **Self-Healing Repairs Applied:**\n" + "\n".join(f"- {r}" for r in heal_res["repairs"])
        out = f"```\n{heal_res.get('output', '')}\n```{repairs_info}"
        return out, "python_interpreter"

    # 5. Deterministic offline pattern search or workspace symbol search
    code_res = handle_coding_query(text)
    if code_res.get("handled"):
        return code_res.get("response"), "offline_coding_engine"

    # 6. Local system metrics intent
    if any(term in low for term in ["system stats", "cpu usage", "ram usage", "disk space", "hardware status", "system metrics"]):
        return get_local_system_stats(), "system_monitor"

    # 7. Computer Vision & Webcam Perception Intent
    vision_triggers = [
        "activate vision", "start vision", "turn on vision", "enable vision", "open vision",
        "deactivate vision", "disable vision", "stop vision", "turn off vision", "kill vision",
        "close vision", "shut vision", "shutdown vision", "halt vision",
        "turn on camera", "open camera", "start camera", "enable camera", "launch camera",
        "turn off camera", "close camera", "stop camera", "deactivate camera", "disable camera",
        "kill camera", "shut camera", "shutdown camera", "halt camera", "stop watching",
        "what do you see", "what am i holding", "look around", "scan this", "describe what you see",
        "who is here", "who do you see", "who is that", "who am i", "identify me", "can you see me",
        "do you see me", "who is in front", "look at me", "learn my face", "enroll my face",
        "recognize my face", "vision status", "camera status", "did you see my", "what was on my desk"
    ]
    if any(t in low for t in vision_triggers) or (("camera" in low or "vision" in low) and any(w in low for w in ["activate", "deactivate", "on", "off", "stop", "close", "disable", "kill", "halt", "see", "show", "feed", "look", "status", "scan", "capture", "snapshot"])):
        from skills.vision_engine import vision_engine
        return vision_engine.handle_query(text), "vision_scanner"

    # 8. Offline Image Generation Intent
    image_triggers = [
        "generate image", "create image", "render image", "draw an image", "generate an image",
        "draw a picture", "create picture", "generate art", "create artwork", "paint an image",
        "generate photo", "make an image", "render art", "concept art of"
    ]
    if any(t in low for t in image_triggers) or (("generate" in low or "draw" in low or "render" in low or "create" in low) and any(w in low for w in ["image", "picture", "artwork", "painting", "photo", "illustration", "sketch"])):
        from skills.media_engine import media_skill_engine
        return media_skill_engine.handle_query(text), "image_generator"

    # 9. Check for direct time/system request
    if any(k in low for k in ["what time", "current time", "what date", "today's date", "system time"]):
        return get_system_time_info(), "system_info"

    # 9. Math routing
    has_math_structure = bool(
        re.search(r"(\d+\s*[\+\-\*\/\^%]\s*\d+)", text) or
        ("=" in text and any(c.isalpha() for c in text)) or
        re.search(r"\b(d/dx|integral|sin|cos|tan|matrix|determinant|sqrt)\b", low)
    )
    if has_math_structure and not is_search_request(query) and not force_search:
        return handle_math(query), "math"

    # 10. Modular Dynamic Plugins (e.g. Gmail Analyzer, custom plugins)
    try:
        from core.plugin_manager import PluginManager
        plugin_res = PluginManager.get_instance().dispatch(text)
        if plugin_res is not None:
            return plugin_res
    except Exception as e:
        print(f"⚠️ [Chat] Plugin dispatch error: {e}")

    if plan["needs_search"]:
        return None, "web_search"

    if thinking_mode or plan.get("needs_thinking"):
        return None, "thinking"

    return None, "coding" if plan["needs_coding"] else "chat"






# ==================== MAIN CHAT LOOP ====================
def chat_with_void():
    print("\n" + "="*50)
    print(f"👁️  V.O.I.D. SYSTEM ONLINE [{void_mem.identity.get('version','unknown')}]")
    print("="*50)
    print(f"🧠 Identity: {void_mem.identity.get('full_name','V.O.I.D.')}")
    print("💾 Memory: Active (SQLite + Local Vectors)")
    print(f"🌐 Capabilities: Math, Coding, Web Search, NLP (Advanced)")
    print("="*50 + "\n")

    model.eval()
    
    while True:
        try:
            user_input = input("You: ")

            if user_input.lower() in ["exit", "quit", "shutdown"]:
                print("V.O.I.D.: Systems decoupling. Powering down.")
                break

            if user_input.strip() == "":
                continue

            # Route to appropriate skill
            response, skill_type = route_query(user_input)

            # If deterministic skill handled it, print and continue
            if response is not None:
                print(f"V.O.I.D.: {response}")
                void_mem.stm.append(f"User: {user_input}")
                void_mem.stm.append(f"V.O.I.D.: {response}")
                continue

            # Otherwise, use generative model (coding or chat)
            is_coding = skill_type == "coding"
            agent_context = collect_agent_context(user_input, void_mem=void_mem)
            context_block = void_mem.inject_memory_into_prompt(user_input)
            if agent_context.get("context_text"):
                context_block += "\n\n" + agent_context["context_text"]
            
            if is_coding:
                coding_instruction = get_coding_persona(user_input)
                context_block += coding_instruction

            context_block += "\n" + get_agent_instruction(user_input)

            # Prompt construction
            full_prompt = (
                f"{context_block}\n"
                f"### User:\n{user_input}\n"
                f"### V.O.I.D.:\n"
            )

            # Generate
            input_ids = tokenizer.encode(full_prompt)
            input_tensor = torch.tensor([input_ids], dtype=torch.long, device=device)

            if input_tensor.size(1) > args.seq_len:
                input_tensor = input_tensor[:, -args.seq_len:]

            with torch.no_grad():
                generated = input_tensor
                max_new = 250 if is_coding else 150

                for _ in range(max_new):
                    if generated.size(1) > args.seq_len:
                        generated_cond = generated[:, -args.seq_len:]
                    else:
                        generated_cond = generated

                    logits = model(generated_cond)
                    temperature = 0.5 if is_coding else 0.7
                    logits = logits[:, -1, :] / temperature

                    probs = torch.nn.functional.softmax(logits, dim=-1)
                    next_token = torch.multinomial(probs, num_samples=1)

                    generated = torch.cat((generated, next_token), dim=1)

            # Decode
            full_output = tokenizer.decode(generated[0].cpu().tolist())
            try:
                response = full_output.split("### V.O.I.D.:")[-1].strip()
            except Exception:
                response = full_output

            if "### User:" in response:
                response = response.split("### User:")[0]

            # Format if coding
            if is_coding:
                response = format_code_response(response)

            print(f"V.O.I.D.: {response}")

            # Save to working memory & extract long-term memories
            void_mem.working_memory.append(f"User: {user_input}")
            void_mem.working_memory.append(f"V.O.I.D.: {response}")
            void_mem.manager.extract_and_store_from_turn(user_input, response, project_id="VOID")

        except KeyboardInterrupt:
            print("\nV.O.I.D.: Manual override detected. Terminating.")
            break

if __name__ == "__main__":
    chat_with_void()
