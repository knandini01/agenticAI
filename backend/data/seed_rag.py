"""
Seed Qdrant vector database with enterprise RAG documents.
Run once on startup after Qdrant is available.
"""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import QDRANT_URL, QDRANT_COLLECTION, DOCS_DIR

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


def get_embedding(text: str) -> list[float]:
    """
    Generate text embedding. Uses sentence-transformers for local embedding
    (no API key needed, works offline in Docker).
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        print(f"Warning: sentence-transformers failed: {e}")
        # Fallback: zero vector (should not happen in production)
        return [0.0] * 384


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split document into overlapping chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def seed_rag():
    # Wait for Qdrant to be ready
    client = None
    for attempt in range(10):
        try:
            client = QdrantClient(url=QDRANT_URL)
            client.get_collections()
            print(f"  [OK] Connected to Qdrant at {QDRANT_URL}")
            break
        except Exception as e:
            print(f"  Waiting for Qdrant... attempt {attempt+1}/10 ({e})")
            time.sleep(3)

    if client is None:
        print("ERROR: Could not connect to Qdrant. RAG will be unavailable.")
        return

    # Recreate collection
    try:
        client.delete_collection(QDRANT_COLLECTION)
    except Exception:
        pass

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    # Load and embed all documents
    doc_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]
    points = []
    total_chunks = 0

    for filename in doc_files:
        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_document(content)
        is_adversarial = filename.startswith("_adversarial")

        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "source": filename,
                    "chunk_index": i,
                    "content": chunk,
                    "is_adversarial": is_adversarial,
                    "doc_type": "adversarial_test" if is_adversarial else "enterprise_document"
                }
            )
            points.append(point)
            total_chunks += 1

        print(f"  [OK] {filename}: {len(chunks)} chunks embedded")

    # Upload to Qdrant
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"  [OK] Total: {total_chunks} chunks uploaded to Qdrant collection '{QDRANT_COLLECTION}'")


if __name__ == "__main__":
    print("Seeding Qdrant RAG database...")
    seed_rag()
    print("[OK] RAG database seeded successfully.")
