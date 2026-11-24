import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from docling.document_converter import DocumentConverter


logger = logging.getLogger(__name__)


class MedicineDocumentParser:
	"""Parse medical PDF files with Docling's structural conversion."""

	def __init__(self) -> None:
		self.converter = DocumentConverter()

	def parse_pdf(self, file_path: Union[str, Path]) -> Optional[Dict]:
		"""Convert one PDF to Markdown and return its source metadata."""
		path = Path(file_path)

		try:
			if path.suffix.lower() != ".pdf":
				raise ValueError(f"Expected a PDF file, got: {path.name}")

			logger.info("Parsing document: %s", path)
			result = self.converter.convert(str(path))
			document = result.document
			markdown_content = document.export_to_markdown()

			pages = getattr(document, "pages", None)
			page_count = len(pages) if pages is not None else 0

			return {
				"filename": path.name,
				"content_markdown": markdown_content,
				"metadata": {
					"source_document": path.name,
					"source_path": str(path.resolve()),
					"pages": page_count,
				},
			}
		except Exception:
			logger.exception("Skipping document that could not be parsed: %s", path)
			return None

	def parse_directory(self, directory: Union[str, Path]) -> List[Dict]:
		"""Parse every PDF below a directory and skip failed files."""
		directory_path = Path(directory)

		if not directory_path.is_dir():
			logger.error("Document directory does not exist: %s", directory_path)
			return []

		parsed_documents = []
		pdf_paths = sorted(
			path
			for path in directory_path.rglob("*")
			if path.is_file() and path.suffix.lower() == ".pdf"
		)
		for pdf_path in pdf_paths:
			parsed_document = self.parse_pdf(pdf_path)
			if parsed_document is not None:
				parsed_documents.append(parsed_document)

		logger.info(
			"Parsed %d of %d PDF files from %s",
			len(parsed_documents),
			len(pdf_paths),
			directory_path,
		)
		return parsed_documents


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	parser = MedicineDocumentParser()
	documents = parser.parse_directory("data/documents")
	for document in documents:
		print(
			f"Parsed {document['filename']} "
			f"({document['metadata']['pages']} pages)"
		)
