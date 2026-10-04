# void_voice/brain/llm_interface.py
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def get_void_response(user_input: str) -> str:
    """
    Routes voice input through V.O.I.D.'s central autonomous agent.
    Falls back gracefully to local diagnostic response if an exception occurs.
    """
    clean_input = (user_input or "").strip()
    if not clean_input or clean_input == "[inaudible]":
        return "I am listening."

    try:
        from core.agent import agent
        result = agent.run_task(clean_input)
        return result.response
    except Exception as e:
        print(f"⚠️ Agent processing error in voice interface: {e}")
        return f"V.O.I.D. local core encountered an internal routing state: {str(e)}"