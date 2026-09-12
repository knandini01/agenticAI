"""
RAG tools — semantic search over enterprise documents via Qdrant.
Includes prompt injection detection.
Auto-falls back to in-memory Qdrant and fast local vector embeddings.
"""
import os
import sys
import re
import uuid
import hashlib
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import QDRANT_URL, QDRANT_COLLECTION, INJECTION_PATTERNS, DOCS_DIR

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


_client = None
_st_model = None

def _get_embedding(text: str) -> list[float]:
    """Get embedding using local sentence-transformers model or fast deterministic vector fallback."""
    global _st_model
    try:
        if _st_model is None:
            from sentence_transformers import SentenceTransformer
            os.environ["HF_HUB_OFFLINE"] = "1"
            _st_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        return _st_model.encode(text, normalize_embeddings=True).tolist()
    except Exception:
        # Instant 384-dim normalized term-hash embedding (0ms execution, zero network calls)
        words = re.findall(r'\w+', text.lower())
        vec = [0.0] * 384
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % 384
            vec[idx] += 1.0
        norm = (sum(x * x for x in vec) ** 0.5) or 1.0
        return [x / norm for x in vec]


def _seed_in_memory_qdrant(client: QdrantClient):
    """Seed in-memory Qdrant database if external Qdrant server is unavailable."""
    try:
        client.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        if not os.path.exists(DOCS_DIR):
            return

        points = []
        for filename in os.listdir(DOCS_DIR):
            if not filename.endswith(".txt"):
                continue
            filepath = os.path.join(DOCS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            is_adv = filename.startswith("_")
            doc_type = "adversarial" if is_adv else "enterprise_document"

            # chunk document
            words = content.split()
            chunks = []
            chunk_size, overlap = 500, 100
            for i in range(0, len(words), chunk_size - overlap):
                chunk = " ".join(words[i:i + chunk_size])
                if chunk:
                    chunks.append(chunk)

            for chunk in chunks:
                vector = _get_embedding(chunk)
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "filename": filename,
                        "source": filename,
                        "content": chunk,
                        "is_adversarial": is_adv,
                        "doc_type": doc_type
                    }
                ))
        if points:
            client.upsert(collection_name=QDRANT_COLLECTION, points=points)
            print(f"[RAG] Auto-seeded in-memory Qdrant with {len(points)} document chunks.")
    except Exception as e:
        print(f"Warning: Failed to seed in-memory Qdrant: {e}")


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        try:
            client = QdrantClient(url=QDRANT_URL, timeout=1.0)
            client.get_collections()
            _client = client
            print(f"[RAG] Connected to Qdrant at {QDRANT_URL}")
        except Exception:
            print(f"[RAG] External Qdrant unreachable. Falling back to in-memory Qdrant instance.")
            _client = QdrantClient(":memory:")
            _seed_in_memory_qdrant(_client)
    return _client


def detect_prompt_injection(text: str) -> dict[str, Any]:
    """
    Check retrieved text for prompt injection patterns.
    Returns detection result with matched patterns.
    """
    text_lower = text.lower()
    matched = [p for p in INJECTION_PATTERNS if p in text_lower]

    if matched:
        return {
            "injection_detected": True,
            "matched_patterns": matched,
            "severity": "HIGH",
            "action": "CONTENT_ISOLATED",
            "message": f"Prompt injection detected in retrieved content. {len(matched)} pattern(s) matched. Content rejected for agent processing."
        }
    return {
        "injection_detected": False,
        "matched_patterns": [],
        "severity": "NONE",
        "action": "CONTENT_APPROVED",
        "message": "Content passed injection check."
    }


def query(text: str, top_k: int = 5, include_adversarial: bool = True) -> dict[str, Any]:
    """
    Semantic search over enterprise documents.
    Returns relevant chunks with source metadata and injection check results.
    """
    try:
        client = _get_client()
        embedding = _get_embedding(text)

        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=embedding,
                limit=top_k,
                with_payload=True
            )
            results = res.points
        else:
            results = client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=embedding,
                limit=top_k,
                with_payload=True
            )

        chunks = []
        injection_alerts = []

        for hit in results:
            payload = hit.payload or {}
            content = payload.get("content", "")
            source = payload.get("source", payload.get("filename", "unknown"))
            is_adversarial = payload.get("is_adversarial", False)

            # Run injection check on every retrieved chunk
            injection_check = detect_prompt_injection(content)

            if injection_check["injection_detected"]:
                injection_alerts.append({
                    "source": source,
                    "check": injection_check
                })
                # Still include in results but clearly flagged — agent sees the alert
                chunks.append({
                    "source": source,
                    "content": "[CONTENT BLOCKED — PROMPT INJECTION DETECTED]",
                    "relevance_score": round(getattr(hit, 'score', 0.95), 4),
                    "is_adversarial": True,
                    "injection_alert": injection_check,
                    "doc_type": payload.get("doc_type", "unknown")
                })
            else:
                chunks.append({
                    "source": source,
                    "content": content,
                    "relevance_score": round(getattr(hit, 'score', 0.95), 4),
                    "is_adversarial": is_adversarial,
                    "injection_alert": None,
                    "doc_type": payload.get("doc_type", "enterprise_document")
                })

        return {
            "query": text,
            "chunks": chunks,
            "total_results": len(chunks),
            "injection_alerts": injection_alerts,
            "injection_detected": len(injection_alerts) > 0
        }
    except Exception as e:
        print(f"Error in RAG query: {e}")
        return {
            "query": text,
            "chunks": [],
            "total_results": 0,
            "injection_alerts": [],
            "injection_detected": False,
            "error": str(e)
        }


def get_source_quality(source: str) -> float:
    """
    Score source reliability (0.0 – 1.0).
    Internal documents score higher than external sources.
    """
    source_scores = {
        "machine_manual.txt": 0.95,
        "supplier_report.txt": 0.90,
        "engineering_incident_2023.txt": 0.88,
        "quality_policy.txt": 0.92,
        "_adversarial_injection.txt": 0.0,   # Never trust adversarial sources
    }
    return source_scores.get(source, 0.70)
