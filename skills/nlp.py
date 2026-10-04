# skills/nlp.py
import re
import json
import os
from collections import Counter
from datetime import datetime

DATASET_PATH = "data/nlp_dataset.json"

# ---------------------------
# Dataset Save / Load
# ---------------------------

def load_user_dataset():
    """Load or create user dataset."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump({"examples": []}, f, indent=2)
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user_example(input_text, output_text):
    """Save learning example to dataset."""
    dataset = load_user_dataset()
    dataset["examples"].append({"input": input_text, "output": output_text})
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


# ---------------------------
# Language Detection
# ---------------------------

def detect_language(text: str) -> str:
    """Detect language using Unicode ranges."""
    text = text.strip()

    # Malayalam (U+0D00–U+0D7F)
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "Malayalam"
    # Tamil (U+0B80–U+0BFF)
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "Tamil"
    # Hindi / Devanagari (U+0900–U+097F)
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    # Japanese Hiragana/Katakana
    if re.search(r"[\u3040-\u309F\u30A0-\u30FF]", text):
        return "Japanese"
    # Chinese (U+4E00–U+9FFF)
    if re.search(r"[\u4E00-\u9FFF]", text):
        return "Chinese"
    # Arabic (U+0600–U+06FF)
    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic"
    # Russian/Cyrillic (U+0400–U+04FF)
    if re.search(r"[\u0400-\u04FF]", text):
        return "Russian/Cyrillic"

    if re.search(r"[A-Za-z]", text):
        return "English or Latin script"
    
    return "Unknown"


# ---------------------------
# Upgraded Summarizer
# ---------------------------

def summarize(text: str, mode: str = "default") -> str:
    """
    Upgraded summarizer:
    - Keyword extraction
    - Sentence scoring by frequency
    - Multi-sentence summary
    - ELI12 (Explain Like I'm 12)
    """

    # Cleanup
    clean = text.replace("\n", " ").strip()

    # Split into sentences
    sentences = re.split(r"[.!?]", clean)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if not sentences:
        summary = clean[:150]
        save_user_example(text, summary)
        return "Summary: " + summary

    # Token frequency
    words = re.findall(r"\b\w+\b", clean.lower())
    stopwords = {
        "the","a","an","and","or","but","so","because","is","am","are","was","were",
        "to","in","on","at","from","of","for","with","as","that","this","it","be"
    }
    words = [w for w in words if w not in stopwords]
    
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    # Score sentences
    sent_scores = {}
    for s in sentences:
        s_words = re.findall(r"\b\w+\b", s.lower())
        score = sum(freq.get(w, 0) for w in s_words)
        sent_scores[s] = score

    # Pick top sentences
    ranked = sorted(sent_scores.items(), key=lambda x: x[1], reverse=True)
    top = [s[0] for s in ranked[:2]]  # best 2 sentences

    summary = " ".join(top)

    # ELI12 mode
    if mode == "eli12":
        summary = f"This text is mainly about: {summary.lower()}."

    save_user_example(text, "Summary: " + summary)
    return "Summary: " + summary


def summarize_eli12(text: str) -> str:
    """Convenience wrapper for ELI12 (Explain Like I'm 12) mode."""
    return summarize(text, mode="eli12")


# ---------------------------
# Simple NLP Functions
# ---------------------------

def generate_reply(text: str) -> str:
    """Generate language-aware reply."""
    lang = detect_language(text)
    save_user_example(text, f"(auto reply in {lang})")

    replies = {
        "Malayalam": "ഞാൻ മലയാളം മനസ്സിലാക്കുന്നു!",
        "Tamil": "நான் தமிழ் தெரியும்!",
        "Hindi": "मैं हिंदी समझता हूँ!",
        "Japanese": "日本語を理解できます!",
        "Chinese": "我能理解中文!",
        "Arabic": "أنا أفهم العربية!"
    }
    
    return replies.get(lang, f"Detected language: {lang}")


# ---------------------------
# Advanced NLP Class
# ---------------------------

class VOID_NLP:
    """
    Advanced local NLP module for V.O.I.D.
    - deterministic tools (no external libs)
    - multilingual support
    - logs learning examples
    - appends training examples
    """

    def __init__(self,
                 memory_path="nlp_memory.jsonl",
                 dataset_path="nlp_dataset/nlp_train.jsonl"):
        self.memory_path = memory_path
        self.dataset_path = dataset_path
        os.makedirs(os.path.dirname(self.dataset_path) or ".", exist_ok=True)
        open(self.memory_path, "a").close()
        open(self.dataset_path, "a").close()

    def _split_sentences(self, text):
        s = re.split(r'(?<=[.!?])\s+', text.strip())
        return [x.strip() for x in s if x.strip()]

    def sentiment(self, text: str) -> str:
        pos = {"good","great","nice","happy","love","excellent","awesome","amazing"}
        neg = {"bad","sad","angry","terrible","hate","awful","worst","poor"}
        w = set(re.findall(r'\w+', text.lower()))
        score = len(w & pos) - len(w & neg)
        if score > 0:
            return "Sentiment: Positive"
        if score < 0:
            return "Sentiment: Negative"
        return "Sentiment: Neutral"

    def keywords(self, text: str, num: int = 6) -> str:
        words = [w.lower() for w in re.findall(r'\w+', text)]
        stop = {"the","and","is","in","of","to","a","an","for","on","with","that","this"}
        filtered = [w for w in words if w not in stop and len(w) > 2]
        freq = Counter(filtered).most_common(num)
        if not freq:
            return "No significant keywords found."
        return "Keywords: " + ", ".join([w for w,_ in freq])

    def grammar_fix(self, text: str) -> str:
        fixes = {
            r"\bi am\b": "I am",
            r"\bu r\b": "you are",
            r"\bim\b": "I'm",
            r"\bidk\b": "I don't know",
            r"\bdont\b": "don't",
            r"\bdoesnt\b": "doesn't",
            r"\bgonna\b": "going to",
            r"\bwanna\b": "want to"
        }
        out = text
        for pat, rep in fixes.items():
            out = re.sub(pat, rep, out, flags=re.IGNORECASE)
        out = re.sub(r'\s+([,.!?])', r'\1', out)
        out = re.sub(r'\s{2,}', ' ', out)
        return out.strip()

    def extract_entities(self, text: str) -> str:
        ents = set(re.findall(r'\b([A-Z][a-z]{1,}[A-Za-z0-9_-]*)\b', text))
        caps = set(re.findall(r'\b([A-Z]{2,})\b', text))
        all_ents = list(ents | caps)
        if not all_ents:
            return "No named entities detected."
        return "Entities: " + ", ".join(all_ents)

    def _append_memory(self, user_text: str, nlp_output: str):
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input": user_text,
            "nlp_output": nlp_output
        }
        with open(self.memory_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_dataset(self, user_text: str, nlp_output: str):
        example = {
            "instruction": "Apply NLP processing as requested.",
            "input": user_text,
            "output": nlp_output,
            "language": detect_language(user_text)
        }
        with open(self.dataset_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")

    def run(self, prompt: str) -> str:
        p = prompt.strip()
        pl = p.lower()

        result = None

        # Language Detection
        if "language" in pl or "detect" in pl:
            result = f"Detected language: {detect_language(p)}"

        # Grammar / Correction
        elif "grammar" in pl or "correct" in pl or "fix" in pl:
            result = self.grammar_fix(p)

        # Summarize (with optional ELI12 mode)
        elif "summarize" in pl or "summary" in pl:
            if "eli12" in pl or "simple" in pl or "explain like" in pl:
                result = summarize(p, mode="eli12")
            else:
                result = summarize(p, mode="default")

        # Sentiment / Tone
        elif "sentiment" in pl or "tone" in pl or "feeling" in pl:
            result = self.sentiment(p)

        # Keywords
        elif "keyword" in pl or "extract" in pl:
            result = self.keywords(p)

        # Entities / NER
        elif "entity" in pl or "entities" in pl or "ner" in pl:
            result = self.extract_entities(p)

        else:
            result = "NLP active. Try: 'summarize', 'sentiment', 'keywords', 'detect language', 'grammar fix', or 'extract entities'."

        try:
            self._append_memory(p, result)
            self._append_dataset(p, result)
        except Exception:
            pass

        return result
