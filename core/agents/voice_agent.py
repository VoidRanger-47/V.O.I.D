# core/agents/voice_agent.py
import json
import os
from typing import Optional
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel

class VoiceAgent(BaseAgent):
    """
    Dedicated Voice Agent.
    Orchestrates local wake-word detection, offline STT (Faster-Whisper), in-process TTS (Piper), and barge-in.
    """
    def __init__(self):
        super().__init__(
            name="voice_agent",
            role="Handles offline speech recognition, local voice synthesis, and acoustic wake-word sensing",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )
        self.voice_engine = None
        self.ear = None
        self.config = {}
        self.is_ready = True
        self._load_config()

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "void_voice", "config", "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"[WARN] VoiceAgent config error: {e}")

    def get_ear(self):
        """Lazy loads Faster-Whisper only when voice transcription is required."""
        if self.ear is None:
            try:
                from void_voice.stt.transcriber import Ear
                self.ear = Ear(self.config)
            except Exception as e:
                print(f"[WARN] Ear STT unavailable: {e}")
        return self.ear

    def get_voice_engine(self):
        """Lazy loads Piper TTS only when voice playback is required."""
        if self.voice_engine is None:
            try:
                from void_voice.tts.piper_engine import VoiceEngine
                self.voice_engine = VoiceEngine(self.config)
            except Exception as e:
                print(f"[WARN] VoiceEngine TTS unavailable: {e}")
        return self.voice_engine

    def process(self, message: AgentMessage) -> AgentMessage:
        action = message.payload.get("action", "status")

        if action == "speak":
            text = message.payload.get("text", message.goal)
            engine = self.get_voice_engine()
            if engine:
                engine.speak(text)
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="SUCCESS",
                    result=f"Synthesized voice output for: '{text[:50]}...'",
                    payload={"spoken": True}
                )
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                result="Local TTS engine unavailable.",
                error="TTS unavailable"
            )

        elif action == "stop_speech":
            engine = self.get_voice_engine()
            if engine:
                engine.stop_speaking()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result="Audio playback halted (barge-in)."
            )

        else:
            ear = self.get_ear()
            engine = self.get_voice_engine()
            status_info = {
                "stt_available": ear is not None and getattr(ear, "is_ready", True),
                "tts_available": engine is not None,
                "wake_word": self.config.get("wake_word", "hey_void"),
                "voice": self.config.get("voice", "en_US-amy-medium")
            }
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result="Voice subsystem operational (100% Offline).",
                payload=status_info
            )
