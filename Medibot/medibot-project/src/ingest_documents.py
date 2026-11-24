import json
import logging
from pathlib import Path
from typing import Dict, List

from src.chunking import HierarchicalChunker
from src.document_parser import MedicineDocumentParser
from src.embeddings import EmbeddingService
from src.rbac_config import get_access_roles_for_collection
from src.vector_store import QdrantVectorStore


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = PROJECT_ROOT / "data" / "documents"
INDEXED_CHUNKS_PATH = PROJECT_ROOT / "data" / "indexed_chunks.json"


def ingest_documents() -> List[Dict]:
    parser = MedicineDocumentParser()
    chunker = HierarchicalChunker(max_chunk_tokens=512)
    embedder = EmbeddingService()
    vector_store = QdrantVectorStore()
    vector_store.init_collection(recreate=True)

    chunks: List[Dict] = []
    for collection_dir in sorted(path for path in DOCUMENT_ROOT.iterdir() if path.is_dir()):
        collection = collection_dir.name
        access_roles = get_access_roles_for_collection(collection)
        for pdf_path in sorted(collection_dir.glob("*.pdf")):
            parsed = parser.parse_pdf(pdf_path)
            if parsed is None:
                continue
            document_chunks = chunker.chunk_markdown(
                parsed["content_markdown"],
                parsed["filename"],
                collection,
                access_roles,
            )
            for chunk in document_chunks:
                chunk["metadata"].update(parsed["metadata"])
            chunks.extend(document_chunks)

    if not chunks:
        raise RuntimeError(f"No parseable PDF chunks found in {DOCUMENT_ROOT}")

    embeddings = embedder.embed_batch([chunk["text"] for chunk in chunks])
    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = vector_store._stable_chunk_id(chunk["text"], chunk["metadata"])
        chunk["chunk_id"] = chunk_id
        chunk["metadata"]["chunk_id"] = chunk_id
        vector_store.add_chunk(
            chunk["text"],
            embedding,
            chunk["metadata"],
            chunk_id=chunk_id,
        )

    INDEXED_CHUNKS_PATH.write_text(
        json.dumps(chunks, indent=2),
        encoding="utf-8",
    )
    logger.info("Indexed %d chunks from %s", len(chunks), DOCUMENT_ROOT)
    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    indexed = ingest_documents()
    print(f"Indexed {len(indexed)} chunks")
