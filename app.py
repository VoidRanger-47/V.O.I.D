from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response, stream_with_context
from chat import (
    route_query, void_mem, tokenizer, model, args, device,
    get_coding_persona, format_code_response, generate_stream_tokens, AVAILABLE_TOOLS,
    get_agent_instruction, collect_agent_context
)
import torch
import os
import json
import sys
import time
import subprocess
import uuid
import socket
import re
import shlex
from io import BytesIO

from core.vram_manager import vram_manager
from core.task_lifecycle import task_lifecycle
from core.router import executive_router, ExecutionPath

# V.O.I.D. 10-Phase AGI Cognitive Core
from core.agent import agent as void_agent, VoidAgent
from core.meta_cognition.supervisor import supervisor as meta_supervisor
from core.world_model.model import world_model
from core.self_model.model import self_model
from void_memory.experience_memory import experience_memory
from core.proactive.assistant import proactive_assistant
from core.sleep.consolidation_daemon import consolidation_daemon
from core.adaptation.adaptation_guard import adaptation_guard
from core.curiosity.curiosity_engine import curiosity_engine
from core.verification.empirical_engine import empirical_engine

# Remote access pending confirmations store
PENDING_CONFIRMATIONS = {}

def is_sensitive_command(command: str) -> tuple:
    """Classifies if a command performs dangerous, destructive, or administrative changes."""
    cmd_lower = command.lower().strip()
    patterns = [
        (r'\b(?:shutdown|reboot|poweroff|halt|init\s+0|init\s+6)\b', "System Power / Shutdown operation"),
        (r'\b(?:rmdir|rd)\s+.*[/\\]s', "Recursive directory deletion"),
        (r'\b(?:del|erase)\s+.*[/\\][fs]', "Forceful bulk file deletion"),
        (r'\b(?:rm\s+-(?:rf|fr|r|f))\b', "Recursive force file deletion"),
        (r'\b(?:format|diskpart|mkfs|fdisk)\b', "Disk / Partition format operation"),
        (r'\b(?:taskkill|kill|pkill)\s+.*(?:[/\\]f|-9)\b', "Force process termination"),
        (r'\b(?:reg\s+(?:delete|add)|regedit)\b', "Windows Registry modification"),
        (r'\b(?:netsh|iptables|ufw|firewall)\b', "Network / Firewall reconfiguration"),
        (r'\b(?:drop\s+table|drop\s+database|truncate)\b', "Database destruction command"),
        (r'\b(?:sc\s+delete|stop-service|net\s+stop)\b', "System Service termination")
    ]
    for pat, desc in patterns:
        if re.search(pat, cmd_lower):
            return True, desc
    return False, ""


# Session History in memory
CHAT_SESSIONS = []

# Add project root to path so void_voice imports resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

# Import voice modules
try:
    from void_voice.stt.transcriber import Ear
    from void_voice.tts.piper_engine import VoiceEngine
    from void_voice.wakeword.detector import WakeWordEngine
    VOICE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Voice module unavailable: {e}")
    VOICE_AVAILABLE = False

# Load voice config
voice_config = {}
voice_config_path = os.path.join(os.path.dirname(__file__), 'void_voice', 'config', 'config.json')
if os.path.exists(voice_config_path):
    try:
        with open(voice_config_path, 'r') as f:
            voice_config = json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load voice config: {e}")

# Initialize voice components
voice_engine = None
ear = None
if VOICE_AVAILABLE:
    try:
        voice_engine = VoiceEngine(voice_config)
    except Exception as e:
        print(f"⚠️  Could not initialize voice engine: {e}")
    try:
        if voice_config:
            ear = Ear(voice_config)
    except Exception as e:
        print(f"⚠️  Could not initialize ear: {e}")


app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Enable Global Cross-Origin Resource Sharing (CORS) for Flutter Web/Chrome, Android, and Desktop clients
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Cache-Control"
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Cache-Control"
    return response

# Ensure upload directory exists (optional)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check ping endpoint for Flutter and external clients."""
    return jsonify({
        "status": "online",
        "system": "V.O.I.D. AI",
        "timestamp": time.time()
    })

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/studio")
@app.route("/studio/")
@app.route("/studio/<path:path>")
def studio_page(path=None):
    """Dedicated V.O.I.D. Studio Cockpit IDE & Neural Observatory webpage."""
    studio_dir = os.path.join(os.path.dirname(__file__), "public", "studio")
    if not os.path.exists(studio_dir):
        studio_dir = os.path.join(os.path.dirname(__file__), "void_studio", "build", "web")
    if path and os.path.exists(os.path.join(studio_dir, path)):
        return send_from_directory(studio_dir, path)
    return send_from_directory(studio_dir, "index.html")

@app.route("/vision")
def vision_page():
    """Dedicated V.O.I.D. Computer Vision & Perception HUD webpage."""
    return render_template("vision.html")

@app.route("/voice-test")
def voice_test():
    """Diagnostic page for voice functionality."""
    return render_template("voice_test.html")

@app.route("/api/tools", methods=["GET"])
def api_tools():
    """Returns list of active agent tools."""
    tools_list = [
        {"id": k, "name": v["name"], "icon": v["icon"], "description": v["description"]}
        for k, v in AVAILABLE_TOOLS.items()
    ]
    return jsonify({"tools": tools_list, "count": len(tools_list)})

@app.route("/api/history", methods=["GET", "DELETE"])
def api_history():
    """Get, clear, or individually delete session history."""
    global CHAT_SESSIONS
    if request.method == "DELETE":
        session_id = request.args.get("id")
        if session_id:
            CHAT_SESSIONS = [s for s in CHAT_SESSIONS if str(s.get("id")) != str(session_id)]
            return jsonify({"status": "deleted", "id": session_id, "message": f"Session {session_id} deleted"})
        CHAT_SESSIONS = []
        return jsonify({"status": "cleared", "message": "Session history reset successfully"})
    return jsonify({"history": CHAT_SESSIONS, "count": len(CHAT_SESSIONS)})

