"""
void_cloud package
Host-Only Cloud Model Token Generation Engine for V.O.I.D.
Enables streaming inference via Google Gemini 2.0 models with automatic local fallback.
"""
from void_cloud.cloud_manager import CloudManager, cloud_manager

__all__ = ["CloudManager", "cloud_manager"]
