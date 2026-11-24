import logging
import hashlib
import json
import uuid
from typing import Dict, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
	Distance,
	FieldCondition,
	Filter,
	MatchValue,
	PayloadSchemaType,
	PointStruct,
	VectorParams,
)

from src.rbac_config import validate_role


logger = logging.getLogger(__name__)


class QdrantVectorStore:
	"""Store document chunks and enforce RBAC during Qdrant retrieval."""

	COLLECTION_NAME = "medibot_documents"
	EMBEDDING_DIMENSION = 384

	def __init__(
		self,
		url: str = "http://localhost:6333",
		api_key: Optional[str] = None,
		client: Optional[QdrantClient] = None,
	) -> None:
		self.client = client or QdrantClient(url=url, api_key=api_key)

	def init_collection(self, recreate: bool = False) -> None:
		"""Create the vector collection and the role payload index."""
		if recreate:
			self.client.recreate_collection(
				collection_name=self.COLLECTION_NAME,
				vectors_config=VectorParams(
					size=self.EMBEDDING_DIMENSION,
					distance=Distance.COSINE,
				),
			)
		else:
			collections = self.client.get_collections().collections
			exists = any(
				collection.name == self.COLLECTION_NAME for collection in collections
			)
			if not exists:
				self.client.create_collection(
					collection_name=self.COLLECTION_NAME,
					vectors_config=VectorParams(
						size=self.EMBEDDING_DIMENSION,
						distance=Distance.COSINE,
					),
				)

		self.client.create_payload_index(
			collection_name=self.COLLECTION_NAME,
			field_name="access_roles",
			field_schema=PayloadSchemaType.KEYWORD,
		)
		logger.info("Qdrant collection ready: %s", self.COLLECTION_NAME)

	def add_chunk(
		self,
		chunk_text: str,
		embedding: List[float],
		metadata: Dict,
		chunk_id: Optional[str] = None,
	) -> str:
		"""Upsert one chunk with its text and metadata as Qdrant payload."""
		if len(embedding) != self.EMBEDDING_DIMENSION:
			raise ValueError(
				f"Expected {self.EMBEDDING_DIMENSION} embedding values, "
				f"got {len(embedding)}"
			)
		if not metadata.get("access_roles"):
			raise ValueError("Chunk metadata must include access_roles")

		stable_id = chunk_id or metadata.get("chunk_id") or self._stable_chunk_id(
			chunk_text,
			metadata,
		)
		payload = {
			"text": chunk_text,
			**metadata,
			"chunk_id": stable_id,
		}
		self.client.upsert(
			collection_name=self.COLLECTION_NAME,
			points=[
				PointStruct(
					id=self._point_id(stable_id),
					vector=embedding,
					payload=payload,
				)
			],
		)
		return stable_id

	@staticmethod
	def _point_id(chunk_id: str) -> str:
		"""Convert a stable chunk ID into a valid deterministic Qdrant UUID."""
		return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

	@staticmethod
	def _stable_chunk_id(chunk_text: str, metadata: Dict) -> str:
		identity = json.dumps(
			{"text": chunk_text.strip(), "metadata": metadata},
			sort_keys=True,
			separators=(",", ":"),
			default=str,
		)
		digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
		return f"chunk-{digest}"

	def search_with_rbac(
		self,
		query_embedding: List[float],
		user_role: str,
		limit: int = 10,
	) -> List[Dict]:
		"""Search only chunks whose payload grants access to ``user_role``."""
		validate_role(user_role)
		if len(query_embedding) != self.EMBEDDING_DIMENSION:
			raise ValueError(
				f"Expected {self.EMBEDDING_DIMENSION} query values, "
				f"got {len(query_embedding)}"
			)
		if limit < 1:
			raise ValueError("limit must be greater than zero")

		rbac_filter = Filter(
			must=[
				FieldCondition(
					key="access_roles",
					match=MatchValue(value=user_role),
				)
			]
		)
		if hasattr(self.client, "query_points"):
			response = self.client.query_points(
				collection_name=self.COLLECTION_NAME,
				query=query_embedding,
				query_filter=rbac_filter,
				limit=limit,
				with_payload=True,
			)
			results = response.points
		else:
			results = self.client.search(
				collection_name=self.COLLECTION_NAME,
				query_vector=query_embedding,
				query_filter=rbac_filter,
				limit=limit,
				with_payload=True,
			)

		formatted_results = []
		for result in results:
			payload = result.payload or {}
			metadata = {
				key: value
				for key, value in payload.items()
				if key not in {"text", "chunk_id"}
			}
			formatted_results.append(
				{
					"id": result.id,
					"chunk_id": payload.get("chunk_id", str(result.id)),
					"score": result.score,
					"text": payload.get("text", ""),
					"metadata": metadata,
				}
			)

		logger.info("Retrieved %d RBAC-filtered chunks for role %s", len(formatted_results), user_role)
		return formatted_results
