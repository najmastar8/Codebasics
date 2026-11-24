from src.chunking import HierarchicalChunker


MARKDOWN = """# Clinical Guide
## Fever Treatment
Paracetamol dosage guidance.

| Dose | Frequency |
| --- | --- |
| 500mg | Twice daily |

### Pediatric Patients
Use age-appropriate dosing.
"""


def test_section_titles_survive_chunking():
    chunks = HierarchicalChunker().chunk_markdown(
        MARKDOWN,
        "clinical.pdf",
        "clinical",
        ["doctor", "admin"],
    )

    pediatric = next(
        chunk
        for chunk in chunks
        if chunk["metadata"]["subsection_title"] == "Pediatric Patients"
    )
    assert pediatric["metadata"]["section_title"] == "Clinical Guide"
    assert pediatric["metadata"]["heading_path"] == (
        "Clinical Guide > Fever Treatment > Pediatric Patients"
    )


def test_tables_remain_intact_and_are_marked_as_tables():
    chunks = HierarchicalChunker().chunk_markdown(
        MARKDOWN,
        "clinical.pdf",
        "clinical",
        ["doctor", "admin"],
    )
    table_chunks = [
        chunk for chunk in chunks if chunk["metadata"]["chunk_type"] == "table"
    ]

    assert len(table_chunks) == 1
    assert "| Dose | Frequency |" in table_chunks[0]["text"]
    assert "| 500mg | Twice daily |" in table_chunks[0]["text"]


def test_every_chunk_contains_access_metadata():
    chunks = HierarchicalChunker().chunk_markdown(
        MARKDOWN,
        "clinical.pdf",
        "clinical",
        ["doctor", "admin"],
    )
    for chunk in chunks:
        assert chunk["metadata"]["source_document"] == "clinical.pdf"
        assert chunk["metadata"]["collection"] == "clinical"
        assert chunk["metadata"]["access_roles"] == ["doctor", "admin"]
