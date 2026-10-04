"""
void_cloud/ollama/client.py
High-Performance Streaming Client for Offline Ollama LLM Engine.
Connects directly to the local Ollama daemon (default http://localhost:11434)
using standard HTTP streams with zero external dependencies.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error
from typing import Generator, Dict, Any, List, Tuple, Optional


class OllamaClient:
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        num_ctx: int = 4096,
        keep_alive: str = "5m",
        timeout: int = 90,
        system_prompt: Optional[str] = None
    ):
        self.host = host.rstrip("/")
        self.model = model.strip()
        self.temperature = float(temperature)
        self.top_p = float(top_p)
        self.top_k = int(top_k)
        self.num_ctx = int(num_ctx)
        self.keep_alive = str(keep_alive)
        self.timeout = int(timeout)
        self.system_prompt = system_prompt

    def is_server_available(self) -> bool:
        """Checks if the local Ollama daemon is currently running and responding."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def try_start_daemon(self) -> bool:
        """
        Attempts to launch the local Ollama daemon if 'ollama' executable is found.
        Returns True if the daemon becomes reachable.
        """
        if self.is_server_available():
            return True

        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            # Check default Windows AppData path
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            candidate = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
            if os.path.exists(candidate):
                ollama_bin = candidate

        if not ollama_bin:
            return False

        try:
            # Launch in background
            if os.name == "nt":
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                subprocess.Popen(
                    [ollama_bin, "serve"],
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(
                    [ollama_bin, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

            # Wait up to 5 seconds for daemon to respond
            for _ in range(10):
                time.sleep(0.5)
                if self.is_server_available():
                    return True
        except Exception as e:
            print(f"[OllamaClient] Could not start daemon: {e}")

        return False

    def list_models(self) -> List[Dict[str, Any]]:
        """Returns a list of all locally pulled and available Ollama models."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("models", [])
        except Exception as e:
            print(f"[OllamaClient] Error fetching local models: {e}")
        return []

    def list_model_names(self) -> List[str]:
        """Returns clean list of model tags (e.g. ['llama3.2:latest', 'mistral:latest'])."""
        models = self.list_models()
        return [m.get("name", "") for m in models if m.get("name")]

    def has_model(self, model_name: Optional[str] = None) -> bool:
        """Verifies if the specified model is installed locally in Ollama."""
        target = (model_name or self.model).lower().strip()
        names = [n.lower() for n in self.list_model_names()]
        # Check exact or prefix match (e.g. 'llama3.2' matches 'llama3.2:latest')
        for name in names:
            if name == target or name.split(":")[0] == target.split(":")[0]:
                return True
        return False

    def test_connection(self) -> Tuple[bool, str]:
        """
        Validates Ollama connection and checks model availability.
        Returns (is_ready, descriptive_status_message).
        """
        if not self.is_server_available():
            started = self.try_start_daemon()
            if not started:
                return (
                    False,
                    f"Ollama daemon is not running at {self.host}. "
                    "Run 'ollama serve' in your terminal or install Ollama from https://ollama.com"
                )

        installed = self.list_model_names()
        if not installed:
            return (
                False,
                f"Ollama server is active at {self.host}, but no models are downloaded yet. "
                f"Run 'ollama pull {self.model}' to download the offline model."
            )

        if not self.has_model(self.model):
            return (
                False,
                f"Configured model '{self.model}' is not installed. "
                f"Available local models: {', '.join(installed)}. "
                f"Run 'ollama pull {self.model}' or switch model."
            )

        # Quick test generation
        try:
            test_gen = self.stream_generate_tokens("Hi", max_tokens=3)
            next(test_gen, None)
            return True, f"Online and ready. Active model: '{self.model}' at {self.host}."
        except Exception as e:
            return False, f"Server responded but failed to generate: {e}"

    def stream_generate_tokens(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """
        Yields tokens one by one as they stream out of the local Ollama model.
        Compatible with V.O.I.D. streaming interfaces.
        """
        sys_p = system_prompt if system_prompt is not None else self.system_prompt
        options: Dict[str, Any] = {
            "temperature": temperature if temperature is not None else self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "num_ctx": self.num_ctx,
        }
        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": options,
            "keep_alive": self.keep_alive
        }
        if sys_p:
            payload["system"] = sys_p

        url = f"{self.host}/api/generate"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue
                    try:
                        chunk = json.loads(line_str)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.host}. "
                f"Is the Ollama service running? (Error: {e.reason})"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama generation error: {e}")

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Generator[str, None, None]:
        """
        Conversational chat stream via /api/chat.
        Accepts list of message dicts: [{"role": "user", "content": "..."}].
        """
        sys_p = system_prompt if system_prompt is not None else self.system_prompt
        chat_messages = []
        if sys_p:
            chat_messages.append({"role": "system", "content": sys_p})
        chat_messages.extend(messages)

        options: Dict[str, Any] = {
            "temperature": temperature if temperature is not None else self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "num_ctx": self.num_ctx,
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "stream": True,
            "options": options,
            "keep_alive": self.keep_alive
        }

        url = f"{self.host}/api/chat"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue
                    try:
                        chunk = json.loads(line_str)
                        msg = chunk.get("message", {})
                        token = msg.get("content", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise RuntimeError(f"Ollama chat error: {e}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Synchronous wrapper collecting all streamed tokens into a complete string."""
        return "".join(self.stream_generate_tokens(prompt, system_prompt=system_prompt))

    def pull_model(self, model_name: str) -> Generator[Dict[str, Any], None, None]:
        """
        Pulls a model from Ollama library, yielding live progress dicts:
        {"status": "downloading", "completed": 12345, "total": 67890}
        """
        payload = {"name": model_name.strip(), "stream": True}
        url = f"{self.host}/api/pull"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue
                    try:
                        yield json.loads(line_str)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise RuntimeError(f"Failed to pull model '{model_name}': {e}")
