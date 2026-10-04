import os
from pathlib import Path
from typing import List
import chromadb
from chromadb.config import Settings

# ensure project root is on sys.path so imports like "from pdf_utils import ..." work
import sys
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise RuntimeError(
        "Missing dependency: sentence-transformers. "
        "Install with: python -m pip install --upgrade sentence-transformers chromadb\n"
        f"Original error: {e}"
    )

from pdf_utils import pdf_to_text  # your existing helper

DATA_DIR = Path("data/docs")           # place .txt/.md/.pdf files here
PERSIST_DIR = Path("chroma_db")        # chroma DB folder
COLLECTION_NAME = "knowledge"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast; change if desired

# chunking params
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

def list_files(root: Path) -> List[Path]:
    exts = {".txt", ".md", ".pdf"}
    return [p for p in root.rglob("*") if p.suffix.lower() in exts]

def load_file_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return pdf_to_text(str(path))
    else:
        return path.read_text(encoding="utf-8", errors="ignore")

def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    parts = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + chunk_size, L)
        parts.append(text[start:end].strip())
        if end == L:
            break
        start = max(0, end - overlap)
    return [p for p in parts if p]

def ingest_all(data_dir: Path = DATA_DIR, persist_dir: Path = PERSIST_DIR):
    data_dir.mkdir(parents=True, exist_ok=True)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Chroma client (try persistent; fall back to in-memory if config deprecated)
    try:
        client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=str(persist_dir)))
    except ValueError as e:
        print("Warning: chromadb persistent Settings not supported by this chromadb version.")
        print("Falling back to an in-memory Chroma client. To enable persistence, run 'pip install chroma-migrate' and follow migration docs, or pin chromadb to a compatible version.")
        client = chromadb.Client()

    try:
        existing = [c.name for c in client.list_collections()]
    except Exception:
        existing = []

    if COLLECTION_NAME in existing:
        col = client.get_collection(COLLECTION_NAME)
    else:
        col = client.create_collection(name=COLLECTION_NAME)

    # embedder
    embedder = SentenceTransformer(EMBED_MODEL_NAME)

    docs = list_files(data_dir)
    all_texts, all_metadatas, all_ids = [], [], []

    for doc_path in docs:
        text = load_file_text(doc_path)
        if not text or text.strip() == "":
            continue
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            doc_id = f"{doc_path.stem}_{i}"
            all_texts.append(chunk)
            all_metadatas.append({"source": str(doc_path), "chunk": i})
            all_ids.append(doc_id)

    if not all_texts:
        print("No documents found to ingest in", data_dir)
        return

    # compute embeddings in batches
    embeddings = embedder.encode(all_texts, show_progress_bar=True, convert_to_numpy=True)

    # add to chroma (will append)
    col.add(documents=all_texts, metadatas=all_metadatas, ids=all_ids, embeddings=embeddings.tolist())
    client.persist()
    print(f"Ingested {len(all_texts)} chunks into Chroma collection '{COLLECTION_NAME}' at {persist_dir}")

if __name__ == "__main__":
    ingest_all()