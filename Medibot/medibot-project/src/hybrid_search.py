from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.rbac_config import validate_role


class HybridSearchEngine:
	"""Combine RBAC-filtered dense and BM25 retrieval with RRF."""

	def __init__(
		self,
		embedding_service: Optional[Any] = None,
		vector_store: Optional[Any] = None,
		bm25_engine: Optional[Any] = None,
	) -> None:
		if embedding_service is None:
			from src.embeddings import EmbeddingService
			embedding_service = EmbeddingService()
		if vector_store is None:
			from src.vector_store import QdrantVectorStore
			vector_store = QdrantVectorStore()
		if bm25_engine is None:
			from src.bm25_search import BM25SearchEngine
			bm25_engine = BM25SearchEngine()

		self.embedding_service = embedding_service
		self.vector_store = vector_store
		self.bm25_engine = bm25_engine

	def setup(self, chunks: Sequence[Dict]) -> None:
		"""Build the sparse index from the same chunks loaded into Qdrant."""
		self.bm25_engine.index_documents(chunks)

	def reciprocal_rank_fusion(
		self,
		dense_results: Sequence[Tuple[str, float]],
		sparse_results: Sequence[Tuple[str, float]],
		k: int = 60,
	) -> List[Tuple[str, float]]:
		"""Merge ranked IDs using RRF: sum of ``1 / (k + rank)``."""
		if k < 1:
			raise ValueError("k must be greater than zero")

		rrf_scores: Dict[str, float] = {}
		for ranked_results in (dense_results, sparse_results):
			for rank, (chunk_id, _score) in enumerate(ranked_results, start=1):
				rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1 / (k + rank)

		return sorted(rrf_scores.items(), key=lambda item: (-item[1], item[0]))

	def hybrid_search(
		self,
		query: str,
		user_role: str,
		limit: int = 20,
	) -> List[Dict]:
		"""Retrieve and fuse a broad candidate set for a validated user role."""
		validate_role(user_role)
		if not query.strip():
			raise ValueError("query must be a non-empty string")
		if limit < 1:
			raise ValueError("limit must be greater than zero")
		if hasattr(self.bm25_engine, "bm25") and self.bm25_engine.bm25 is None:
			return []

		query_embedding = self.embedding_service.embed_text(query)
		dense_raw = [
			result
			for result in self.vector_store.search_with_rbac(
				query_embedding,
				user_role,
				limit=limit,
			)
			if user_role in result.get("metadata", {}).get("access_roles", [])
		]
		sparse_raw = [
			result
			for result in self.bm25_engine.search(query, limit=limit)
			if user_role in result.get("metadata", {}).get("access_roles", [])
		]

		records: Dict[str, Dict] = {}
		dense_ranked = []
		for result in dense_raw:
			key = self._result_key(result)
			dense_ranked.append((key, float(result.get("score", 0.0))))
			records[key] = self._normalize_result(result, key, "dense")

		sparse_ranked = []
		for result in sparse_raw:
			key = self._result_key(result)
			sparse_ranked.append((key, float(result.get("score", 0.0))))
			records.setdefault(key, self._normalize_result(result, key, "sparse"))

		fused = self.reciprocal_rank_fusion(dense_ranked, sparse_ranked)
		return [
			{
				**records[key],
				"score": score,
			}
			for key, score in fused[:limit]
		]

	@staticmethod
	def _result_key(result: Dict) -> str:
		chunk_id = result.get("chunk_id") or result.get("id")
		if not chunk_id:
			raise ValueError("Search result must contain chunk_id or id")
		return str(chunk_id)

	@staticmethod
	def _normalize_result(result: Dict, key: str, retrieval_source: str) -> Dict:
		return {
			"chunk_id": key,
			"text": result.get("text", ""),
			"metadata": result.get("metadata", {}),
			"retrieval_sources": [retrieval_source],
		}