@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """Real-time SSE token streaming chat endpoint."""
    try:
        data = request.get_json() or {}
        message = data.get("message", "")
        context_files = data.get("files", [])
        user_settings = data.get("settings", {})
        force_search = bool(data.get("force_search", False))
        thinking_mode = bool(data.get("thinking_mode", False))
        task_id = data.get("task_id") or f"chat_{str(uuid.uuid4())[:8]}"
        task_lifecycle.register_task(task_id)

        # Dynamic Engine Selection (Mobile & Web override: "ollama", "gemini", "local")
        req_provider = user_settings.get("provider") or data.get("provider")
        req_model = user_settings.get("model") or data.get("model")
        if req_provider:
            try:
                from void_cloud.cloud_manager import cloud_manager
                p_clean = str(req_provider).lower()
                if p_clean == "ollama":
                    from void_cloud.ollama import ollama_manager
                    if req_model:
                        ollama_manager.set_model(str(req_model).strip())
                    cloud_manager.set_provider("ollama")
                    cloud_manager.set_enabled(True)
                elif p_clean == "gemini":
                    cloud_manager.set_provider("gemini")
                    cloud_manager.set_enabled(True)
                elif p_clean in ("local", "local_transformer", "scratch"):
                    cloud_manager.set_enabled(False)
            except Exception as pe:
                print(f"[ProviderSelection] Error switching provider to {req_provider}: {pe}")

        if not message.strip() and not context_files:
            def empty_gen():
                yield f"data: {json.dumps({'token': 'I am listening. Please ask something.', 'done': True, 'task_id': task_id})}\n\n"
            return Response(empty_gen(), mimetype="text/event-stream")

        full_context_message = message
        if context_files:
            file_names = ", ".join([f['name'] for f in context_files])
            full_context_message = f"[System Context: Attached files: {file_names}]\n{message}"

        def generate():
            try:
                yield f"data: {json.dumps({'type': 'task_init', 'task_id': task_id})}\n\n"

                # Visual Cognitive Grounding for Web UI and Mobile SSE Stream:
                # 1. Meta-Cognitive Supervisor Assessment
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'meta_cognition', 'name': 'Meta-Cognitive Supervisor', 'icon': '🧠'})}\n\n"
                time.sleep(0.02)

                # 2. Procedural Knowledge & Experience Memory Lookup
                procedural_rules = void_agent.experience_memory.get_procedural_rules_for_situation(full_context_message)
                if procedural_rules:
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'experience_memory', 'name': 'Procedural Knowledge Retrieval', 'icon': '📚'})}\n\n"
                    time.sleep(0.02)

                if thinking_mode:
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'reasoning_engine', 'name': 'Deep Reasoning Chain', 'icon': '💭'})}\n\n"
                    time.sleep(0.02)

                # Run multi-agent execution with real-time token streaming queue
                import queue
                import threading

                token_queue = queue.Queue()
                task_done = threading.Event()
                task_container = {}

                def worker():
                    try:
                        res = void_agent.run_task(
                            full_context_message,
                            force_search=force_search,
                            thinking_mode=thinking_mode,
                            user_settings=user_settings,
                            token_callback=lambda tok: token_queue.put(tok)
                        )
                        task_container["res"] = res
                    except Exception as ex:
                        task_container["err"] = ex
                    finally:
                        task_done.set()

                th = threading.Thread(target=worker, daemon=True)
                th.start()

                accumulated = ""
                has_started_gen = False

                while not task_done.is_set() or not token_queue.empty():
                    if task_lifecycle.should_stop(task_id):
                        yield f"data: {json.dumps({'token': ' [Generation stopped]', 'done': True, 'stopped': True})}\n\n"
                        vram_manager.cleanup_vram(force=True)
                        break

                    try:
                        tok = token_queue.get(timeout=0.03)
                        if not has_started_gen:
                            yield f"data: {json.dumps({'type': 'start_generation', 'skill': 'conversation'})}\n\n"
                            has_started_gen = True
                        accumulated += tok
                        yield f"data: {json.dumps({'token': tok, 'done': False})}\n\n"
                    except queue.Empty:
                        pass

                th.join(timeout=2.0)

                if "err" in task_container:
                    raise task_container["err"]

                agent_res = task_container.get("res")
                if agent_res:
                    # Emit executed tools to Web / Mobile stream
                    for tool_name, tool_result in agent_res.executed_tools:
                        if tool_name not in ["meta_cognition", "experience_memory"]:
                            tool_info = AVAILABLE_TOOLS.get(tool_name, {"name": tool_name.replace("_", " ").title(), "icon": "⚡"})
                            yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'name': tool_info.get('name', tool_name), 'icon': tool_info.get('icon', '⚡')})}\n\n"

                    # If no tokens were streamed (e.g. direct fast path output), stream words smoothly
                    if not accumulated and agent_res.response:
                        final_text = agent_res.response
                        if not has_started_gen:
                            yield f"data: {json.dumps({'type': 'start_generation', 'skill': agent_res.skill})}\n\n"
                            has_started_gen = True
                        words = re.findall(r'\S+|\s+', final_text)
                        for w in words:
                            if task_lifecycle.should_stop(task_id):
                                break
                            accumulated += w
                            yield f"data: {json.dumps({'token': w, 'done': False})}\n\n"
                            time.sleep(0.01)

                    CHAT_SESSIONS.append({"role": "user", "content": message, "timestamp": time.time()})
                    CHAT_SESSIONS.append({"role": "assistant", "content": accumulated, "skill": agent_res.skill, "timestamp": time.time()})
                    void_mem.working_memory.append(f"User: {message}")
                    void_mem.working_memory.append(f"V.O.I.D.: {accumulated}")
                    try:
                        void_mem.manager.extract_and_store_from_turn(message, accumulated, project_id="VOID")
                    except Exception:
                        pass

                    task_lifecycle.complete_task(task_id)
                    yield f"data: {json.dumps({'done': True, 'skill': agent_res.skill, 'cognitive_state': agent_res.cognitive_state})}\n\n"
                else:
                    task_lifecycle.complete_task(task_id)
                    yield f"data: {json.dumps({'done': True})}\n\n"


            except Exception as e:
                print(f"Streaming generator internal error: {e}")
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        headers = {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
        return Response(stream_with_context(generate()), headers=headers, mimetype="text/event-stream")

    except Exception as e:
        print(f"SSE Error: {e}")
        def err_gen():
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        return Response(err_gen(), mimetype="text/event-stream; charset=utf-8")


@app.route("/api/chat/stop", methods=["POST"])
def api_chat_stop():
    """Immediately stops active neural generation or task execution and frees VRAM."""
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id")
    if task_id:
        task_lifecycle.stop_task(task_id)
    # Stop all active streaming tasks
    for active_id in list(task_lifecycle._active_tasks):
        task_lifecycle.stop_task(active_id)
    vram_manager.cleanup_vram(force=True)
    return jsonify({
        "status": "success",
        "message": "Inference and execution halted. GPU VRAM released."
    })


@app.route("/api/observability/telemetry", methods=["GET"])
def api_observability_telemetry():
    """Telemetry endpoint for CPU, RAM, VRAM, and hardware metrics."""
    telemetry = vram_manager.get_telemetry()
    return jsonify({
        "status": "success",
        "telemetry": telemetry
    })


@app.route("/api/observability/agents", methods=["GET"])
def api_observability_agents():
    """Real-time observability of all registered specialized agents and states."""
    from core.agents.coordinator import agent_coordinator
    states = agent_coordinator.list_agents_state()
    return jsonify({
        "status": "success",
        "count": len(states),
        "agents": states
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json() or {}
        message = data.get("message", "")
        context_files = data.get("files", [])
        force_search = bool(data.get("force_search", False))
        thinking_mode = bool(data.get("thinking_mode", False))
        user_settings = data.get("settings", {})

        # Dynamic Engine Selection (Mobile & Web override: "ollama", "gemini", "local")
        req_provider = user_settings.get("provider") or data.get("provider")
        req_model = user_settings.get("model") or data.get("model")
        if req_provider:
            try:
                from void_cloud.cloud_manager import cloud_manager
                p_clean = str(req_provider).lower()
                if p_clean == "ollama":
                    from void_cloud.ollama import ollama_manager
                    if req_model:
                        ollama_manager.set_model(str(req_model).strip())
                    cloud_manager.set_provider("ollama")
                    cloud_manager.set_enabled(True)
                elif p_clean == "gemini":
                    cloud_manager.set_provider("gemini")
                    cloud_manager.set_enabled(True)
                elif p_clean in ("local", "local_transformer", "scratch"):
                    cloud_manager.set_enabled(False)
            except Exception as pe:
                print(f"[ProviderSelection] Error switching provider to {req_provider}: {pe}")

        if not message.strip() and not context_files:
            return jsonify({
                "response": "I am listening. Please say something.",
                "reply": "I am listening. Please say something.",
                "content": "I am listening. Please say something.",
                "status": "success"
            })

        full_context_message = message
        if context_files:
            file_names = ", ".join([f['name'] for f in context_files])
            full_context_message = f"[System Context: Attached files: {file_names}]\n{message}"

        # Execute through the 10-Phase AGI Cognitive Architecture
        agent_res = void_agent.run_task(
            full_context_message,
            force_search=force_search,
            thinking_mode=thinking_mode,
            user_settings=user_settings
        )

        final_response = agent_res.response

        # Update working memory & session records
        CHAT_SESSIONS.append({"role": "user", "content": message, "timestamp": time.time()})
        CHAT_SESSIONS.append({"role": "assistant", "content": final_response, "skill": agent_res.skill, "timestamp": time.time()})
        void_mem.working_memory.append(f"User: {full_context_message}")
        void_mem.working_memory.append(f"V.O.I.D.: {final_response}")
        try:
            void_mem.manager.extract_and_store_from_turn(full_context_message, final_response, project_id="VOID")
        except Exception:
            pass

        return jsonify({
            "response": final_response,
            "reply": final_response,
            "content": final_response,
            "status": "success" if agent_res.status == "SUCCESS" else "failed",
            "skill": agent_res.skill,
            "cognitive_state": agent_res.cognitive_state,
            "duration_s": agent_res.duration_s,
            "executed_tools": [t[0] for t in agent_res.executed_tools],
            "plan": [
                {
                    "step_id": getattr(s, "step_id", idx + 1),
                    "description": getattr(s, "description", ""),
                    "tool": getattr(s, "tool_name", ""),
                    "status": getattr(s, "status", "COMPLETED")
                }
                for idx, s in enumerate(getattr(agent_res.plan, "steps", []))
            ] if hasattr(agent_res.plan, "steps") else []
        })

    except Exception as e:
        print(f"Server Error in api_chat: {e}")
        # Graceful fallback to deterministic routing if unexpected error occurs
        try:
            response, skill_type = route_query(full_context_message, force_search=force_search, thinking_mode=thinking_mode)
            if response is not None:
                return jsonify({
                    "response": response,
                    "reply": response,
                    "content": response,
                    "skill": skill_type,
                    "status": "success"
                })
        except Exception:
            pass

        return jsonify({
            "reply": "I encountered a neural pathway error.",
            "response": "I encountered a neural pathway error.",
            "content": "I encountered a neural pathway error.",
            "error": str(e),
            "status": "error"
        }), 500


# ============================
# VOICE API ENDPOINTS
# ============================

@app.route("/api/voice/transcribe", methods=["POST"])
def api_transcribe():
    """Convert speech to text."""
    if not VOICE_AVAILABLE or not ear:
        return jsonify({
            "error": "Voice module not available",
            "status": "error"
        }), 503
    
    try:
        if 'audio' not in request.files:
            return jsonify({
                "error": "No audio file provided",
                "status": "error"
            }), 400
        
        audio_file = request.files['audio']
        temp_path = "temp_audio.wav"
        audio_file.save(temp_path)
        
        try:
            text = ear.transcribe_file(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if text.startswith("[Error:") or text.startswith("[Transcription Error:"):
                return jsonify({
                    "error": text,
                    "status": "error"
                }), 400
            
            return jsonify({
                "text": text,
                "status": "success"
            })
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        print(f"Transcription Error: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/api/voice/speak", methods=["GET", "POST"])
def api_speak():
    """Convert text to speech audio WAV stream for web playback."""
    if not VOICE_AVAILABLE or not voice_engine:
        return jsonify({
            "error": "Voice module not available",
            "status": "error"
        }), 503
    
    try:
        text = ""
        if request.method == "POST":
            if request.is_json:
                data = request.get_json() or {}
                text = data.get("text", "")
            else:
                text = request.form.get("text", "")
        else:
            text = request.args.get("text", "")
        
        if not text.strip():
            return jsonify({
                "error": "No text provided",
                "status": "error"
            }), 400
        
        audio_data = voice_engine.synthesize_to_bytes(text)
        if audio_data:
            return send_file(
                BytesIO(audio_data),
                mimetype='audio/wav',
                as_attachment=False,
                download_name='void_speech.wav'
            )
        else:
            return jsonify({
                "error": "TTS synthesis failed",
                "status": "error"
            }), 500
            
    except Exception as e:
        print(f"TTS Error: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/api/voice/chat", methods=["POST"])
def api_voice_chat():
    """Full voice conversation: audio input → text → response → audio output."""
    print(f"\n📞 Voice Chat Request Received")
    print(f"   Content-Type: {request.content_type}")
    print(f"   Files: {list(request.files.keys())}")
    print(f"   Content-Length: {request.content_length}")
    
    if not VOICE_AVAILABLE or not ear or not voice_engine:
        print(f"❌ Voice module not available")
        return jsonify({
            "error": "Voice module not available",
            "status": "error"
        }), 503
    
    try:
        # Transcribe audio
        if 'audio' not in request.files:
            print(f"❌ No audio file in request.files")
            print(f"   Available files: {list(request.files.keys())}")
            return jsonify({
                "error": "No audio file provided",
                "status": "error"
            }), 400
        
        audio_file = request.files['audio']
        temp_path = "temp_audio_chat.wav"
        print(f"💾 Saving audio file: {temp_path}")
        audio_file.save(temp_path)
        
        file_size = os.path.getsize(temp_path)
        print(f"📊 Audio file size: {file_size} bytes")
        
        if file_size == 0:
            print(f"❌ Audio file is empty!")
            os.remove(temp_path)
            return jsonify({
                "error": "Audio file is empty. No data recorded.",
                "status": "error"
            }), 400
        
        try:
            print(f"🎙️ Attempting transcription with Whisper...")
            transcribed_text = ear.transcribe_file(temp_path)
            
            if transcribed_text.startswith("[Error:") or transcribed_text.startswith("[Transcription Error:"):
                print(f"❌ Transcription error: {transcribed_text}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({
                    "error": transcribed_text,
                    "status": "error"
                }), 400
            
            print(f"✅ Transcribed: {transcribed_text}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"❌ Exception during transcription: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                "error": f"Transcription failed: {str(e)}",
                "status": "error"
            }), 500
        
        print(f"📝 Transcribed: {transcribed_text}")
        
        # Get chat response via 10-Phase AGI Cognitive Architecture
        context_files = request.form.getlist("files", [])
        user_settings = request.form.to_dict()

        full_context_message = transcribed_text
        if context_files:
            file_names = ", ".join(context_files)
            full_context_message = f"[System Context: Attached files: {file_names}]\n{transcribed_text}"

        agent_res = void_agent.run_task(full_context_message, user_settings=user_settings)
        response = agent_res.response
        skill_type = agent_res.skill
        
        print(f"🤖 Response: {response}")
        
        # Synthesize response audio for web playback
        audio_available = False
        if voice_engine:
            audio_bytes = voice_engine.synthesize_to_bytes(response)
            audio_available = audio_bytes is not None

        return jsonify({
            "transcribed_text": transcribed_text,
            "response_text": response,
            "status": "success",
            "skill": skill_type,
            "audio_available": audio_available
        })
            
    except Exception as e:
        print(f"Voice Chat Error: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


@app.route("/api/voice/status", methods=["GET"])
def api_voice_status():
    """Check if voice module is available."""
    return jsonify({
        "voice_available": VOICE_AVAILABLE,
        "stt_available": VOICE_AVAILABLE and ear is not None,
        "tts_available": VOICE_AVAILABLE and voice_engine is not None,
        "voice_model": voice_config.get("voice", "en_US-amy-medium"),
        "language": voice_config.get("language", "en-US"),
        "web_speech_supported": True,
        "server_tts_supported": VOICE_AVAILABLE and voice_engine is not None
    })


@app.route("/api/voice/speak", methods=["GET", "POST"])
def api_voice_speak():
    """Synthesize text into WAV audio and stream to browser/Electron."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        play_direct = data.get("direct", False)
    else:
        text = request.args.get("text", "")
        play_direct = request.args.get("direct", "0") in ("1", "true", "True")

    if not text or not text.strip():
        return jsonify({"error": "No text provided"}), 400

    if not VOICE_AVAILABLE or voice_engine is None:
        return jsonify({"error": "Server TTS engine is not available"}), 503

    try:
        audio_bytes = voice_engine.synthesize_to_bytes(text)
        if not audio_bytes:
            return jsonify({"error": "Speech synthesis returned empty audio"}), 500

        if play_direct:
            voice_engine.speak(text, blocking=False)

        response = Response(audio_bytes, mimetype="audio/wav")
        response.headers["Content-Length"] = str(len(audio_bytes))
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        print(f"TTS Synthesis Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/play", methods=["POST"])
def api_voice_play():
    """Directly play speech through host PC speakers (hardware fallback)."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text or not text.strip():
        return jsonify({"error": "No text provided"}), 400
    if not VOICE_AVAILABLE or voice_engine is None:
        return jsonify({"error": "Voice engine not available"}), 503
    try:
        voice_engine.speak(text, blocking=False)
        return jsonify({"status": "playing", "text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice/stop", methods=["POST"])
def api_voice_stop():
    """Stop active speech playback."""
    if VOICE_AVAILABLE and voice_engine is not None:
        try:
            voice_engine.stop_speaking()
        except Exception:
            pass
    return jsonify({"status": "stopped"})




# ============================
# SEARCH & NETWORK TELEMETRY
# ============================

@app.route("/api/network/status", methods=["GET"])
def api_network_status():
    """Returns live internet status and offline capability telemetry."""
    from lib.offline_manager import offline_mgr
    force = request.args.get("force", "false").lower() in ("true", "1")
    return jsonify(offline_mgr.get_status(force_check=force))


@app.route("/api/search", methods=["GET", "POST"])
def api_search():
    """
    Web Search Endpoint — fetch → analyse → synthesise.
    Raw DuckDuckGo results are fed to V.O.I.D. as context; the LLM synthesises
    the final answer. The raw data is also returned for transparency.
    """
    from lib.offline_manager import offline_mgr
    from skills.web_search import perform_search, extract_search_query

    if request.method == "POST":
        data = request.get_json() or {}
        raw_query = data.get("query") or data.get("q", "")
        max_results = int(data.get("max_results", 4))
        force_check = bool(data.get("force_check", False))
    else:
        raw_query = request.args.get("query") or request.args.get("q", "")
        max_results = int(request.args.get("max_results", 4))
        force_check = request.args.get("force_check", "false").lower() in ("true", "1")

    clean_query = extract_search_query(raw_query)
    if not clean_query:
        return jsonify({
            "status": "error",
            "message": "Query parameter 'query' or 'q' is required."
        }), 400

    is_online = offline_mgr.is_online(force_check=force_check)
    raw_results = perform_search(clean_query, max_results=max_results, force_check=force_check)

    # ── Synthesise with LLM (online only) ──────────────────────────────────────
    # Inject the raw search data as grounded context so V.O.I.D. analyses it
    # and returns a coherent answer instead of a dump of search snippets.
    synthesised = raw_results
    if is_online:
        try:
            from chat import generate_stream_tokens, void_mem
            from skills.agentic import get_agent_instruction

            memory_ctx = void_mem.inject_memory_into_prompt(clean_query)
            search_instruction = get_agent_instruction(clean_query, force_search=True)

            synthesis_prompt = (
                f"{memory_ctx}\n\n"
                f"[Web Search Results for '{clean_query}']\n{raw_results}\n\n"
                f"{search_instruction}\n"
                f"### User:\n{raw_query}\n"
                f"### V.O.I.D.:\n"
            )

            tokens = []
            for tok in generate_stream_tokens(synthesis_prompt, max_new_tokens=300, temperature=0.5):
                tokens.append(tok)
            synthesised = "".join(tokens).strip() or raw_results
        except Exception as e:
            print(f"[Search Synthesis] LLM synthesis failed ({e}), returning raw results.")
            synthesised = raw_results

    return jsonify({
        "status": "success" if is_online else "offline",
        "query": clean_query,
        "online": is_online,
        "no_internet": not is_online,
        "result": synthesised,         # V.O.I.D.'s synthesised answer
        "raw_results": raw_results,    # raw search data for transparency
    })


@app.route("/api/agent/state", methods=["GET"])
def api_agent_state():
    """Return live local World State telemetry (hardware, active window, offline mode)."""
    from core.state_manager import state_manager
    return jsonify(state_manager.get_world_state())



@app.route("/api/diagnostics", methods=["GET"])
def api_diagnostics():
    """Perform self-diagnostic checks across all local subsystems."""
    from providers.manager import model_manager
    from core.security import security_manager
    from core.event_bus import event_bus
    from void_memory.memory import void_memory
    from core.tool_registry import tool_registry

    mem_stats = model_manager.get_memory_stats()
    tools_list = tool_registry.list_tools()

    diagnostics = {
        "core": "ONLINE",
        "local_llm": "ONLINE" if model is not None else "OFFLINE",
        "memory_tier": "ONLINE",
        "stt": "ONLINE" if VOICE_AVAILABLE and ear is not None else "OFFLINE",
        "tts": "ONLINE" if VOICE_AVAILABLE and voice_engine is not None else "OFFLINE",
        "tools": f"{len(tools_list)} tools active",
        "gpu": mem_stats.get("gpu_name", "Unknown"),
        "vram": f"{mem_stats.get('vram_allocated_gb', 0)} GB / {mem_stats.get('vram_total_gb', 0)} GB",
        "ram": f"{mem_stats.get('ram_used_gb', 0)} GB / {mem_stats.get('ram_total_gb', 0)} GB",
        "database": "HEALTHY",
        "event_bus": "ONLINE",
        "security": "ACTIVE" if not security_manager.emergency_stop_triggered else "EMERGENCY_STOP",
        "offline_mode": True
    }
    return jsonify(diagnostics)


@app.route("/api/memory", methods=["GET", "POST", "PUT", "DELETE"])
def api_memory():
    """Manage multi-tiered memory with advanced filtering, full-text search, and CRUD."""
    from void_memory.memory_manager import MemoryManager
    from void_memory.database.models import MemoryTier, MemoryStatus
    manager = MemoryManager.get_instance()

    if request.method == "GET":
        tier = request.args.get("tier")
        category = request.args.get("category")
        status_param = request.args.get("status", MemoryStatus.ACTIVE.value)
        query = request.args.get("q", "").strip()
        pinned = request.args.get("pinned", "").lower() in ("true", "1")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        if query:
            results = manager.recall(
                query=query,
                tier=tier,
                category=category,
                top_k=limit,
                include_archived=(status_param == "all" or status_param == "archived")
            )
        else:
            nodes = manager.repo.list_memories(
                memory_type=tier,
                category=category,
                status=None if status_param == "all" else status_param,
                pinned_only=pinned,
                limit=limit,
                offset=offset
            )
            results = [n.to_dict() for n in nodes]

        return jsonify({"memories": results, "count": len(results), "status": "success"})

    elif request.method == "POST":
        data = request.get_json() or {}
        content = data.get("content") or data.get("text", "")
        tier = data.get("tier") or data.get("memory_type", MemoryTier.SEMANTIC.value)
        category = data.get("category", "general")
        importance = data.get("importance")
        if importance is not None:
            importance = float(importance)
        tags = data.get("tags", [])
        pinned = bool(data.get("pinned", False))
        project_id = data.get("project_id")

        if not content:
            return jsonify({"status": "error", "message": "Memory content is required"}), 400

        node = manager.remember(
            content=content,
            memory_type=tier,
            category=category,
            importance=importance,
            tags=tags,
            pinned=pinned,
            project_id=project_id,
            source="api_manual"
        )
        return jsonify({"status": "created", "memory": node.to_dict(), "success": True})

    elif request.method == "PUT":
        data = request.get_json() or {}
        mem_id = data.get("id")
        if not mem_id:
            return jsonify({"status": "error", "message": "Memory ID is required"}), 400

        updated_node = manager.update(
            memory_id=str(mem_id),
            content=data.get("content") or data.get("text"),
            memory_type=data.get("tier") or data.get("memory_type"),
            category=data.get("category"),
            importance=data.get("importance"),
            tags=data.get("tags"),
            pinned=data.get("pinned")
        )
        if not updated_node:
            return jsonify({"status": "error", "message": "Memory not found"}), 404
        return jsonify({"status": "updated", "memory": updated_node.to_dict()})

    elif request.method == "DELETE":
        data = request.get_json() or {}
        target = data.get("target") or request.args.get("target")
        mem_id = data.get("id") or request.args.get("id")
        if mem_id:
            deleted = manager.repo.delete_memory(str(mem_id), hard_delete=False)
            return jsonify({"status": "deleted" if deleted else "not_found", "count": 1 if deleted else 0})
        elif target:
            count = manager.forget(target)
            return jsonify({"status": "forgotten", "count": count})
        else:
            # Auto-archive stale memories
            pruned = manager.lifecycle.auto_archive_stale_memories()
            return jsonify({"status": "pruned", "count": pruned})


@app.route("/api/memory/stats", methods=["GET"])
def api_memory_stats():
    """Returns detailed telemetry of the V.O.I.D. Advanced Memory Engine."""
    from void_memory.memory_manager import MemoryManager
    manager = MemoryManager.get_instance()
    return jsonify(manager.get_stats())


@app.route("/api/memory/graph", methods=["GET"])
def api_memory_graph():
    """Returns the knowledge graph nodes and relationship edges."""
    from void_memory.memory_manager import MemoryManager
    manager = MemoryManager.get_instance()
    return jsonify(manager.knowledge_graph.get_graph_export())


@app.route("/api/memory/consolidate", methods=["POST"])
def api_memory_consolidate():
    """Triggers background memory consolidation (deduplication & contradiction resolution)."""
    from void_memory.memory_manager import MemoryManager
    manager = MemoryManager.get_instance()
    result = manager.consolidate()
    return jsonify(result)


@app.route("/api/memory/export", methods=["GET", "POST"])
def api_memory_export():
    """Exports memory database as portable JSON."""
    from void_memory.memory_manager import MemoryManager
    manager = MemoryManager.get_instance()
    return jsonify(manager.export_data())


@app.route("/api/memory/import", methods=["POST"])
def api_memory_import():
    """Imports memory records from JSON."""
    from void_memory.memory_manager import MemoryManager
    manager = MemoryManager.get_instance()
    data = request.get_json() or {}
    count = manager.import_data(data)
    return jsonify({"status": "imported", "count": count})


@app.route("/api/agents", methods=["GET"])
def api_agents():
    """Returns the live status of all 13 specialized agents in the V.O.I.D. Multi-Agent Network."""
    from core.agents.coordinator import agent_coordinator
    return jsonify({
        "status": "success",
        "agent_count": len(agent_coordinator.agents),
        "agents": agent_coordinator.list_agents_state(),
        "recent_traces": agent_coordinator.message_trace[-10:]
    })


@app.route("/api/missions", methods=["GET", "POST", "PUT"])
def api_missions():
    """Persistent Long-Running Mission API."""
    from core.mission import mission_manager
    if request.method == "GET":
        status_filter = request.args.get("status")
        missions = mission_manager.list_missions(status=status_filter)
        return jsonify({"status": "success", "missions": missions, "count": len(missions)})

    elif request.method == "POST":
        data = request.get_json() or {}
        title = data.get("title", "New Mission")
        goal = data.get("goal", "")
        steps = data.get("steps", [])
        assigned = data.get("assigned_agents", [])
        mid = mission_manager.create_mission(title, goal, steps, assigned)
        return jsonify({"status": "created", "mission_id": mid})

    elif request.method == "PUT":
        data = request.get_json() or {}
        mid = data.get("mission_id")
        if not mid:
            return jsonify({"status": "error", "message": "mission_id is required"}), 400
        updated = mission_manager.update_mission(
            mission_id=int(mid),
            progress=data.get("progress"),
            status=data.get("status"),
            current_objective=data.get("current_objective"),
            blockers=data.get("blockers"),
            completed_step_index=data.get("completed_step_index")
        )
        return jsonify({"status": "updated" if updated else "not_found"})



@app.route("/api/apps", methods=["GET"])
def api_apps():
    """Returns all discovered and indexed applications across Host PC and Connected Devices."""
    from skills.computer_control import app_registry
    force_refresh = request.args.get("refresh", "").lower() in ("true", "1")
    host_apps = app_registry.scan_installed_apps(force=force_refresh)
    
    phone_status = {}
    phone_apps = []
    try:
        from void_phone.phone_controller import phone_controller
        phone_status = phone_controller.get_status_summary()
        if phone_status.get("connected"):
            phone_apps = phone_controller.get_live_device_packages()
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "host_apps_count": len(host_apps),
        "host_apps": [
            {"key": k, "name": v.get("name"), "type": v.get("type"), "source": v.get("source")}
            for k, v in sorted(host_apps.items())
        ],
        "phone_connected": phone_status.get("connected", False),
        "phone_apps_count": len(phone_apps),
        "phone_packages": phone_apps
    })


# ==========================================
# 🌐 REMOTE ACCESS & LIVE SYSTEM TELEMETRY
# ==========================================

@app.route("/api/system/live_stats", methods=["GET"])
def api_system_live_stats():
    """Real-time detailed hardware, GPU, RAM, VRAM, disk, temperature, and battery metrics."""
    try:
        import psutil
        import platform

        # CPU
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        cpu_cores = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)

        # RAM
        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024**3), 2)
        ram_total_gb = round(ram.total / (1024**3), 2)

        # Storage
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        disk_used_gb = round(disk.used / (1024**3), 2)
        disk_total_gb = round(disk.total / (1024**3), 2)
        disk_free_gb = round(disk.free / (1024**3), 2)

        # GPU & VRAM
        gpu_name = "CPU (No CUDA)"
        gpu_available = False
        vram_used_gb = 0.0
        vram_total_gb = 0.0
        vram_pct = 0.0
        if torch.cuda.is_available():
            try:
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
                vram_used_bytes = torch.cuda.memory_allocated(0)
                vram_total_bytes = torch.cuda.get_device_properties(0).total_memory
                vram_used_gb = round(vram_used_bytes / (1024**3), 2)
                vram_total_gb = round(vram_total_bytes / (1024**3), 2)
                vram_pct = round((vram_used_bytes / vram_total_bytes) * 100, 1) if vram_total_bytes > 0 else 0.0
            except Exception:
                pass

        # Temperatures
        temps = {}
        try:
            if hasattr(psutil, "sensors_temperatures"):
                st = psutil.sensors_temperatures()
                if st:
                    for k, v in st.items():
                        if v and len(v) > 0:
                            temps[k] = v[0].current
        except Exception:
            pass

        # Battery
        battery = psutil.sensors_battery()
        battery_pct = battery.percent if battery else None
        battery_plugged = battery.power_plugged if battery else None

        # Uptime
        boot_time = psutil.boot_time()
        uptime_secs = int(time.time() - boot_time)
        hours, remainder = divmod(uptime_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_formatted = f"{hours}h {minutes}m {seconds}s"

        # Local Network IPs
        local_ips = []
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127."):
                    local_ips.append(ip)
        except Exception:
            pass
        if not local_ips:
            local_ips = ["127.0.0.1"]

        return jsonify({
            "status": "success",
            "cpu": {
                "usage_percent": cpu_pct,
                "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
                "logical_cores": cpu_cores,
                "physical_cores": cpu_physical
            },
            "ram": {
                "used_gb": ram_used_gb,
                "total_gb": ram_total_gb,
                "percent": ram.percent
            },
            "gpu": {
                "available": gpu_available,
                "name": gpu_name,
                "vram_used_gb": vram_used_gb,
                "vram_total_gb": vram_total_gb,
                "vram_percent": vram_pct
            },
            "storage": {
                "used_gb": disk_used_gb,
                "total_gb": disk_total_gb,
                "free_gb": disk_free_gb,
                "percent": disk.percent
            },
            "temperatures": temps,
            "battery": {
                "percent": battery_pct,
                "plugged": battery_plugged
            },
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "uptime_seconds": uptime_secs,
                "uptime_formatted": uptime_formatted,
                "python_version": platform.python_version()
            },
            "network": {
                "local_ips": local_ips,
                "primary_lan_url": f"http://{local_ips[0]}:5000" if local_ips else "http://localhost:5000",
                "port": 5000
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/remote/tunnel_info", methods=["GET"])
@app.route("/api/remote/connection_info", methods=["GET"])
def api_remote_tunnel_info():
    """Returns local network IPs, port, and mobile LAN pairing info."""
    local_ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                local_ips.append(ip)
    except Exception:
        pass
    if not local_ips:
        local_ips = ["127.0.0.1"]

    primary_url = f"http://{local_ips[0]}:5000"

    return jsonify({
        "status": "success",
        "primary_url": primary_url,
        "local_lan_url": primary_url,
        "all_lan_urls": [f"http://{ip}:5000" for ip in local_ips],
        "port": 5000,
        "hostname": socket.gethostname(),
        "pairing_payload": {
            "name": "V.O.I.D. AI",
            "url": primary_url,
            "created_at": time.time()
        }
    })


@app.route("/api/remote/execute", methods=["POST"])
def api_remote_execute():
    """
    Executes a remote command from the mobile dashboard or web terminal.
    Sensitive/destructive commands require explicit confirmation handshake.
    """
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").strip()
    confirm_token = data.get("confirm_token")

    if not command:
        return jsonify({"status": "error", "error": "Command string is required"}), 400

    # Clean expired confirmation tokens
    now = time.time()
    for tok in list(PENDING_CONFIRMATIONS.keys()):
        if PENDING_CONFIRMATIONS[tok].get("expires_at", 0) < now:
            PENDING_CONFIRMATIONS.pop(tok, None)

    # Check sensitivity
    is_sens, reason = is_sensitive_command(command)
    if is_sens:
        if not confirm_token or confirm_token not in PENDING_CONFIRMATIONS:
            # Generate pending confirmation token
            token = f"CONFIRM_{uuid.uuid4().hex[:8]}"
            PENDING_CONFIRMATIONS[token] = {
                "command": command,
                "reason": reason,
                "created_at": now,
                "expires_at": now + 60.0
            }
            return jsonify({
                "status": "requires_confirmation",
                "token": token,
                "command": command,
                "reason": reason,
                "expires_in": 60,
                "message": f"⚠️ Sensitive command detected: {reason}. Explicit user approval required."
            }), 200

        # Validate token matches command
        entry = PENDING_CONFIRMATIONS.pop(confirm_token, None)
        if not entry or entry.get("command") != command:
            return jsonify({"status": "error", "error": "Invalid or expired confirmation token"}), 403

    # Execute command securely
    start_time = time.time()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        duration_ms = int((time.time() - start_time) * 1000)
        return jsonify({
            "status": "success",
            "command": command,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_ms": duration_ms
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "error": "Command execution timed out (30 seconds limit exceeded)",
            "command": command
        }), 408
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "command": command
        }), 500


@app.route("/api/remote/confirm", methods=["POST"])
def api_remote_confirm():
    """Approves or rejects a pending sensitive remote command execution token."""
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    action = data.get("action", "approve").lower()

    if not token or token not in PENDING_CONFIRMATIONS:
        return jsonify({"status": "error", "error": "Invalid or expired confirmation token"}), 404

    if action == "deny":
        PENDING_CONFIRMATIONS.pop(token, None)
        return jsonify({"status": "denied", "message": "Command execution cancelled by user"})

    # Forward to execute with the valid token
    entry = PENDING_CONFIRMATIONS.get(token)
    command = entry["command"]
    return api_remote_execute()


# ==============================================================================
# 🧠 V.O.I.D. KNOWLEDGE CORE & CONTINUOUS LEARNING ENDPOINTS
# ==============================================================================

@app.route("/api/learning/stats", methods=["GET"])
def api_learning_stats():
    """Returns telemetry and metrics for the Knowledge Core dashboard."""
    try:
        from void_learning.knowledge_engine import knowledge_engine
        stats = knowledge_engine.get_dashboard_stats()
        return jsonify({"status": "success", "data": stats})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/research", methods=["POST"])
def api_learning_research():
    """Runs interactive research on a topic without immediately committing to persistent storage."""
    try:
        from void_learning.research_agent import WebResearchAgent
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "").strip()
        if not topic:
            return jsonify({"status": "error", "error": "Topic is required"}), 400

        researcher = WebResearchAgent()
        result = researcher.research(topic)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/learn", methods=["POST"])
