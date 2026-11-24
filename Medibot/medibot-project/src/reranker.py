from typing import Any, Dict, List, Optional, Sequence


class MedicalReranker:
	"""Rerank hybrid-search candidates with a cross-encoder model."""

	MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-12-v2"

	def __init__(self, model_name: str = MODEL_NAME, model: Optional[Any] = None) -> None:
		self.model_name = model_name
		if model is not None:
			self.model = model
			return

		try:
			from sentence_transformers import CrossEncoder
		except ImportError as error:
			raise RuntimeError(
				"sentence-transformers is required for cross-encoder reranking"
			) from error
		self.model = CrossEncoder(self.model_name)

	def rerank(
		self,
		question: str,
		chunks: Sequence[Dict],
		top_k: int = 3,
	) -> List[Dict]:
		"""Score candidates against a question and return the best ``top_k``."""
		if not isinstance(question, str) or not question.strip():
			raise ValueError("question must be a non-empty string")
		if top_k < 1:
			raise ValueError("top_k must be greater than zero")
		if not chunks:
			return []

		pairs = []
		for chunk in chunks:
			if not isinstance(chunk, dict):
				raise TypeError("Each candidate must be a dictionary")
			text = chunk.get("text")
			if not isinstance(text, str) or not text.strip():
				raise ValueError("Each candidate must contain non-empty text")
			pairs.append((question, text))

		scores = self.model.predict(pairs)
		if len(scores) != len(chunks):
			raise ValueError("Cross-encoder returned an unexpected number of scores")

		scored_chunks = []
		for index, (chunk, score) in enumerate(zip(chunks, scores)):
			try:
				numeric_score = float(score)
			except (TypeError, ValueError) as error:
				raise ValueError("Cross-encoder scores must be numeric") from error
			scored_chunk = dict(chunk)
			scored_chunk["rerank_score"] = numeric_score
			scored_chunk["_input_index"] = index
			scored_chunks.append(scored_chunk)

		scored_chunks.sort(
			key=lambda chunk: (-chunk["rerank_score"], chunk["_input_index"])
		)
		for chunk in scored_chunks:
			chunk.pop("_input_index", None)
		return scored_chunks[:top_k]
