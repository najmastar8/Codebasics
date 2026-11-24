import logging
import re
from typing import Dict, List


logger = logging.getLogger(__name__)


class HierarchicalChunker:
	"""Split Markdown into structure-aware, metadata-rich document chunks."""

	def __init__(self, max_chunk_tokens: int = 512, overlap: int = 50) -> None:
		if max_chunk_tokens < 1:
			raise ValueError("max_chunk_tokens must be greater than zero")
		if overlap < 0:
			raise ValueError("overlap cannot be negative")

		self.max_tokens = max_chunk_tokens
		self.overlap = overlap
		self.chars_per_token = 4

	def chunk_markdown(
		self,
		markdown_text: str,
		source_doc: str,
		collection: str,
		access_roles: List[str],
	) -> List[Dict]:
		"""Chunk Markdown while preserving headings, tables, and access metadata."""
		chunks: List[Dict] = []
		heading_stack: Dict[int, str] = {}
		pending_lines: List[str] = []
		pending_tokens = 0
		lines = markdown_text.splitlines()
		line_index = 0

		def context() -> Dict[str, str]:
			section_title = heading_stack.get(1, "General")
			subsection_levels = sorted(level for level in heading_stack if level >= 2)
			subsection_title = (
				heading_stack[subsection_levels[-1]] if subsection_levels else ""
			)
			heading_path = " > ".join(
				heading_stack[level]
				for level in sorted(heading_stack)
			)
			return {
				"section_title": section_title,
				"subsection_title": subsection_title,
				"heading_path": heading_path,
			}

		def add_text_chunk(chunk_lines: List[str], chunk_context: Dict[str, str]) -> None:
			text = "\n".join(chunk_lines).strip()
			if not text:
				return
			chunks.append(
				self._create_chunk(
					text,
					source_doc,
					collection,
					access_roles,
					chunk_context,
					"text",
				)
			)

		def flush_text() -> None:
			nonlocal pending_lines, pending_tokens
			add_text_chunk(pending_lines, context())
			pending_lines = []
			pending_tokens = 0

		while line_index < len(lines):
			line = lines[line_index]
			heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)

			if heading_match:
				flush_text()
				level = len(heading_match.group(1))
				heading_stack = {
					depth: title
					for depth, title in heading_stack.items()
					if depth < level
				}
				heading_stack[level] = heading_match.group(2).strip()
				pending_lines = [line]
				pending_tokens = self._estimate_tokens(line)
				line_index += 1
				continue

			if self._is_table_line(line):
				flush_text()
				table_lines = []
				table_context = context()
				while line_index < len(lines) and self._is_table_line(lines[line_index]):
					table_lines.append(lines[line_index])
					line_index += 1
				add_text_chunk(table_lines, table_context)
				chunks[-1]["metadata"]["chunk_type"] = "table"
				continue

			line_tokens = self._estimate_tokens(line)
			if pending_lines and pending_tokens + line_tokens > self.max_tokens:
				flush_text()

			pending_lines.append(line)
			pending_tokens += line_tokens
			line_index += 1

		flush_text()
		logger.info("Created %d chunks from %s", len(chunks), source_doc)
		return chunks

	@staticmethod
	def _is_table_line(line: str) -> bool:
		return line.strip().startswith("|") and line.strip().endswith("|")

	def _estimate_tokens(self, text: str) -> int:
		return max(1, (len(text) + self.chars_per_token - 1) // self.chars_per_token)

	@staticmethod
	def _create_chunk(
		text: str,
		source_doc: str,
		collection: str,
		access_roles: List[str],
		context: Dict[str, str],
		chunk_type: str,
	) -> Dict:
		return {
			"text": text,
			"metadata": {
				"source_document": source_doc,
				"collection": collection,
				"access_roles": list(access_roles),
				"section_title": context["section_title"],
				"subsection_title": context["subsection_title"],
				"heading_path": context["heading_path"],
				"chunk_type": chunk_type,
			},
		}
