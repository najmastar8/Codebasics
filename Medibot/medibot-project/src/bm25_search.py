import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence


class BM25SearchEngine:
	"""Index document chunks for exact-term BM25 retrieval."""

	def __init__(self, bm25_class: Optional[Any] = None) -> None:
		if bm25_class is None:
			try:
				from rank_bm25 import BM25Okapi
			except ImportError as error:
				raise RuntimeError("rank-bm25 is required for keyword search") from error
			self._bm25_class = BM25Okapi
		else:
			self._bm25_class = bm25_class

		self.bm25: Optional[Any] = None
		self.documents: List[Dict] = []

	def index_documents(self, chunks: Sequence[Dict]) -> None:
		"""Build a BM25 index from chunks and assign stable IDs where needed."""
		self.documents = []
		tokenized_documents = []
		seen_ids = set()

		for chunk in chunks:
			if not isinstance(chunk, dict):
				raise TypeError("Each chunk must be a dictionary")
			text = str(chunk.get("text", "")).strip()
			if not text:
				raise ValueError("Each chunk must contain non-empty text")

			indexed_chunk = dict(chunk)
			metadata = dict(chunk.get("metadata", {}))
			chunk_id = (
				chunk.get("chunk_id")
				or metadata.get("chunk_id")
				or self._stable_chunk_id(text, metadata)
			)
			if chunk_id in seen_ids:
				raise ValueError(f"Duplicate chunk ID: {chunk_id}")
			seen_ids.add(chunk_id)
			indexed_chunk["chunk_id"] = str(chunk_id)
			indexed_chunk["text"] = text
			indexed_chunk["metadata"] = metadata
			self.documents.append(indexed_chunk)
			tokenized_documents.append(self._tokenize(text))

		self.bm25 = self._bm25_class(tokenized_documents)

	def search(self, query: str, limit: int = 10) -> List[Dict]:
		"""Return matching chunks with stable IDs and BM25 scores."""
		if self.bm25 is None:
			raise RuntimeError("BM25 index is empty; call index_documents() first")
		if not isinstance(query, str) or not query.strip():
			raise ValueError("query must be a non-empty string")
		if limit < 1:
			raise ValueError("limit must be greater than zero")

		scores = self.bm25.get_scores(self._tokenize(query))
		ranked_indices = sorted(
			range(len(self.documents)),
			key=lambda index: (-float(scores[index]), index),
		)

		results = []
		for index in ranked_indices[:limit]:
			score = float(scores[index])
			if score <= 0:
				continue
			chunk = self.documents[index]
			results.append(
				{
					"chunk_id": chunk["chunk_id"],
					"score": score,
					"text": chunk["text"],
					"metadata": chunk["metadata"],
				}
			)
		return results

	@staticmethod
	def _tokenize(text: str) -> List[str]:
		return re.findall(r"\w+", text.casefold())

	@staticmethod
	def _stable_chunk_id(text: str, metadata: Dict) -> str:
		identity = json.dumps(
			{"text": text, "metadata": metadata},
			sort_keys=True,
			separators=(",", ":"),
			default=str,
		)
		digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
		return f"chunk-{digest}"