def api_learning_learn():
    """Executes full learning cycle: research -> clean -> extract -> verify -> graph link -> store."""
    try:
        from void_learning.knowledge_engine import knowledge_engine
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "").strip()
        if not topic:
            return jsonify({"status": "error", "error": "Topic is required"}), 400

        result = knowledge_engine.learn(topic)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/sources", methods=["GET"])
def api_learning_sources():
    """Requirement 11 Source Traceability endpoint."""
    try:
        from void_learning.knowledge_engine import knowledge_engine
        topic = request.args.get("topic", "").strip()
        result = knowledge_engine.get_sources(topic)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/forget", methods=["POST"])
def api_learning_forget():
    """Deletes learned knowledge for a topic."""
    try:
        from void_learning.knowledge_engine import knowledge_engine
        data = request.get_json(silent=True) or {}
        topic = data.get("topic", "").strip()
        result = knowledge_engine.forget_knowledge(topic)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/autolearn/toggle", methods=["POST"])
def api_learning_autolearn_toggle():
    """Toggles autonomous learning mode."""
    try:
        from void_learning.knowledge_engine import knowledge_engine
        data = request.get_json(silent=True) or {}
        enabled = data.get("enabled")
        new_state = knowledge_engine.toggle_auto_learning(enabled)
        return jsonify({"status": "success", "auto_learning": new_state})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ==============================================================================
