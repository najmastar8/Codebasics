import hashlib
import json
from pathlib import Path
from typing import Any, List, Optional, Sequence


class EmbeddingService:
	"""Generate and cache embeddings with all-MiniLM-L6-v2."""

	MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
	EMBEDDING_DIMENSION = 384

	def __init__(
		self,
		model_name: str = MODEL_NAME,
		cache_dir: Optional[str] = ".cache/embeddings",
		model: Optional[Any] = None,
	) -> None:
		self.model_name = model_name
		self.cache_dir = Path(cache_dir) if cache_dir else None
		self.model = model

		if self.model is None:
			try:
				from sentence_transformers import SentenceTransformer
			except ImportError as error:
				raise RuntimeError(
					"sentence-transformers is required to generate embeddings"
				) from error
			self.model = SentenceTransformer(self.model_name)

		if self.cache_dir:
			self.cache_dir.mkdir(parents=True, exist_ok=True)

	def embed_text(self, text: str) -> List[float]:
		"""Return one validated 384-dimensional embedding."""
		if not isinstance(text, str) or not text.strip():
			raise ValueError("text must be a non-empty string")

		return self.embed_batch([text])[0]

	def embed_batch(self, texts: Sequence[str], batch_size: int = 32) -> List[List[float]]:
		"""Return embeddings in input order, using cached values when available."""
		if batch_size < 1:
			raise ValueError("batch_size must be greater than zero")

		text_list = list(texts)
		if any(not isinstance(text, str) or not text.strip() for text in text_list):
			raise ValueError("texts must contain only non-empty strings")

		results: List[Optional[List[float]]] = [None] * len(text_list)
		missing_indices = []
		for index, text in enumerate(text_list):
			cached = self._load_cached(text)
			if cached is None:
				missing_indices.append(index)
			else:
				results[index] = cached

		for start in range(0, len(missing_indices), batch_size):
			indices = missing_indices[start : start + batch_size]
			texts_to_encode = [text_list[index] for index in indices]
			encoded = self.model.encode(
				texts_to_encode,
				convert_to_numpy=True,
			)

			for index, vector in zip(indices, encoded):
				validated = self._validate_embedding(vector)
				results[index] = validated
				self._save_cached(text_list[index], validated)

		return [vector for vector in results if vector is not None]

	def _cache_path(self, text: str) -> Optional[Path]:
		if self.cache_dir is None:
			return None
		key = hashlib.sha256(
			f"{self.model_name}\0{text}".encode("utf-8")
		).hexdigest()
		return self.cache_dir / f"{key}.json"

	def _load_cached(self, text: str) -> Optional[List[float]]:
		path = self._cache_path(text)
		if path is None or not path.exists():
			return None

		try:
			return self._validate_embedding(json.loads(path.read_text(encoding="utf-8")))
		except (OSError, ValueError, TypeError, json.JSONDecodeError):
			return None

	def _save_cached(self, text: str, embedding: List[float]) -> None:
		path = self._cache_path(text)
		if path is None:
			return
		path.write_text(json.dumps(embedding), encoding="utf-8")

	@classmethod
	def _validate_embedding(cls, embedding: Any) -> List[float]:
		values = [float(value) for value in embedding]
		if len(values) != cls.EMBEDDING_DIMENSION:
			raise ValueError(
				f"Expected {cls.EMBEDDING_DIMENSION} embedding values, "
				f"got {len(values)}"
			)
		return values
