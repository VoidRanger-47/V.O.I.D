# void_memory/embedding_provider.py
"""
Strict 100% Offline Embedding Providers for V.O.I.D.
Enforces offline operation: never dials out, never auto-downloads from HuggingFace,
loads only from local disk, and provides a pure-local mathematical fallback.
"""

import os
import sys
import re
import math
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import numpy as np

# STRICT OFFLINE ENFORCEMENT
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EmbeddingProvider(ABC):
    """Abstract interface for all offline embedding providers."""

    @abstractmethod
    def encode(self, text_or_texts: str | List[str]) -> np.ndarray:
        """Compute normalized vector embedding."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return embedding dimension."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier."""
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Loads local SentenceTransformer model strictly from filesystem.
    Never attempts network download.
    """

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "all-MiniLM-L6-v2")
        self.model = None
        self.dim = 384
        self._load_local_model()

    def _load_local_model(self):
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(f"Local model directory not found: {self.model_dir}")

        # Verify key model files exist locally
        required_files = ["config.json", "modules.json"]
        weights_found = any(os.path.exists(os.path.join(self.model_dir, f)) for f in ["model.safetensors", "pytorch_model.bin"])
        if not weights_found:
            raise FileNotFoundError(f"No model weights found in {self.model_dir}")

        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(self.model_dir, local_files_only=True)

    def encode(self, text_or_texts: str | List[str]) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Local model is not initialized.")
        is_single = isinstance(text_or_texts, str)
        inp = [text_or_texts] if is_single else text_or_texts
        vecs = self.model.encode(inp, show_progress_bar=False, normalize_embeddings=True)
        if is_single:
            return np.array(vecs[0], dtype=np.float32)
        return np.array(vecs, dtype=np.float32)

    def get_dimension(self) -> int:
        return self.dim

    def get_provider_name(self) -> str:
        return "local_sentence_transformer (all-MiniLM-L6-v2)"


class LocalFallbackEmbeddingProvider(EmbeddingProvider):
    """
    100% Offline, zero-dependency TF-IDF + Character/Word N-Gram Dense Vectorizer.
    Produces deterministic 384-dimensional normalized dense vectors using hashing trick
    and subword frequency projections.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, text_or_texts: str | List[str]) -> np.ndarray:
        if isinstance(text_or_texts, str):
            return self._encode_single(text_or_texts)
        return np.array([self._encode_single(t) for t in text_or_texts], dtype=np.float32)

    def _encode_single(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        clean = text.lower().strip()
        if not clean:
            return vec

        words = re.findall(r'\b[a-z0-9_]+\b', clean)
        # Word N-grams (1-gram and 2-grams)
        ngrams = list(words)
        for i in range(len(words) - 1):
            ngrams.append(f"{words[i]}_{words[i+1]}")

        # Subword 3-char and 4-char ngrams
        for w in words:
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    ngrams.append(w[i:i+3])
            if len(w) >= 4:
                for i in range(len(w) - 3):
                    ngrams.append(w[i:i+4])

        for gram in ngrams:
            # MD5 hashing to bucket index and sign
            h = int(hashlib.md5(gram.encode('utf-8')).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            # Term weight based on length
            weight = math.log(1.0 + len(gram))
            vec[idx] += sign * weight

        # Non-linear squashing & L2 normalization
        vec = np.tanh(vec)
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec

    def get_dimension(self) -> int:
        return self.dim

    def get_provider_name(self) -> str:
        return "local_fallback_ngram_vectorizer (384-dim deterministic hash)"


class KeywordSearchProvider:
    """
    Keyword frequency and token overlap provider when vectors are bypassed.
    """
    @staticmethod
    def compute_overlap(query: str, target: str) -> float:
        q_words = set(re.findall(r'\w+', query.lower()))
        t_words = set(re.findall(r'\w+', target.lower()))
        if not q_words or not t_words:
            return 0.0
        intersection = q_words & t_words
        if not intersection:
            return 0.0
        # Precision & Recall harmonic mean (F1)
        prec = len(intersection) / len(q_words)
        rec = len(intersection) / len(t_words)
        if prec + rec < 1e-6:
            return 0.0
        return float((2 * prec * rec) / (prec + rec))


_global_embedding_provider: Optional[EmbeddingProvider] = None


def get_offline_embedding_provider() -> EmbeddingProvider:
    """
    Returns the primary local embedding provider if available;
    otherwise gracefully falls back to the deterministic local n-gram vectorizer.
    """
    global _global_embedding_provider
    if _global_embedding_provider is not None:
        return _global_embedding_provider

    # Try loading primary local SentenceTransformer model
    try:
        provider = LocalEmbeddingProvider()
        _global_embedding_provider = provider
        return provider
    except Exception as e:
        print(f"ℹ️ Local neural embedding model notice ({e}). Activating LocalFallbackEmbeddingProvider.")
        provider = LocalFallbackEmbeddingProvider()
        _global_embedding_provider = provider
        return provider
