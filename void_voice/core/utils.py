# core/utils.py
import os
import numpy as np
from pathlib import Path

def add_metallic_effect(audio_data, intensity=0.3):
    """
    Add a metallic/robotic effect to audio (V.O.I.D. voice signature).
    
    Args:
        audio_data: numpy array of audio samples
        intensity: Effect strength (0.0 to 1.0)
        
    Returns:
        Modified audio array
    """
    try:
        # Simple pitch shift by duplicating samples (creates robotic tone)
        if intensity > 0:
            # Add harmonic distortion
            modified = audio_data.copy().astype(float)
            modified = modified + (intensity * 0.1 * modified ** 2)
            # Clip to prevent overflow
            modified = np.clip(modified, -32768, 32767)
            return modified.astype(np.int16)
        return audio_data
    except Exception as e:
        print(f"Warning: Could not apply metallic effect: {e}")
        return audio_data


def cleanup_temp_files(temp_dir="/tmp"):
    """
    Clean up temporary audio files.
    
    Args:
        temp_dir: Directory to clean (default: /tmp)
    """
    try:
        temp_path = Path(temp_dir)
        void_files = list(temp_path.glob("void_*.wav"))
        
        for f in void_files:
            try:
                f.unlink()
                print(f"Cleaned: {f}")
            except Exception as e:
                print(f"Could not delete {f}: {e}")
    except Exception as e:
        print(f"Cleanup error: {e}")


def ensure_dir(path):
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def load_config_safe(config_path):
    """
    Load JSON config with fallback defaults.
    
    Args:
        config_path: Path to config.json
        
    Returns:
        dict: Config dictionary
    """
    import json
    
    defaults = {
        "wakeword_threshold": 1000,
        "wakeword_buffer": 5,
        "language": "en-US",
        "voice": "en_US-amy-medium",
        "tts_enabled": True,
        "metallic_effect": 0.3
    }
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        # Merge with defaults (config overrides defaults)
        return {**defaults, **config}
    except FileNotFoundError:
        print(f"⚠️  Config not found at {config_path}. Using defaults.")
        return defaults
    except json.JSONDecodeError:
        print(f"⚠️  Config is invalid JSON. Using defaults.")
        return defaults