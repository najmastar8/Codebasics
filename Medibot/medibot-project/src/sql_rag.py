import json
import re
from typing import Any, Dict, List, Optional

from src.database import DatabaseConnection
from src.llm_service import LLMService


class SQLRAGChain:
	"""Answer analytical questions with schema-aware, read-only SQL RAG."""

	MAX_ROWS = 100
	_FORBIDDEN_KEYWORDS = re.compile(
		r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|ATTACH|DETACH|REPLACE|CREATE|VACUUM)\b",
		re.IGNORECASE,
	)

	def __init__(
		self,
		db: Optional[DatabaseConnection] = None,
		llm: Optional[LLMService] = None,
		db_path: str = "data/mediassist.db",
	) -> None:
		self.db = db or DatabaseConnection(db_path)
		self.db.initialize_schema()
		self.llm = llm or LLMService()

	def format_schema_for_llm(self) -> str:
		"""Format the live SQLite schema for the SQL-generation prompt."""
		schema = self.db.get_schema()
		parts = ["SQLite database schema:"]
		for table_name, table_info in schema.items():
			parts.append(f"\nTable: {table_name}")
			for column in table_info["columns"]:
				parts.append(
					f"- {column['name']} ({column['type'] or 'TEXT'})"
					+ (" PRIMARY KEY" if column["primary_key"] else "")
				)
		return "\n".join(parts)

	@classmethod
	def validate_sql(cls, sql: str) -> str:
		"""Validate and normalize one read-only SELECT or WITH statement."""
		if not isinstance(sql, str) or not sql.strip():
			raise ValueError("Generated SQL must be a non-empty string")

		cleaned = sql.strip()
		if cleaned.endswith(";"):
			cleaned = cleaned[:-1].rstrip()
		if ";" in cleaned:
			raise ValueError("Multiple SQL statements are not allowed")
		if not re.match(r"^(?:SELECT|WITH)\b", cleaned, re.IGNORECASE):
			raise ValueError("Only SELECT and WITH queries are allowed")
		if cls._FORBIDDEN_KEYWORDS.search(cleaned):
			raise ValueError("SQL contains a forbidden write or schema operation")
		return cleaned

	def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
		"""Validate SQL and execute it with a hard result-row limit."""
		validated_sql = self.validate_sql(sql)
		bounded_sql = (
			f"SELECT * FROM ({validated_sql}) AS sql_rag_result "
			f"LIMIT {self.MAX_ROWS}"
		)
		return self.db.execute_query(bounded_sql)

	def answer(self, question: str) -> str:
		"""Run schema lookup, SQL generation, validation, execution, and summary."""
		if not isinstance(question, str) or not question.strip():
			raise ValueError("question must be a non-empty string")

		sql = self.llm.generate_sql(question, self.format_schema_for_llm())
		results = self.execute_sql(sql)
		if not results:
			return "No results found for that query."

		results_text = json.dumps(results, indent=2, default=str)
		system_prompt = (
			"You are MediBot, a healthcare analytics assistant. Summarize only "
			"the supplied SQL results, answer the question directly, and cite "
			"specific numbers. Do not invent facts."
		)
		user_prompt = (
			f"Question: {question}\n\nSQL results:\n{results_text}\n\n"
			"Provide a concise natural-language answer:"
		)
		return self.llm._complete(
			system_prompt,
			user_prompt,
			temperature=0.2,
			max_tokens=300,
		)

	def close(self) -> None:
		"""Close the underlying database connection."""
		self.db.close()
