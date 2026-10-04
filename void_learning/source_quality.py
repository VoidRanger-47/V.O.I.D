# void_learning/source_quality.py
"""
Source Quality and Credibility Evaluation System for V.O.I.D.
Categorizes websites into 3 quality tiers:
- Tier 1: Official docs, government, universities, standards bodies, foundational research (weight: 0.95)
- Tier 2: Established technical publications, reputable tech media, recognized educational platforms (weight: 0.75)
- Tier 3: Blogs, forums, community websites, social media (weight: 0.50)
"""

import re
from enum import Enum
from typing import Dict, Any, Tuple
from urllib.parse import urlparse


class SourceTier(str, Enum):
    TIER_1 = "Tier 1: Authoritative / Official"
    TIER_2 = "Tier 2: Established Technical / Reputable"
    TIER_3 = "Tier 3: Community / Blog / Discussion"


TIER_1_DOMAINS = {
    # Official Language & Foundation Docs
    "python.org", "docs.python.org", "w3.org", "ietf.org", "iso.org", "ieee.org",
    "developer.mozilla.org", "khronos.org", "vulkan.org", "rust-lang.org",
    "isocpp.org", "cppreference.com", "open-std.org", "llvm.org", "gcc.gnu.org",
    "kernel.org", "git-scm.com", "sqlite.org", "postgresql.org", "mysql.com",
    "pytorch.org", "tensorflow.org", "huggingface.co", "opencv.org", "docs.opencv.org",
    # Official Cloud & OS Vendor Docs
    "learn.microsoft.com", "docs.microsoft.com", "developer.apple.com", "developer.android.com",
    "cloud.google.com", "aws.amazon.com", "docs.aws.amazon.com", "azure.microsoft.com",
    # Academic & Research
    "arxiv.org", "acm.org", "biorxiv.org", "nature.com", "science.org",
}

TIER_2_DOMAINS = {
    # Established Technical Publications & Reputable Tech Media
    "arstechnica.com", "infoq.com", "realpython.com", "baeldung.com",
    "spectrum.ieee.org", "zdnet.com", "wired.com", "theverge.com",
    "techcrunch.com", "tomshardware.com", "anandtech.com", "geeksforgeeks.org",
    "tutorialspoint.com", "freecodecamp.org", "digitalocean.com", "towardsdatascience.com",
    "distill.pub", "stackabuse.com", "linuxjournal.com", "lwn.net",
    "reuters.com", "bbc.com", "apnews.com"
}

TIER_3_DOMAINS = {
    # Blogs, Forums, Community Q&A
    "reddit.com", "stackoverflow.com", "stackexchange.com", "medium.com",
    "dev.to", "quora.com", "twitter.com", "x.com", "threads.net", "facebook.com",
    "hashnode.dev", "substack.com", "wordpress.com", "blogspot.com",
    "github.com", "gitlab.com"  # General repos or issue trackers are Tier 3 unless proven official doc
}


def evaluate_source_quality(url_or_domain: str) -> Dict[str, Any]:
    """
    Evaluates credibility tier, trust score, and source description for a URL or domain.
    """
    if not url_or_domain:
        return {
            "tier": SourceTier.TIER_3.value,
            "tier_num": 3,
            "trust_score": 0.50,
            "domain": "unknown",
            "source_type": "community_blog",
            "is_authoritative": False
        }

    raw = url_or_domain.strip().lower()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw

    try:
        parsed = urlparse(raw)
        domain = (parsed.hostname or parsed.netloc or "").lower().strip()
    except Exception:
        domain = raw.split("/")[0]

    # Remove standard prefixes
    domain = re.sub(r"^www\.", "", domain)

    # 1. Check Top-Level Domain rules (.gov, .edu are automatically Tier 1)
    if domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".mil"):
        return {
            "tier": SourceTier.TIER_1.value,
            "tier_num": 1,
            "trust_score": 0.98,
            "domain": domain,
            "source_type": "government_or_academic",
            "is_authoritative": True
        }

    # 2. Check explicitly registered Tier 1 domains
    for t1 in TIER_1_DOMAINS:
        if domain == t1 or domain.endswith("." + t1):
            return {
                "tier": SourceTier.TIER_1.value,
                "tier_num": 1,
                "trust_score": 0.95,
                "domain": domain,
                "source_type": "official_documentation",
                "is_authoritative": True
            }

    # 3. Check registered Tier 2 domains
    for t2 in TIER_2_DOMAINS:
        if domain == t2 or domain.endswith("." + t2):
            return {
                "tier": SourceTier.TIER_2.value,
                "tier_num": 2,
                "trust_score": 0.78,
                "domain": domain,
                "source_type": "technical_publication",
                "is_authoritative": False
            }

    # 4. Check registered Tier 3 domains
    for t3 in TIER_3_DOMAINS:
        if domain == t3 or domain.endswith("." + t3):
            return {
                "tier": SourceTier.TIER_3.value,
                "tier_num": 3,
                "trust_score": 0.55,
                "domain": domain,
                "source_type": "community_or_blog",
                "is_authoritative": False
            }

    # 5. Heuristic fallback based on subdomain and path hints
    if "docs." in domain or "documentation" in raw or "/doc/" in raw or "/api/" in raw:
        return {
            "tier": SourceTier.TIER_1.value,
            "tier_num": 1,
            "trust_score": 0.88,
            "domain": domain,
            "source_type": "technical_documentation",
            "is_authoritative": True
        }

    # Default unrecognized domain: Tier 3
    return {
        "tier": SourceTier.TIER_3.value,
        "tier_num": 3,
        "trust_score": 0.60,
        "domain": domain,
        "source_type": "general_webpage",
        "is_authoritative": False
    }