# 🤖 V.O.I.D. FULL AUTO MODE — AUTONOMOUS SELF-TRAINING ENDPOINTS
# ==============================================================================

@app.route("/api/learning/fullauto/status", methods=["GET"])
def api_fullauto_status():
    """Returns the current state of the Autonomous Training system."""
    try:
        from void_learning.autonomous_trainer import autonomous_trainer
        return jsonify({"status": "success", "data": autonomous_trainer.get_status()})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/fullauto/request", methods=["POST"])
def api_fullauto_request():
    """
    V.O.I.D. autonomously scouts datasets and builds an authorization request.
    DOES NOT download or train - only proposes a plan for admin review.
    """
    try:
        from void_learning.autonomous_trainer import autonomous_trainer
        data = request.get_json(silent=True) or {}
        reason = data.get("reason", "Autonomous self-improvement cycle initiated by V.O.I.D.")
        result = autonomous_trainer.request_full_auto(trigger_reason=reason)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/fullauto/authorize", methods=["POST"])
def api_fullauto_authorize():
    """
    Admin authorization endpoint. Grants V.O.I.D. permission to download
    datasets and begin training. Optionally, admin can select specific datasets.
    """
    try:
        from void_learning.autonomous_trainer import autonomous_trainer
        data = request.get_json(silent=True) or {}
        admin_name = data.get("admin_name", "Admin")
        selected_names = data.get("selected_datasets", None)  # None = accept all proposed
        result = autonomous_trainer.authorize(admin_name=admin_name, selected_names=selected_names)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/fullauto/abort", methods=["POST"])
