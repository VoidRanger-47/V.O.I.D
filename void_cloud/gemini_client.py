"""
void_cloud/gemini_client.py
High-Performance Streaming Client for Google Gemini 2.0.
Connects directly via HTTPS Server-Sent Events (SSE) protocol using standard libraries.
"""

import json
import urllib.request
import urllib.error
from typing import Generator, Dict, Any, Tuple, Optional


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash", temperature: float = 0.7, max_tokens: int = 2048, top_p: float = 0.95):
        self.api_key = api_key.strip()
        self.model_name = model_name.strip().replace("models/", "")
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.top_p = float(top_p)

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def get_endpoint_url(self) -> str:
        clean_model = self.model_name.replace("models/", "")
        return f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:streamGenerateContent?alt=sse&key={self.api_key}"

    def test_connection(self) -> Tuple[bool, str]:
        """Tests live API connectivity and key validity with a minimal test prompt."""
        if not self.is_configured():
            return False, "Gemini API key is not configured."

        try:
            clean_model = self.model_name.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 5}
            }
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True, f"Successfully connected to Gemini 2.0 ({self.model_name})."
                return False, f"API returned HTTP status {resp.status}."

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                msg = err_json.get("error", {}).get("message", err_body)
            except Exception:
                msg = err_body
            return False, f"HTTP Error {e.code}: {msg}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def stream_generate_tokens(self, prompt: str) -> Generator[str, None, None]:
        """
        Yields individual text tokens streamed in real time from Gemini 2.0.
        """
        if not self.is_configured():
            raise ValueError("Gemini API key is not configured in void_cloud/config.json.")

        url = self.get_endpoint_url()
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "topP": self.top_p
            }
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                buffer = ""
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace")
                    buffer += line

                    while "\n" in buffer:
                        current_line, buffer = buffer.split("\n", 1)
                        current_line = current_line.strip()

                        if current_line.startswith("data: "):
                            json_str = current_line[6:].strip()
                            if not json_str or json_str == "[DONE]":
                                continue
                            try:
                                chunk = json.loads(json_str)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        text_part = p.get("text", "")
                                        if text_part:
                                            yield text_part
                            except json.JSONDecodeError:
                                continue

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API Error [{e.code}]: {err_body}")
        except Exception as e:
            raise RuntimeError(f"Gemini Streaming Error: {str(e)}")

    def generate_vision_content(self, prompt: str, image_data: Any, mime_type: str = "image/jpeg") -> str:
        """
        Multimodal visual analysis with Google Gemini.
        Accepts raw JPEG/PNG bytes or base64 data string.
        """
        if not self.is_configured():
            raise ValueError("Gemini API key is not configured in void_cloud/config.json.")

        import base64
        if isinstance(image_data, bytes):
            b64_img = base64.b64encode(image_data).decode("utf-8")
        elif isinstance(image_data, str):
            if "base64," in image_data:
                b64_img = image_data.split("base64,", 1)[1]
            else:
                b64_img = image_data.strip()
        else:
            raise ValueError("Invalid image_data format. Expected bytes or base64 string.")

        clean_model = self.model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": b64_img
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": self.max_tokens,
                "topP": self.top_p
            }
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    resp_body = resp.read().decode("utf-8", errors="replace")
                    resp_json = json.loads(resp_body)
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_chunks = [p.get("text", "") for p in parts if "text" in p]
                        return "".join(text_chunks).strip()
                return "Vision analysis could not parse visual response."
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini Vision API Error [{e.code}]: {err_body}")
        except Exception as e:
            raise RuntimeError(f"Gemini Vision Request Failed: {str(e)}")

