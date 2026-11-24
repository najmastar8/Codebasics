import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


class LLMService:
	"""Generate cited answers and SQL queries with a Groq-hosted model."""

	DEFAULT_MODEL = "llama-3.3-70b-versatile"

	def __init__(
		self,
		client: Optional[Any] = None,
		model: Optional[str] = None,
		env_path: Optional[str] = None,
	) -> None:
		load_dotenv(dotenv_path=Path(env_path) if env_path else None)
		self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)

		if client is not None:
			self.client = client
			return

		api_key = os.getenv("GROQ_API_KEY")
		if not api_key or api_key == "gsk_your_key_here":
			raise RuntimeError("GROQ_API_KEY is missing or still set to its placeholder")

		try:
			from groq import Groq
		except ImportError as error:
			raise RuntimeError("groq is required to generate LLM responses") from error

		self.client = Groq(api_key=api_key)

	def generate_answer(self, question: str, retrieved_chunks: List[Dict]) -> str:
		"""Generate an answer grounded in retrieved chunks with numbered citations."""
		if not question.strip():
			raise ValueError("question must be a non-empty string")
		if not retrieved_chunks:
			return "The answer is not present in the available context."

		context_parts = []
		for index, chunk in enumerate(retrieved_chunks, start=1):
			metadata = chunk.get("metadata", chunk)
			source = metadata.get("source_document", "unknown source")
			section = metadata.get("section_title", "unknown section")
			context_parts.append(
				f"[{index}] Source: {source}; Section: {section}\n"
				f"{chunk.get('text', '')}"
			)

		system_prompt = (
			"You are MediBot, an internal healthcare assistant. "
			"Answer using only the supplied context. Cite every factual claim "
			"with one or more source markers such as [1] or [2]. "
			"Never invent a citation or medical fact. If the answer is not "
			"supported by the context, say exactly: The answer is not present "
			"in the available context."
		)
		user_prompt = (
			"Context:\n\n"
			+ "\n\n".join(context_parts)
			+ f"\n\nQuestion: {question}\n\nAnswer with citations:"
		)

		return self._complete(system_prompt, user_prompt, temperature=0.2, max_tokens=500)

	def generate_sql(self, question: str, schema_info: str) -> str:
		"""Translate a question to SQLite SQL without producing an answer."""
		if not question.strip():
			raise ValueError("question must be a non-empty string")
		if not schema_info.strip():
			raise ValueError("schema_info must be a non-empty string")

		system_prompt = (
			"You are a SQLite SQL generator. Return only one read-only SELECT "
			"or WITH query, with no Markdown fences or explanation. Never return "
			"INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, or multiple statements."
		)
		user_prompt = (
			f"Database schema:\n{schema_info}\n\n"
			f"Question: {question}\n\nReturn only the SQL query:"
		)
		sql = self._complete(system_prompt, user_prompt, temperature=0.0, max_tokens=250)
		cleaned_sql = re.sub(
			r"^```(?:sql)?\s*|\s*```$",
			"",
			sql.strip(),
			flags=re.IGNORECASE,
		)
		return cleaned_sql.strip()

	def translate_to_sql(self, question: str, schema_info: str) -> str:
		"""Backward-compatible name for :meth:`generate_sql`."""
		return self.generate_sql(question, schema_info)

	def _complete(
		self,
		system_prompt: str,
		user_prompt: str,
		temperature: float,
		max_tokens: int,
	) -> str:
		try:
			response = self.client.chat.completions.create(
				model=self.model,
				messages=[
					{"role": "system", "content": system_prompt},
					{"role": "user", "content": user_prompt},
				],
				temperature=temperature,
				max_tokens=max_tokens,
			)
			return response.choices[0].message.content.strip()
		except Exception as error:
			raise RuntimeError("Groq completion failed") from error