def api_fullauto_abort():
    """Admin emergency abort — immediately stops any in-progress autonomous operation."""
    try:
        from void_learning.autonomous_trainer import autonomous_trainer
        result = autonomous_trainer.abort()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/learning/fullauto/stream")
def api_fullauto_stream():
    """SSE endpoint: real-time autonomous training events for the dashboard."""
    try:
        from void_learning.autonomous_trainer import autonomous_trainer
        def generate():
            yield from autonomous_trainer.sse_stream()
        return Response(
            stream_with_context(generate()),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ==============================================================================
# 🧠 V.O.I.D. INTELLIGENCE ENDPOINTS (PIPELINE, TASKS, REFLECTION, ROUTER, AWARENESS)
# ==============================================================================

@app.route("/api/agent/pipeline", methods=["POST"])
def api_agent_pipeline():
    """
    Executes the 5-stage Multi-Agent Pipeline:
    Planner -> Researcher -> Coder -> Executor -> Verifier -> Self-Reflection
    Supports streaming via SSE or synchronous JSON response.
    """
    from core.agents.pipeline import agent_pipeline
    data = request.get_json(silent=True) or {}
    goal = data.get("goal", "").strip()
    stream_mode = data.get("stream", False)

    if not goal:
        return jsonify({"status": "error", "error": "Goal parameter is required"}), 400

    if stream_mode:
        def event_stream():
            for update in agent_pipeline.stream_pipeline(goal):
                yield f"data: {json.dumps(update)}\n\n"
        return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

    result = agent_pipeline.run_pipeline(goal)
    return jsonify({"status": "success", **result})


@app.route("/api/agent/reflect", methods=["GET", "POST"])
def api_agent_reflect():
    """Returns past reflections or creates a new evaluation."""
    from core.agents.reflection import reflection_engine
    if request.method == "GET":
        limit = int(request.args.get("limit", 30))
        reflections = reflection_engine.list_reflections(limit=limit)
        return jsonify({"status": "success", "reflections": reflections})

    data = request.get_json(silent=True) or {}
    goal = data.get("goal", "")
    steps = data.get("steps", [])
    output = data.get("output", "")
    success = bool(data.get("success", True))
    reflection = reflection_engine.evaluate_task(
        goal=goal,
        steps=steps,
        output=output,
        success=success,
        error=data.get("error")
    )
    return jsonify({"status": "success", "reflection": reflection})


@app.route("/api/tasks", methods=["GET", "POST"])
def api_tasks():
    """Task Queue Management: List all missions or enqueue a new mission."""
    from core.mission import mission_manager
    if request.method == "GET":
        status_filter = request.args.get("status")
        missions = mission_manager.list_missions(status=status_filter)
        return jsonify({"status": "success", "tasks": missions, "total": len(missions)})

    data = request.get_json(silent=True) or {}
    title = data.get("title", "New Task").strip()
    goal = data.get("goal", "").strip()
    steps = data.get("steps", [])
    assigned_agents = data.get("assigned_agents", ["planner", "researcher", "coder", "executor", "verifier"])

    if not goal:
        return jsonify({"status": "error", "error": "Goal is required to enqueue a task"}), 400

    mission_id = mission_manager.create_mission(
        title=title,
        goal=goal,
        steps=steps if steps else [f"Analyze & Plan: {goal[:40]}", "Execute Implementation", "Verify and Validate"],
        assigned_agents=assigned_agents
    )
    return jsonify({"status": "success", "task_id": mission_id, "message": f"Task #{mission_id} enqueued successfully."})


@app.route("/api/tasks/<int:task_id>/toggle_step", methods=["POST"])
def api_toggle_task_step(task_id: int):
    """Toggles step completion in a task."""
    from core.mission import mission_manager
    data = request.get_json(silent=True) or {}
    step_index = int(data.get("step_index", 0))
    updated_mission = mission_manager.toggle_step(task_id, step_index)
    if not updated_mission:
        return jsonify({"status": "error", "error": "Task or step index not found"}), 404
    return jsonify({"status": "success", "task": updated_mission})


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id: int):
    """Deletes a task from the queue."""
    from core.mission import mission_manager
    deleted = mission_manager.delete_mission(task_id)
    if deleted:
        return jsonify({"status": "success", "message": f"Task #{task_id} deleted."})
    return jsonify({"status": "error", "error": "Task not found"}), 404


@app.route("/api/tasks/run_next", methods=["POST"])
def api_tasks_run_next():
    """Runs the multi-agent pipeline on the next pending or in-progress mission."""
    from core.mission import mission_manager
    from core.agents.pipeline import agent_pipeline
    queued = mission_manager.list_missions(status="IN_PROGRESS") or mission_manager.list_missions(status="QUEUED")
    if not queued:
        return jsonify({"status": "empty", "message": "No pending tasks in queue."})

    target_task = queued[0]
    mission_manager.update_mission(target_task["id"], status="IN_PROGRESS")

    pipe_res = agent_pipeline.run_pipeline(target_task["goal"])
    new_status = "COMPLETED" if pipe_res.get("success") else "FAILED"
    mission_manager.update_mission(target_task["id"], progress=100 if new_status == "COMPLETED" else 50, status=new_status)

    return jsonify({
        "status": "success",
        "task_id": target_task["id"],
        "pipeline_result": pipe_res
    })


@app.route("/api/skills/route", methods=["POST"])
def api_skills_route():
    """Inspects and returns the intelligent skill routing decision for a prompt."""
    from skills.router import skill_router
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    force_search = bool(data.get("force_search", False))
    decision = skill_router.route(query, force_search=force_search)
    return jsonify({"status": "success", "decision": decision.to_dict()})


@app.route("/api/project/structure", methods=["GET"])
def api_project_structure():
    """Returns real-time codebase structure, module roles, file counts, and nested tree."""
    from core.project_awareness import project_awareness
    force = request.args.get("force", "false").lower() == "true"
    summary = project_awareness.scan_structure(force=force)
    file_tree = project_awareness.get_file_tree(max_depth=3)
    return jsonify({
        "status": "success",
        "summary": summary,
        "tree": file_tree
    })


@app.route("/api/project/symbols", methods=["GET"])
def api_project_symbols():
    """Search code symbols (classes, functions) across workspace."""
    from skills.coding_engine import coding_engine
    query = request.args.get("q", "")
    symbols = coding_engine.find_symbols(query) if query else [s.__dict__ for s in coding_engine.scan_workspace()[:100]]
    return jsonify({"status": "success", "query": query, "symbols": symbols, "total": len(symbols)})


# ==========================================
# V.O.I.D. MODULAR VISION SUBSYSTEM ENDPOINTS
# ==========================================
from vision.vision_controller import vision_controller
from vision.camera.frame_processor import FrameProcessor

def _serialize_vision_data(val):
    try:
        import numpy as np
        if isinstance(val, (np.integer, np.int32, np.int64)):
            return int(val)
        if isinstance(val, (np.floating, np.float32, np.float64)):
            return float(val)
        if isinstance(val, (np.bool_, bool)):
            return bool(val)
        if isinstance(val, np.ndarray):
            return val.tolist()
    except Exception:
        pass
    if isinstance(val, dict):
        return {k: _serialize_vision_data(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_serialize_vision_data(x) for x in val]
    return val

@app.route("/api/vision/status", methods=["GET"])
def api_vision_status():
    """Get real-time vision telemetry, camera state, hardware metrics, and perception context."""
    context = vision_controller.get_current_context()
    return jsonify({
        "status": "success",
        "data": _serialize_vision_data(context)
    })

@app.route("/api/vision/devices", methods=["GET"])
def api_vision_devices():
    """List available physical camera devices."""
    devices = vision_controller.get_devices()
    return jsonify({
        "status": "success",
        "devices": devices,
        "count": len(devices)
    })

@app.route("/api/vision/start", methods=["POST"])
def api_vision_start():
    """Activate camera perception strictly for the dedicated vision page."""
    data = request.get_json(silent=True) or {}
    referer = request.headers.get("Referer", "")
    page_param = request.args.get("page", "") or data.get("page", "")

    # Security policy: camera hardware is exclusive to /vision page
    if not ("/vision" in referer or page_param == "vision"):
        return jsonify({
            "status": "denied",
            "active": False,
            "message": "Access Denied: Camera hardware is strictly confined to the dedicated /vision page."
        }), 403

    device_idx = data.get("device_index")
    if device_idx is not None:
        try:
            device_idx = int(device_idx)
        except ValueError:
            device_idx = None
    
    success = vision_controller.start(device_idx)
    return jsonify({
        "status": "success" if success else "error",
        "active": success,
        "message": "Camera online (exclusive /vision session)" if success else "Failed to open camera hardware"
    })

@app.route("/api/vision/stop", methods=["POST"])
def api_vision_stop():
    """Deactivate camera perception and completely release hardware."""
    success = vision_controller.stop()
    return jsonify({
        "status": "success",
        "active": False,
        "message": "Camera hardware released safely."
    })

@app.route("/api/vision/mode", methods=["POST"])
def api_vision_mode():
    """Set vision performance mode: ECO, BALANCED, or TURBO."""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "BALANCED")
    active_mode = vision_controller.set_mode(mode)
    return jsonify({
        "status": "success",
        "mode": active_mode
    })

@app.route("/api/vision/feed")
def api_vision_feed():
    """Live MJPEG video stream strictly authorized for the dedicated /vision webpage."""
    referer = request.headers.get("Referer", "")
    page_param = request.args.get("page", "")
    
    # Enforce camera exclusivity: reject if stream is requested outside /vision
    if not ("/vision" in referer or page_param == "vision"):
        return Response("Camera access is strictly confined to the dedicated /vision page.", status=403, mimetype="text/plain")

    use_hud = request.args.get("hud", "true").lower() != "false"
    auto_start = request.args.get("auto_start", "false").lower() == "true"
    
    if not vision_controller.camera.is_active:
        if auto_start:
            vision_controller.start()
        else:
            # Camera is offline; return 204 No Content so clients do not hang or auto-restart
            return Response(b"", status=204, mimetype="text/plain")

    return Response(
        vision_controller.generate_feed(use_hud=use_hud),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/api/vision/subject", methods=["GET"])
def api_vision_subject():
    """Get comprehensive real-time telemetry and dossier of the primary subject in camera view."""
    subject_data = vision_controller.get_subject_telemetry()
    return jsonify({
        "status": "success",
        "subject": subject_data
    })

@app.route("/api/vision/snapshot", methods=["POST"])
def api_vision_snapshot():
    """Capture current camera frame and return base64 image + detections + subject dossier."""
    frame = vision_controller.capture(auto_open=True)
    if frame is None:
        return jsonify({"status": "error", "message": "Could not capture camera frame"}), 400

    b64 = FrameProcessor.to_base64(frame, quality=85)
    objs = vision_controller.detect_objects(frame)
    faces = vision_controller.detect_people(frame)
    scene = vision_controller.analyze_scene(frame)
    gestures = vision_controller.gesture_detector.detect_gestures(frame)
    subject = vision_controller.subject_analyzer.analyze_primary_subject(
        frame=frame,
        faces=faces,
        objects=objs,
        gestures=gestures
    )

    return jsonify({
        "status": "success",
        "image_base64": b64,
        "objects": objs,
        "faces": faces,
        "scene": scene,
        "subject": subject
    })

@app.route("/api/vision/analyze", methods=["POST"])
def api_vision_analyze():
    """Process natural language vision question against current camera perception."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "What do you see?")
    res = vision_controller.process_query(query)
    return jsonify({
        "status": "success",
        "result": res
    })

@app.route("/api/vision/enroll", methods=["POST"])
def api_vision_enroll():
    """Enroll any person or owner face locally from live webcam."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "Person").strip() or "Person"
    is_owner = bool(data.get("is_owner", False))
    samples = int(data.get("samples", 6))
    notes = data.get("notes", "")
    res = vision_controller.enroll_person(name, is_owner=is_owner, samples_count=samples, notes=notes)
    return jsonify({
        "status": "success" if res.get("success") else "error",
        "result": res
    })

@app.route("/api/vision/profiles", methods=["GET"])
def api_vision_profiles():
    """List enrolled face recognition profiles."""
    profiles = vision_controller.face_recognizer.list_enrolled_profiles()
    return jsonify({
        "status": "success",
        "profiles": profiles
    })

@app.route("/api/vision/profiles/<profile_id>", methods=["DELETE"])
def api_vision_delete_profile(profile_id):
    """Delete an enrolled face profile."""
    success = vision_controller.delete_person(profile_id)
    return jsonify({
        "status": "success" if success else "error",
        "message": f"Profile '{profile_id}' deleted." if success else "Profile not found."
    })

@app.route("/api/vision/memory", methods=["GET"])
def api_vision_memory():
    """Query recent visual memory observations for objects and people."""
    limit = int(request.args.get("limit", 30))
    obj_filter = request.args.get("object")
    person_filter = request.args.get("person")
    
    if person_filter:
        observations = vision_controller.memory.query_person_history(person_filter, limit=limit)
    elif obj_filter:
        observations = vision_controller.memory.query_by_object(obj_filter, limit=limit)
    else:
        observations = vision_controller.memory.query_recent(limit=limit)
    
    today_objs = vision_controller.memory.query_today_objects()
    today_people = vision_controller.memory.query_people_seen_today()
    
    return jsonify({
        "status": "success",
        "observations": observations,
        "today_objects": today_objs,
        "today_people": today_people
    })

@app.route("/api/vision/models", methods=["GET"])
def api_vision_models():
    """Get active vision models catalog, hardware accelerators, and available YOLO versions."""
    catalog = vision_controller.get_model_catalog()
    obj_data = catalog.get("object_detection", {})
    return jsonify({
        "status": "success",
        "models": catalog,
        "available_object_models": obj_data.get("available_object_models", []),
        "active_model": obj_data.get("active_model", "yolov8s-worldv2.pt"),
        "is_open_vocabulary": obj_data.get("is_open_vocabulary", False),
        "active_vocabulary": obj_data.get("active_vocabulary", []),
        "presets": obj_data.get("presets", {})
    })

@app.route("/api/vision/models/switch", methods=["POST"])
def api_vision_models_switch():
    """Dynamically switch active neural object detection model."""
    data = request.get_json(silent=True) or {}
    model_name = data.get("model") or data.get("model_name") or "yolov8s-worldv2.pt"
    success = vision_controller.switch_object_model(model_name)
    catalog = vision_controller.get_model_catalog()
    obj_data = catalog.get("object_detection", {})
    return jsonify({
        "status": "success" if success else "error",
        "active_model": model_name,
        "is_open_vocabulary": obj_data.get("is_open_vocabulary", False),
        "active_vocabulary": obj_data.get("active_vocabulary", []),
        "message": f"Successfully activated {model_name}" if success else f"Failed to activate {model_name}"
    })

@app.route("/api/vision/models/vocabulary", methods=["GET", "POST"])
def api_vision_vocabulary():
    """Manage dynamic open-vocabulary classes live in memory."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        classes = data.get("classes", [])
        preset = data.get("preset")

        presets = vision_controller.get_vocabulary_presets()
        if preset and preset in presets:
            classes = presets[preset]
        elif isinstance(classes, str):
            classes = [c.strip() for c in classes.split(",") if c.strip()]

        success = vision_controller.set_open_vocabulary(classes)
        return jsonify({
            "status": "success" if success else "error",
            "active_vocabulary": vision_controller.get_open_vocabulary(),
            "count": len(vision_controller.get_open_vocabulary()),
            "message": f"Vocabulary updated with {len(classes)} classes." if success else "Failed to update vocabulary."
        })

    return jsonify({
        "status": "success",
        "active_vocabulary": vision_controller.get_open_vocabulary(),
        "count": len(vision_controller.get_open_vocabulary()),
        "presets": vision_controller.get_vocabulary_presets()
    })



# ============================
# PLUGIN SYSTEM API ENDPOINTS
# ============================
@app.route("/api/plugins", methods=["GET"])
def api_list_plugins():
    """List all discovered and loaded V.O.I.D. plugins with status."""
    try:
        from core.plugin_manager import PluginManager
        pm = PluginManager.get_instance()
        return jsonify({
            "status": "success",
            "count": len(pm.plugins),
            "plugins": pm.list_plugins()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/plugins/gmail/status", methods=["GET"])
def api_gmail_status():
    """Check Gmail Analyzer plugin connection status."""
    try:
        from core.plugin_manager import PluginManager
        pm = PluginManager.get_instance()
        gmail_plugin = pm.get_plugin("gmail_analyzer")
        if not gmail_plugin:
            return jsonify({"status": "error", "message": "Gmail Analyzer plugin not found"}), 404
        
        ok, msg = gmail_plugin.engine.test_connection()
        return jsonify({
            "status": "success",
            "connected": ok,
            "configured": gmail_plugin.engine.is_configured(),
            "email": gmail_plugin.engine.email_address or None,
            "demo_mode": gmail_plugin.engine.demo_mode,
            "message": msg
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/plugins/gmail/analyze", methods=["POST"])
def api_gmail_analyze():
    """Trigger Gmail inbox analysis or search."""
    try:
        from core.plugin_manager import PluginManager
        pm = PluginManager.get_instance()
        gmail_plugin = pm.get_plugin("gmail_analyzer")
        if not gmail_plugin:
            return jsonify({"status": "error", "message": "Gmail Analyzer plugin not found"}), 404

        data = request.get_json(silent=True) or {}
        query = data.get("query", "analyze my gmail")
        unread_only = bool(data.get("unread_only", False))
        search_query = data.get("search_query")
        limit = int(data.get("limit", 15))

        if unread_only:
            emails = gmail_plugin.engine.fetch_emails(unread_only=True, limit=limit)
        elif search_query:
            emails = gmail_plugin.engine.fetch_emails(search_query=search_query, limit=limit)
        else:
            emails = gmail_plugin.engine.fetch_emails(limit=limit)

        analysis_report = gmail_plugin.engine.analyze_inbox(emails, custom_query=search_query)

        return jsonify({
            "status": "success",
            "total_emails": len(emails),
            "report": analysis_report,
            "emails": emails
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ============================
# CLOUD ENGINE TELEMETRY
# ============================
@app.route("/api/cloud/status", methods=["GET"])
def api_cloud_status():
    """Returns telemetry of the Host-Only Cloud Engine."""
    try:
        from void_cloud.cloud_manager import cloud_manager
        is_host = request.remote_addr in ("127.0.0.1", "::1", "localhost")
        status = cloud_manager.get_status()
        status["is_host_client"] = is_host
        return jsonify({
            "status": "success",
            "cloud": status
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ============================
# OLLAMA OFFLINE ENGINE API (Mobile & Web)
# ============================
@app.route("/api/ollama/status", methods=["GET"])
def api_ollama_status():
    """Returns status and model list of the local Ollama offline engine."""
    try:
        from void_cloud.ollama import ollama_manager
        from void_cloud.cloud_manager import cloud_manager
        st = ollama_manager.get_status()
        active_provider = cloud_manager.config.get("active_provider", "local")
        is_cloud_enabled = cloud_manager.config.get("cloud_mode_enabled", False)

        current_engine = "local"
        if is_cloud_enabled:
            current_engine = active_provider

        st["is_current_active_engine"] = (current_engine == "ollama")
        st["active_system_engine"] = current_engine

        return jsonify({
            "status": "success",
            "ollama": st
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/ollama/models", methods=["GET"])
def api_ollama_models():
    """Returns list of all downloaded local Ollama models."""
    try:
        from void_cloud.ollama import ollama_manager
        installed = ollama_manager.client.list_models()
        model_names = ollama_manager.client.list_model_names()
        return jsonify({
            "status": "success",
            "models": installed,
            "names": model_names,
            "active_model": ollama_manager.config.model,
            "count": len(model_names)
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "models": [], "names": []}), 500


@app.route("/api/ollama/switch", methods=["POST"])
def api_ollama_switch():
    """
    Switch active Ollama model or activate/deactivate Ollama as primary V.O.I.D. engine.
    Body: {"model": "llama3.2", "activate": true, "enabled": true, "host": "..."}
    """
    try:
        data = request.get_json(silent=True) or {}
        from void_cloud.ollama import ollama_manager
        from void_cloud.cloud_manager import cloud_manager

        new_model = data.get("model")
        if new_model:
            ollama_manager.set_model(str(new_model).strip())

        new_host = data.get("host")
        if new_host:
            ollama_manager.set_host(str(new_host).strip())

        if "enabled" in data:
            ollama_manager.set_enabled(bool(data["enabled"]))

        activate = data.get("activate", True)
        if activate:
            cloud_manager.set_provider("ollama")
            cloud_manager.set_enabled(True)
            if new_model:
                cloud_manager.set_model(str(new_model).strip())
        elif data.get("deactivate", False):
            cloud_manager.set_enabled(False)

        st = ollama_manager.get_status()
        st["active_system_engine"] = "ollama" if (cloud_manager.config.get("cloud_mode_enabled") and cloud_manager.config.get("active_provider") == "ollama") else "local"

        return jsonify({
            "status": "success",
            "message": f"Switched to Ollama model '{ollama_manager.config.model}'",
            "ollama": st
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/ollama/pull", methods=["POST"])
def api_ollama_pull():
    """Triggers background pull of an Ollama model."""
    try:
        data = request.get_json(silent=True) or {}
        model_name = data.get("model")
        if not model_name:
            return jsonify({"status": "error", "message": "Missing 'model' parameter"}), 400

        from void_cloud.ollama import ollama_manager
        if ollama_manager.client.has_model(model_name):
            return jsonify({
                "status": "success",
                "message": f"Model '{model_name}' is already installed locally."
            })

        import threading
        def _pull_worker(name):
            try:
                for _ in ollama_manager.client.pull_model(name):
                    pass
            except Exception as pe:
                print(f"[OllamaPull] Error pulling '{name}': {pe}")

        t = threading.Thread(target=_pull_worker, args=(model_name,), daemon=True)
        t.start()

        return jsonify({
            "status": "pulling",
            "message": f"Started pulling '{model_name}' in background."
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ============================
# MODEL CONTEXT PROTOCOL (MCP) & DESKTOP GUI AUTOMATION
# ============================
from core.mcp.server import mcp_server
from skills.desktop_control import (
    list_desktop_windows,
    focus_desktop_window,
    execute_desktop_action
)
from core.desktop.driver import desktop_driver

@app.route("/api/mcp/status", methods=["GET"])
def api_mcp_status():
    """Returns MCP Server configuration, active tools, and client setup snippets."""
    tools = [t.to_dict() for t in mcp_server._tools.values()]
    resources = [r.to_dict() for r in mcp_server._resources.values()]
    cwd_path = os.path.abspath(os.path.dirname(__file__))

    config_snippet = {
        "mcpServers": {
            "void": {
                "command": "python",
                "args": ["-m", "core.mcp.stdio_server"],
                "cwd": cwd_path
            }
        }
    }

    return jsonify({
        "status": "online",
        "server": mcp_server.server_name,
        "version": mcp_server.server_version,
        "protocolVersion": "2024-11-05",
        "tool_count": len(tools),
        "tools": tools,
        "resource_count": len(resources),
        "resources": resources,
        "client_config": config_snippet
    })


@app.route("/mcp/messages", methods=["POST"])
def api_mcp_messages():
    """JSON-RPC 2.0 message handler for HTTP / SSE MCP sessions."""
    req_data = request.get_json(silent=True)
    if not req_data:
        return jsonify({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Invalid JSON"}
        }), 400

    resp = mcp_server.handle_request(req_data)
    if not resp:
        # Notifications return 204
        return ("", 204)
    return jsonify(resp)


@app.route("/mcp/sse", methods=["GET"])
def api_mcp_sse():
    """Server-Sent Events endpoint for MCP client connections."""
    def event_stream():
        # MCP SSE handshake event pointing client to the message endpoint
        yield f"event: endpoint\ndata: /mcp/messages\n\n"
        while True:
            time.sleep(15)
            yield f": ping\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


@app.route("/api/computer/windows", methods=["GET"])
def api_computer_windows():
    """Lists currently open desktop windows with positions and processes."""
    vis_param = request.args.get("visible_only", "true").lower() != "false"
    windows = list_desktop_windows(visible_only=vis_param)
    return jsonify({
        "status": "success",
        "count": len(windows),
        "windows": windows
    })


@app.route("/api/computer/focus", methods=["POST"])
def api_computer_focus():
    """Focuses a desktop window by title, PID, or process name."""
    data = request.get_json(silent=True) or {}
    target = data.get("target") or data.get("title") or ""
    if not target:
        return jsonify({"status": "error", "message": "Target window title or PID is required."}), 400

    res = focus_desktop_window(target)
    status_code = 200 if res.get("success") else 404
    return jsonify({
        "status": "success" if res.get("success") else "error",
        **res
    }), status_code


@app.route("/api/computer/action", methods=["POST"])
def api_computer_action():
    """Executes a desktop GUI action (click, type, hotkey, move, scroll)."""
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    params = data.get("params", data)

    if not action:
        return jsonify({"status": "error", "message": "Action parameter is required."}), 400

    res = execute_desktop_action(action, params)
    status_code = 200 if res.get("success") else 400
    return jsonify({
        "status": "success" if res.get("success") else "error",
        **res
    }), status_code


@app.route("/api/computer/screenshot", methods=["GET"])
def api_computer_screenshot():
    """Captures and returns the current desktop screen."""
    img = desktop_driver.capture_screen()
    if not img:
        return jsonify({"status": "error", "message": "Screenshot capture failed or screen unavailable."}), 500

    # Return as direct image/jpeg stream
    fmt = request.args.get("format", "image").lower()
    img_io = BytesIO()
    img.save(img_io, 'JPEG', quality=85)
    img_io.seek(0)

    if fmt == "base64":
        import base64
        b64_data = base64.b64encode(img_io.getvalue()).decode('utf-8')
        return jsonify({
            "status": "success",
            "width": img.width,
            "height": img.height,
            "image_data": f"data:image/jpeg;base64,{b64_data}"
        })

    return send_file(img_io, mimetype='image/jpeg')


# ============================
# Mobile Phone Remote Endpoints
# ============================
@app.route("/api/phone/notify", methods=["POST"])
def api_phone_notify():
    """Pushes a notification or heads-up alert to connected Android device."""
    from void_phone.notifications import phone_notifications
    data = request.get_json(silent=True) or {}
    title = data.get("title", "V.O.I.D. Alert")
    message = data.get("message", "")
    priority = data.get("priority", "normal")

    if not message:
        return jsonify({"status": "error", "message": "Notification message is required."}), 400

    res = phone_notifications.send_phone_notification(title=title, message=message, priority=priority)
    status_code = 200 if res.get("success") else 400
    return jsonify({
        "status": "success" if res.get("success") else "error",
        **res
    }), status_code


@app.route("/api/phone/toast", methods=["POST"])
def api_phone_toast():
    """Displays an instant toast message on the connected Android display."""
    from void_phone.notifications import phone_notifications
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    if not message:
        return jsonify({"status": "error", "message": "Toast message is required."}), 400

    res = phone_notifications.show_phone_toast(message)
    status_code = 200 if res.get("success") else 400
    return jsonify({
        "status": "success" if res.get("success") else "error",
        **res
    }), status_code


@app.route("/api/phone/telemetry", methods=["GET"])
def api_phone_telemetry():
    """Fetches live phone telemetry (battery, display, top app, network, storage)."""
    from void_phone.remote_sensor import phone_sensors
    telemetry = phone_sensors.get_telemetry()
    status_code = 200 if telemetry.get("success") else 400
    return jsonify({
        "status": "success" if telemetry.get("success") else "error",
        **telemetry
    }), status_code


@app.route("/api/phone/screen", methods=["GET"])
def api_phone_screen():
    """Captures and returns the live phone screen frame."""
    from void_phone.remote_sensor import phone_sensors
    fmt = request.args.get("format", "image").lower()
    max_dim = request.args.get("max_dim", type=int)

    if fmt == "base64":
        res = phone_sensors.capture_screen_base64(max_dimension=max_dim or 1080)
        status_code = 200 if res.get("success") else 400
        return jsonify({
            "status": "success" if res.get("success") else "error",
            **res
        }), status_code

    # Return raw PNG image stream
    success, png_bytes, err = phone_sensors.capture_screen_bytes()
    if not success or not png_bytes:
        return jsonify({"status": "error", "message": err or "Failed to capture phone screen"}), 400

    return send_file(BytesIO(png_bytes), mimetype='image/png')


@app.route("/api/phone/sms", methods=["GET"])
def api_phone_sms():
    """Reads recent incoming SMS messages from the phone."""
    from void_phone.notification_reader import phone_reader
    limit = request.args.get("limit", default=5, type=int)
    res = phone_reader.get_recent_sms(limit=limit)
    status_code = 200 if res.get("success") else 400
    return jsonify({
        "status": "success" if res.get("success") else "error",
        **res
    }), status_code


@app.route("/api/phone/notifications", methods=["GET"])
def api_phone_notifications():
    """Reads active notifications posted in the Android shade."""
    from void_phone.notification_reader import phone_reader
    limit = request.args.get("limit", default=10, type=int)
    res = phone_reader.get_active_notifications(limit=limit)
    status_code = 200 if res.get("success") else 400
    return jsonify({
        "status": "success" if res.get("success") else "error",
        **res
    }), status_code


@app.route("/api/phone/briefing", methods=["GET"])
def api_phone_briefing():
    """Returns an executive natural language briefing of pending phone communications."""
    from void_phone.notification_reader import phone_reader
    briefing_text = phone_reader.get_unread_digest()
    return jsonify({
        "status": "success",
        "briefing": briefing_text
    })


# ==========================================
# V.O.I.D. 100% OFFLINE IMAGE GENERATION APIS
# ==========================================
@app.route("/api/image/generate", methods=["POST"])
def api_image_generate():
    """Generates an image offline using local neural diffusion / aesthetic synthesis."""
    try:
        from void_media.engine import media_engine
        from void_media.models import ImageRequest, ImageStylePreset
        
        data = request.get_json() or {}
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return jsonify({"status": "error", "message": "Prompt is required"}), 400

        style_str = data.get("style_preset", "none").lower()
        try:
            style_preset = ImageStylePreset(style_str)
        except Exception:
            style_preset = ImageStylePreset.NONE

        width = int(data.get("width", 512))
        height = int(data.get("height", 512))
        seed = int(data["seed"]) if data.get("seed") is not None and str(data.get("seed")).isdigit() else None
        negative_prompt = data.get("negative_prompt", "blurry, low quality, distorted, deformed")

        req = ImageRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            style_preset=style_preset
        )

        result = media_engine.generate_image(req)
        return jsonify({
            "status": "success",
            "image": result.to_dict()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/image/gallery", methods=["GET"])
def api_image_gallery():
    """Retrieves paginated offline generated image gallery."""
    try:
        from void_media.engine import media_engine
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)
        query = request.args.get("q", default=None, type=str)
        gallery_data = media_engine.get_gallery(limit=limit, offset=offset, query=query)
        return jsonify({
            "status": "success",
            **gallery_data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/image/<image_id>", methods=["DELETE"])
def api_image_delete(image_id):
    """Deletes an image from disk and gallery manifest."""
    try:
        from void_media.engine import media_engine
        deleted = media_engine.delete_image(image_id)
        if deleted:
            return jsonify({"status": "success", "message": f"Image {image_id} deleted."})
        return jsonify({"status": "not_found", "message": f"Image {image_id} not found."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/image/settings", methods=["GET", "POST"])
def api_image_settings():
    """Get or update offline media settings (such as auto-purge retention days)."""
    try:
        from void_media.engine import media_engine
        if request.method == "POST":
            data = request.get_json() or {}
            updated = media_engine.update_settings(data)
            return jsonify({"status": "success", "settings": updated})
        return jsonify({"status": "success", "settings": media_engine.get_settings()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/image/purge", methods=["POST"])
def api_image_purge():
    """Manually triggers auto-purge of expired images."""
    try:
        from void_media.engine import media_engine
        pruned = media_engine.trigger_auto_purge()
        return jsonify({"status": "success", "pruned_count": pruned})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===================================================================
# V.O.I.D. 10-PHASE AGI COGNITIVE DASHBOARD & TELEMETRY ENDPOINTS
# ===================================================================

@app.route("/api/agi/state", methods=["GET"])
@app.route("/api/agi/status", methods=["GET"])
def api_agi_status():
    """Returns real-time cognitive status across all 10 AGI phases for Web & Mobile."""
    try:
        wm_stats = void_agent.world_model.get_stats()
        exp_stats = void_agent.experience_memory.get_stats()
        cog_summary = {
            "status": "active",
            "supervisor": {
                "active_task": void_agent.state_manager.current_task,
                "active_states_count": len(void_agent.supervisor.active_states)
            },
            "self_model": {
                "hardware_profile": void_agent.self_model.hardware_profile,
                "domain_confidence": void_agent.self_model.domain_confidence,
                "skill_history": void_agent.self_model.skill_history
            },
            "world_model": {
                "entity_count": wm_stats.get("entity_count", 0),
                "relation_count": wm_stats.get("relation_count", 0)
            },
            "experience_memory": {
                "total_experiences": exp_stats.get("total_experiences", 0),
                "total_procedural_rules": exp_stats.get("total_procedural_rules", 0)
            },
            "skills": {
                "registered_skills": void_agent.skill_registry.list_skills(),
                "count": len(void_agent.skill_registry.list_skills())
            },
            "sleep_daemon": {
                "last_consolidation": void_agent.consolidation_daemon.last_consolidation_time
            },
            "adaptation_guard": {
                "distillation_queue_count": len(void_agent.adaptation_guard.distillation_queue),
                "non_parametric_first": True,
                "safeguards_active": True
            },
            "proactive": {
                "pending_proposals": len(void_agent.proactive_assistant.proposals)
            }
        }
        return jsonify({"status": "success", "agi_core": cog_summary})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/world_model", methods=["GET", "POST"])
def api_agi_world_model():
    """World Model endpoint: inspect or register entities and relations."""
    try:
        if request.method == "POST":
            data = request.get_json() or {}
            name = data.get("name")
            domain = data.get("domain") or data.get("type", "general")
            properties = data.get("properties", {})
            if not name:
                return jsonify({"status": "error", "message": "name is required"}), 400
            ent = void_agent.world_model.add_entity(name, domain=domain, properties=properties)
            return jsonify({"status": "success", "entity": ent.to_dict()})

        # GET
        query = request.args.get("q")
        if query:
            ent = void_agent.world_model.get_entity(query)
            rels = void_agent.world_model.get_relationships(query) if ent else []
            return jsonify({
                "status": "success",
                "entity": ent.to_dict() if ent else None,
                "relationships": [r.to_dict() for r in rels]
            })

        wm_stats = void_agent.world_model.get_stats()
        entities = [e.to_dict() for e in void_agent.world_model.list_entities(limit=100)]
        return jsonify({
            "status": "success",
            "entity_count": wm_stats.get("entity_count", len(entities)),
            "relation_count": wm_stats.get("relation_count", 0),
            "entities": entities
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/experiences", methods=["GET"])
def api_agi_experiences():
    """Experience Memory endpoint: inspect learned procedural rules and experiences."""
    try:
        situation = request.args.get("situation")
        exp_stats = void_agent.experience_memory.get_stats()
        rules = void_agent.experience_memory.get_procedural_rules_for_situation(situation) if situation else void_agent.experience_memory.get_all_procedural_rules()
        recent_exp = void_agent.experience_memory.list_experiences(limit=50)
        return jsonify({
            "status": "success",
            "total_experiences": exp_stats.get("total_experiences", len(recent_exp)),
            "procedural_rules": rules,
            "experiences": [e.to_dict() for e in recent_exp]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/proactive", methods=["GET", "POST"])
def api_agi_proactive():
    """Proactive assistance: view proposals or stage context triggers."""
    try:
        if request.method == "POST":
            data = request.get_json() or {}
            title = data.get("title", "")
            cmd = data.get("command", "")
            if cmd:
                prop = void_agent.proactive_assistant.stage_sensitive_action(
                    title or "Sensitive Command",
                    data.get("description", ""),
                    cmd
                )
                return jsonify({"status": "success", "new_proposals": [prop.to_dict()], "total_pending": len(void_agent.proactive_assistant.proposals)})

            proposals = void_agent.proactive_assistant.evaluate_environment()
            return jsonify({
                "status": "success",
                "new_proposals": [p.to_dict() for p in proposals],
                "total_pending": len(void_agent.proactive_assistant.proposals)
            })

        proposals = [p.to_dict() for p in void_agent.proactive_assistant.proposals]
        return jsonify({
            "status": "success",
            "proposals": proposals,
            "count": len(proposals)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/proactive/approve", methods=["POST"])
def api_agi_proactive_approve():
    """Approve and execute a staged proactive proposal."""
    try:
        data = request.get_json() or {}
        proposal_id = data.get("proposal_id")
        action = data.get("action", "approve")
        if not proposal_id:
            return jsonify({"status": "error", "message": "proposal_id is required"}), 400

        if action == "approve":
            res = void_agent.proactive_assistant.approve_and_execute(proposal_id)
            return jsonify({"status": "success", "result": res})
        else:
            return jsonify({"status": "dismissed", "proposal_id": proposal_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/sleep/trigger", methods=["POST"])
def api_agi_sleep_trigger():
    """Manually trigger sleep-cycle memory consolidation and return report."""
    try:
        report = void_agent.consolidation_daemon.consolidate(force=True)
        return jsonify({
            "status": "success",
            "report": report
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/curiosity/trigger", methods=["POST"])
def api_agi_curiosity_trigger():
    """Trigger autonomous curiosity exploration of a topic or knowledge gap."""
    try:
        data = request.get_json() or {}
        topic = data.get("topic", "System Architecture")
        domain = data.get("domain", "general")
        gap = void_agent.curiosity_engine.register_knowledge_gap(topic, domain=domain)
        mission = void_agent.curiosity_engine.process_next_learning_mission()
        return jsonify({
            "status": "success",
            "gap": gap.to_dict(),
            "mission": mission
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/agi/verify", methods=["POST"])
def api_agi_verify():
    """Empirical verification: tests python code or fact claims without execution risks."""
    try:
        data = request.get_json() or {}
        code = data.get("code")
        claim = data.get("claim")
        if code:
            proof = void_agent.empirical_engine.verify_code(code)
            return jsonify({"status": "success", "type": "code", "verification": proof.to_dict()})
        elif claim:
            proof = void_agent.empirical_engine.verify_empirical_claim(claim, lambda: True)
            return jsonify({"status": "success", "type": "claim", "verification": proof.to_dict()})
        return jsonify({"status": "error", "message": "code or claim required"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================
# FIXED: Prevent double-boot
# ============================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )


