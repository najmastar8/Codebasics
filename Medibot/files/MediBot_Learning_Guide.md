# 🏥 MediBot RAG Project: Complete Learning & Implementation Guide

> Advanced RAG with Hybrid Search, Reranking, and Role-Based Access Control

---

## 📋 Project Overview

**MediBot** is a production-grade RAG system for MediAssist Health Network. This guide breaks down the assignment into **8 manageable phases** with learning resources, prerequisites, and concrete implementation steps.

### Key Requirements
1. **RBAC enforced at vector store retrieval layer** (metadata filters, not UI-only)
2. **Structural PDF parsing** with Docling + hierarchical chunking
3. **Hybrid RAG** (dense embeddings + BM25 keyword search + fusion)
4. **Cross-encoder reranking** to narrow candidates before LLM
5. **SQL RAG** for analytical questions (claims, maintenance tickets)
6. **FastAPI backend** with /login, /chat, /collections, /health endpoints
7. **Next.js frontend** with login, chat, role badges, source citations
8. **RBAC enforcement demonstrations** with adversarial prompt examples in README

### Demo User Accounts

Use these credentials for testing all 5 user roles:

| Username | Password | Role | Collections |
|----------|----------|------|------------|
| `dr.mehta` | `password123` | `doctor` | Clinical, Nursing, General |
| `nurse.priya` | `password123` | `nurse` | Nursing, General |
| `billing.ravi` | `password123` | `billing_executive` | Billing, General |
| `tech.anand` | `password123` | `technician` | Equipment, General |
| `admin.sys` | `password123` | `admin` | All Collections |

**Note:** In production, use real user management with JWT tokens, not hardcoded passwords.

---

# Phase 0: Prerequisites & Environment Setup
**Time: 2-3 hours | Difficulty: ⭐**

Before coding, ensure you have the foundations.

### What You Need to Know
- **Python fundamentals** (functions, classes, loops, error handling, async/await)
- **REST API concepts** (HTTP methods, JSON, request/response, CORS)
- **SQL basics** (SELECT, WHERE, JOIN, aggregation functions)
- **Vector databases** (similarity search, metadata filtering, point storage)
- **Hybrid search** (dense + sparse retrieval, score fusion)

### Learning Resources
| Topic | Resource | Duration |
|-------|----------|----------|
| Python basics & async | [Python Async Tutorial](https://realpython.com/async-io-python/) | 1.5 hours |
| REST APIs | [REST API Design](https://restfulapi.net/) | 30 min |
| Vector Databases 101 | [Qdrant Documentation](https://qdrant.tech/documentation/) | 45 min |
| RAG Fundamentals | [DeepLearning.AI: RAG Short Course](https://www.deeplearning.ai/short-courses/retrieval-augmented-generation-llms/) | 1 hour |
| Hybrid Search | [Weaviate Hybrid Search](https://weaviate.io/blog/hybrid-search-explained) | 30 min |

### Setup Steps

```bash
# 1. Create project directory and virtual environment
mkdir medibot-project && cd medibot-project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Create initial requirements.txt
cat > requirements.txt << 'EOF'
# Phase 0: Core Dependencies
python-dotenv==1.0.0
requests==2.31.0
pydantic==2.0.0
EOF

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (don't commit this!)
cat > .env << 'EOF'
# LLM & Embedding
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_key_here

# Database
DATABASE_PATH=data/mediassist.db

# Frontend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF

# 5. Create project structure
mkdir -p src data tests frontend
```

### Checklist
- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Requirements.txt created
- [ ] .env file created
- [ ] Project folder structure ready

---

# Phase 1: Document Ingestion with Docling & Hierarchical Chunking
**Time: 5-6 hours | Difficulty: ⭐⭐**

### What You'll Learn
- Parse PDFs with structural awareness using Docling
- Implement hierarchical chunking (section → subsection → paragraph)
- Carry parent section context in every chunk
- Build complete metadata schema (collection, access_roles, section_title, chunk_type)

### Why This Matters
Traditional fixed-size chunking destroys medical document structure. A drug dosage table split across two chunks becomes meaningless. Each chunk must carry its parent heading as context — a chunk that just says "25mg twice daily" with no surrounding section is useless to both retrieval and LLM.

### Learning Resources
| Topic | Resource | Duration |
|-------|----------|----------|
| Docling Overview | [Docling GitHub](https://github.com/DS4SD/docling) | 20 min |
| Docling Docs | [Official Docs](https://ds4sd.github.io/docling/) | 1 hour |
| PDF Structure | [PDF Parsing Best Practices](https://medium.com/the-dl/parsing-pdfs-at-scale-with-aws-textract-57127ae42833) | 30 min |
| Hierarchical Chunking | [LlamaIndex Chunking Strategies](https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/index/) | 45 min |

### Implementation Tasks

**Step 1.1: Install Docling and dependencies**
```bash
pip install docling==1.6.0 python-pptx pillow pydantic requests
```

**Step 1.2: Create document parser with Docling**
```python
# Create: src/document_parser.py

from docling.document_converter import DocumentConverter
from docling.models.document import PdfDocument
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

class MedicineDocumentParser:
    """Parse medical PDFs with structural awareness using Docling."""
    
    def __init__(self):
        """Initialize Docling converter."""
        self.converter = DocumentConverter()
    
    def parse_pdf(self, file_path: str) -> Optional[Dict]:
        """
        Parse PDF with structural awareness.
        
        Returns: {
            "filename": "document.pdf",
            "content_markdown": "# Heading\n## Section\nParagraph...",
            "structure": [
                {"level": 1, "title": "Main Heading", "content": "..."},
                {"level": 2, "title": "Sub Heading", "content": "..."}
            ],
            "metadata": {
                "pages": 15,
                "tables_found": 3,
                "source": "document.pdf"
            }
        }
        """
        try:
            logger.info(f"Parsing document: {file_path}")
            
            result = self.converter.convert(file_path)
            document: PdfDocument = result.document
            
            # Export to markdown to preserve structure
            markdown_content = document.export_to_markdown()
            
            return {
                "filename": file_path.split("/")[-1],
                "content_markdown": markdown_content,
                "metadata": {
                    "source": file_path.split("/")[-1],
                    "pages": len(document.pages) if hasattr(document, 'pages') else 0
                }
            }
        
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

# Test
if __name__ == "__main__":
    parser = MedicineDocumentParser()
    result = parser.parse_pdf("sample.pdf")
    if result:
        print(f"✅ Parsed {result['filename']}")
        print(f"Pages: {result['metadata']['pages']}")
        print(f"Content preview: {result['content_markdown'][:200]}...")
```

**Step 1.3: Implement hierarchical chunker with metadata**
```python
# Create: src/chunking.py

from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class HierarchicalChunker:
    """
    Split documents hierarchically by structure, then by token count.
    Section → Subsection → Paragraph / Table → Token limit
    """
    
    def __init__(self, max_chunk_tokens: int = 512, overlap: int = 50):
        self.max_tokens = max_chunk_tokens
        self.overlap = overlap
        self.approximate_chars_per_token = 4
    
    def chunk_markdown(self, markdown_text: str, source_doc: str, 
                      collection: str, access_roles: List[str]) -> List[Dict]:
        """
        Chunk markdown while preserving structure and metadata.
        
        Args:
            markdown_text: Full markdown from Docling
            source_doc: Original filename
            collection: One of: general, clinical, nursing, billing, equipment
            access_roles: List of roles that can access this chunk
        
        Returns: [
            {
                "text": "# Treatment Protocols\n## Fever Treatment\nParacetamol 500mg...",
                "metadata": {
                    "source_document": "clinical_handbook.pdf",
                    "collection": "clinical",
                    "access_roles": ["doctor", "admin"],
                    "section_title": "## Fever Treatment",
                    "chunk_type": "text"
                }
            },
            ...
        ]
        """
        chunks = []
        lines = markdown_text.split('\n')
        
        current_section = "General"
        current_subsection = ""
        current_chunk_lines = []
        current_chunk_tokens = 0
        
        for line in lines:
            line_tokens = len(line) // self.approximate_chars_per_token + 1
            
            # Detect heading level 1
            if line.startswith('# ') and not line.startswith('# '):
                if current_chunk_lines:
                    chunks.append(self._create_chunk(
                        current_chunk_lines, source_doc, collection, 
                        access_roles, current_section, "text"
                    ))
                    current_chunk_lines = []
                    current_chunk_tokens = 0
                
                current_section = line.strip()
                current_subsection = ""
            
            # Detect heading level 2
            elif line.startswith('## '):
                if current_chunk_lines:
                    chunks.append(self._create_chunk(
                        current_chunk_lines, source_doc, collection,
                        access_roles, current_section, "text"
                    ))
                    current_chunk_lines = []
                    current_chunk_tokens = 0
                
                current_subsection = line.strip()
            
            # Detect tables (lines with |)
            elif '|' in line and line.strip().startswith('|'):
                # Save current text chunk
                if current_chunk_lines:
                    chunks.append(self._create_chunk(
                        current_chunk_lines, source_doc, collection,
                        access_roles, current_section, "text"
                    ))
                    current_chunk_lines = []
                    current_chunk_tokens = 0
                
                # Collect table rows
                table_lines = [line]
                # In production, collect entire table
                
                chunks.append(self._create_chunk(
                    table_lines, source_doc, collection,
                    access_roles, current_section, "table"
                ))
            
            # Regular text - add to current chunk with token check
            else:
                if current_chunk_tokens + line_tokens > self.max_tokens and current_chunk_lines:
                    # Save chunk and start new one
                    chunks.append(self._create_chunk(
                        current_chunk_lines, source_doc, collection,
                        access_roles, current_section, "text"
                    ))
                    current_chunk_lines = [line]
                    current_chunk_tokens = line_tokens
                else:
                    current_chunk_lines.append(line)
                    current_chunk_tokens += line_tokens
        
        # Save final chunk
        if current_chunk_lines:
            chunks.append(self._create_chunk(
                current_chunk_lines, source_doc, collection,
                access_roles, current_section, "text"
            ))
        
        logger.info(f"✅ Created {len(chunks)} chunks from {source_doc}")
        return chunks
    
    def _create_chunk(self, lines: List[str], source_doc: str, collection: str,
                     access_roles: List[str], section_title: str, 
                     chunk_type: str) -> Dict:
        """Helper to create a chunk dict with metadata."""
        return {
            "text": "\n".join(lines).strip(),
            "metadata": {
                "source_document": source_doc,
                "collection": collection,
                "access_roles": access_roles,
                "section_title": section_title,
                "chunk_type": chunk_type
            }
        }

# Test
if __name__ == "__main__":
    chunker = HierarchicalChunker(max_chunk_tokens=256)
    
    test_markdown = """# Treatment Protocols
## Fever Management
Fever is a common symptom. Treatment options:
- Paracetamol 500mg twice daily
- Ibuprofen 400mg three times daily

## Infection Control
Always maintain hygiene protocols.
"""
    
    chunks = chunker.chunk_markdown(
        test_markdown, 
        "clinical_handbook.pdf",
        "clinical",
        ["doctor", "admin"]
    )
    
    for i, chunk in enumerate(chunks):
        print(f"\n[Chunk {i+1}]")
        print(f"Section: {chunk['metadata']['section_title']}")
        print(f"Type: {chunk['metadata']['chunk_type']}")
        print(f"Text: {chunk['text'][:100]}...")
```

**Step 1.4: Create RBAC configuration**
```python
# Create: src/rbac_config.py

from typing import List, Dict

# Role to Collection Access Matrix
ROLE_COLLECTION_MATRIX: Dict[str, List[str]] = {
    "doctor": ["clinical", "nursing", "general"],
    "nurse": ["nursing", "general"],
    "billing_executive": ["billing", "general"],
    "technician": ["equipment", "general"],
    "admin": ["clinical", "nursing", "billing", "equipment", "general"]
}

def get_accessible_collections(role: str) -> List[str]:
    """Get collections accessible to a user role."""
    return ROLE_COLLECTION_MATRIX.get(role, ["general"])

def get_access_roles_for_collection(collection: str) -> List[str]:
    """Get roles that can access chunks from a specific collection."""
    roles_with_access = []
    for role, collections in ROLE_COLLECTION_MATRIX.items():
        if collection in collections:
            roles_with_access.append(role)
    return roles_with_access

# Test
if __name__ == "__main__":
    print(f"Doctor can access: {get_accessible_collections('doctor')}")
    print(f"Nurse can access: {get_accessible_collections('nurse')}")
    print(f"Clinical docs accessible by: {get_access_roles_for_collection('clinical')}")
```

### Practice Exercise
- [ ] Download/create a sample medical PDF
- [ ] Parse it using Docling
- [ ] Inspect the markdown output for structure
- [ ] Run hierarchical chunker, verify sections are preserved
- [ ] Check 5-10 chunks have correct section titles and metadata

### Checklist
- [ ] Docling installed and working
- [ ] Document parser script created and tested
- [ ] Hierarchical chunker produces chunks with metadata
- [ ] RBAC config file created
- [ ] All chunks carry parent section title as context
    
    def __init__(self):
        self.converter = DocumentConverter()
    
    def parse_pdf(self, file_path: str) -> Dict:
        """
        Parse PDF and extract structure
        Returns: {
            "content": parsed_content,
            "sections": [list of section titles],
            "tables": [list of tables],
            "metadata": {source, pages, etc}
        }
        """
        try:
            result = self.converter.convert(file_path)
            return {
                "content": result.document.export_to_markdown(),
                "metadata": {
                    "source": file_path.split('/')[-1],
                    "pages": len(result.document.pages)
                }
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

# Test with a sample PDF
if __name__ == "__main__":
    parser = MedicineDocumentParser()
    result = parser.parse_pdf("sample.pdf")
    print(json.dumps(result, indent=2))
```

**Step 1.3: Implement hierarchical chunking**
```python
# Create: src/chunking.py

class HierarchicalChunker:
    """
    Split documents by structure first (sections, subsections),
    then by token count.
    """
    
    def __init__(self, max_chunk_tokens: int = 512):
        self.max_tokens = max_chunk_tokens
    
    def chunk_markdown(self, markdown_text: str, source_doc: str) -> List[Dict]:
        """
        Input: Full markdown from Docling
        Output: List of chunks with metadata
        
        Returns: [
            {
                "text": "chunk content",
                "metadata": {
                    "source_document": "original.pdf",
                    "section_title": "## Treatment Protocols",
                    "chunk_type": "text"
                }
            },
            ...
        ]
        """
        chunks = []
        lines = markdown_text.split('\n')
        current_section = "General"
        current_chunk_text = ""
        
        for line in lines:
            # Detect section headings
            if line.startswith('#'):
                if current_chunk_text.strip():
                    chunks.append({
                        "text": current_chunk_text.strip(),
                        "metadata": {
                            "source_document": source_doc,
                            "section_title": current_section,
                            "chunk_type": "text"
                        }
                    })
                    current_chunk_text = ""
                current_section = line.lstrip('#').strip()
            
            # Detect tables (markdown format: lines with |)
            elif line.strip().startswith('|'):
                if current_chunk_text.strip():
                    chunks.append({
                        "text": current_chunk_text.strip(),
                        "metadata": {
                            "source_document": source_doc,
                            "section_title": current_section,
                            "chunk_type": "text"
                        }
                    })
                current_chunk_text = ""
                
                # Extract full table
                table_lines = [line]
                # (In production, collect full table)
                chunks.append({
                    "text": "\n".join(table_lines),
                    "metadata": {
                        "source_document": source_doc,
                        "section_title": current_section,
                        "chunk_type": "table"
                    }
                })
            else:
                current_chunk_text += line + "\n"
        
        return chunks
```

### Practice Exercise
- [ ] Download one of the sample PDFs (or create a test PDF)
- [ ] Parse it using Docling
- [ ] Extract markdown output
- [ ] Manually inspect the structure
- [ ] Run hierarchical chunker and verify 5-10 chunks are created with correct section titles

### Checklist
- [ ] Docling installed and tested
- [ ] Document parser script created
- [ ] Hierarchical chunker implemented
- [ ] Tested on at least one sample PDF
- [ ] Chunk metadata structure understood

---

# Phase 2: Vector Database Setup (Qdrant) with RBAC Metadata Filtering
**Time: 3-4 hours | Difficulty: ⭐⭐**

### What You'll Learn
- Set up Qdrant locally with Docker
- Store vectors with complete metadata
- Implement RBAC metadata filtering at query time
- Understand why metadata filtering at the DB level is critical for security

### Why This Matters
**RBAC must be enforced at the retrieval layer, not the application layer.** If you filter results after getting them from Qdrant, an adversarial prompt could trick the LLM. By filtering at Qdrant query time, restricted chunks never reach your application.

### Learning Resources
| Topic | Resource | Duration |
|-------|----------|----------|
| Qdrant Quickstart | [Qdrant Getting Started](https://qdrant.tech/documentation/quick-start/) | 30 min |
| Docker Setup | [Qdrant Docker](https://qdrant.tech/documentation/guides/setup_and_manage/docker/) | 20 min |
| Metadata Filtering | [Qdrant Filtering](https://qdrant.tech/documentation/concepts/filtering/) | 45 min |
| Qdrant Python SDK | [qdrant-client docs](https://qdrant-client.readthedocs.io/) | 30 min |

### Implementation Tasks

**Step 2.1: Start Qdrant in Docker**
```bash
# Pull and run Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant:latest

# Verify it's running
curl http://localhost:6333/health

# If you need to stop it later:
docker stop qdrant
docker rm qdrant
```

**Step 2.2: Create Qdrant vector store class**
```python
# Create: src/vector_store.py

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, VectorParams, Distance, 
    FieldCondition, MatchValue, HasIdCondition,
    Filter
)
from typing import List, Dict, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

class QdrantVectorStore:
    """Manage vector storage and retrieval with RBAC metadata filtering."""
    
    def __init__(self, url: str = "http://localhost:6333", api_key: Optional[str] = None):
        """
        Initialize Qdrant client.
        
        Args:
            url: Qdrant server URL
            api_key: API key if using Qdrant Cloud
        """
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = "medibot_documents"
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
    
    def init_collection(self) -> bool:
        """Create collection with vector config and payload indexing."""
        try:
            # Delete if exists (for testing)
            try:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
            except:
                pass
            
            # Create new collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            
            # Create payload indexes for faster filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="access_roles",
                field_schema="keyword"
            )
            
            logger.info(f"✅ Collection '{self.collection_name}' created with indexes")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing collection: {e}")
            return False
    
    def add_chunk(self, chunk_text: str, embedding: List[float], 
                  metadata: Dict) -> Optional[str]:
        """
        Add a chunk with embedding and RBAC metadata.
        
        Args:
            chunk_text: The text content
            embedding: 384-dimensional vector
            metadata: {
                "source_document": str,
                "collection": str,
                "access_roles": List[str],
                "section_title": str,
                "chunk_type": str
            }
        
        Returns:
            Chunk ID
        """
        try:
            chunk_id = str(uuid.uuid4())
            point_id = int(uuid.uuid4().int % (2**31))
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": chunk_text,
                    "source_document": metadata.get("source_document", "unknown"),
                    "collection": metadata.get("collection", "general"),
                    "access_roles": metadata.get("access_roles", ["admin"]),
                    "section_title": metadata.get("section_title", ""),
                    "chunk_type": metadata.get("chunk_type", "text"),
                    "chunk_id": chunk_id
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return chunk_id
        
        except Exception as e:
            logger.error(f"Error adding chunk: {e}")
            return None
    
    def search_with_rbac(self, query_embedding: List[float], 
                         user_role: str, limit: int = 10) -> List[Dict]:
        """
        Search with RBAC enforcement using metadata filter.
        
        **CRITICAL:** Filter is applied at Qdrant level, not in Python.
        This prevents adversarial prompts from leaking restricted documents.
        
        Args:
            query_embedding: 384-dimensional query vector
            user_role: User's role (doctor, nurse, billing_executive, technician, admin)
            limit: Max results to return
        
        Returns:
            List of {id, score, text, metadata, source_document, section_title}
        """
        try:
            # Create RBAC filter: must have user_role in access_roles list
            rbac_filter = Filter(
                must=[
                    FieldCondition(
                        key="access_roles",
                        match=MatchValue(value=user_role)
                    )
                ]
            )
            
            # Search with filter applied AT RETRIEVAL TIME
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=rbac_filter,
                limit=limit,
                with_payload=True
            )
            
            # Convert to response format
            filtered_results = []
            for result in results:
                filtered_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "source_document": result.payload.get("source_document"),
                    "section_title": result.payload.get("section_title"),
                    "collection": result.payload.get("collection"),
                    "chunk_type": result.payload.get("chunk_type")
                })
            
            logger.info(f"✅ Found {len(filtered_results)} results for {user_role}")
            return filtered_results
        
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

# Test
if __name__ == "__main__":
    store = QdrantVectorStore()
    store.init_collection()
    
    # Mock embedding
    mock_embedding = [0.1] * 384
    
    # Add clinical chunk (only doctors/admin can see)
    store.add_chunk(
        "Treatment for fever: Paracetamol 500mg twice daily",
        mock_embedding,
        {
            "collection": "clinical",
            "access_roles": ["doctor", "admin"],
            "section_title": "Treatment Protocols",
            "chunk_type": "text",
            "source_document": "clinical_handbook.pdf"
        }
    )
    
    # Test RBAC
    print("\n--- Searching as Doctor ---")
    results = store.search_with_rbac(mock_embedding, "doctor")
    print(f"Found {len(results)} results (expected: 1)")
    
    print("\n--- Searching as Nurse ---")
    results = store.search_with_rbac(mock_embedding, "nurse")
    print(f"Found {len(results)} results (expected: 0)")
    
    print("\n--- Searching as Admin ---")
    results = store.search_with_rbac(mock_embedding, "admin")
    print(f"Found {len(results)} results (expected: 1)")
```

### Practice Exercise
- [ ] Start Qdrant with Docker
- [ ] Create vector store and init collection
- [ ] Add 5 test chunks with different access_roles
- [ ] Search as different roles, verify RBAC filtering works
- [ ] Verify that nurse cannot access clinical data, doctor cannot access billing

### Checklist
- [ ] Qdrant running and accessible on localhost:6333
- [ ] Collection initialized
- [ ] add_chunk() method working
- [ ] search_with_rbac() enforcing filters correctly
- [ ] No role can access collections outside their permissions


---

# Phase 3: Embeddings & LLM Integration (Groq + local embeddings)
**Time: 2-3 hours | Difficulty: ⭐⭐**

### What You'll Learn
- How embeddings work
- How to use Groq's API for chat completions
- How to generate embeddings for chunks

### Learning Resources
| Topic | Resource | Time |
|-------|----------|------|
| Embeddings 101 | [Sentence Transformers](https://www.sbert.net/) | 20 min |
| Local Embeddings | [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | 15 min |
| Groq API Basics | [Groq Documentation](https://console.groq.com/docs/quickstart) | 30 min |
| Error Handling | [Groq Error Codes](https://console.groq.com/docs/errors) | 15 min |

### Implementation Tasks

**Step 3.1: Get API keys**
```bash
# 1. Create a Groq key at https://console.groq.com/keys
# 2. Add it to .env
echo "GROQ_API_KEY=gsk-your-key-here" >> .env
echo "GROQ_MODEL=llama-3.3-70b-versatile" >> .env
```

**Step 3.2: Create embedding service**
```bash
# Add to requirements.txt
pip install sentence-transformers groq
```

```python
# Create: src/embeddings.py

from sentence_transformers import SentenceTransformer
from typing import List
import time

class EmbeddingService:
    """Generate local embeddings with Sentence Transformers."""
    
    def __init__(self):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single piece of text.
        Returns: 384-dimensional vector
        """
        try:
            return self.model.encode(text).tolist()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Embed multiple texts efficiently.
        The embedding provider has rate limits, so we batch and add delays.
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            print(f"Embedding batch {i//batch_size + 1}...")
            
            try:
                embeddings.extend(self.model.encode(batch).tolist())
                
                # Rate limiting
                time.sleep(1)
            
            except Exception as e:
                print(f"Error in batch: {e}")
                return None
        
        return embeddings

# Test
if __name__ == "__main__":
    embed_service = EmbeddingService()
    
    # Single embedding
    text = "The treatment protocol for fever includes paracetamol"
    embedding = embed_service.embed_text(text)
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
```

**Step 3.3: Create LLM service for generation**
```python
# Create: src/llm_service.py

from groq import Groq
from typing import List, Dict
import os

class LLMService:
    """Handle Groq calls for answer generation and SQL translation."""
    
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    def generate_answer(self, question: str, retrieved_chunks: List[Dict]) -> str:
        """
        Generate an answer based on retrieved chunks.
        
        Args:
            question: User's question
            retrieved_chunks: [{"text": "...", "metadata": {...}}, ...]
        
        Returns:
            Generated answer with citations
        """
        # Build context from chunks
        context = "Based on the following information:\n\n"
        for i, chunk in enumerate(retrieved_chunks, 1):
            source = chunk["metadata"]["source_document"]
            section = chunk["metadata"]["section_title"]
            context += f"[{i}] From '{source}' ({section}):\n{chunk['text']}\n\n"
        
        system_prompt = """You are MediBot, an AI assistant for healthcare professionals at MediAssist Health Network.
Your role is to provide accurate, well-sourced answers to medical and operational questions.
Always cite your sources using [1], [2], etc. notation.
If information is not in the provided context, say so clearly."""
        
        user_prompt = f"{context}\n\nQuestion: {question}\n\nPlease provide an answer with citations."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error generating answer: {e}"
    
    def translate_to_sql(self, question: str, schema_info: str) -> str:
        """
        Translate natural language question to SQL.
        Used for SQL RAG.
        
        Args:
            question: Natural language question
            schema_info: Description of database schema
        
        Returns:
            SQL query string
        """
        system_prompt = """You are a SQL expert. Convert natural language questions to SQL queries.
Return ONLY the SQL query, no explanation."""
        
        user_prompt = f"""Database schema:
{schema_info}

Question: {question}

Generate the SQL query:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            sql = response.choices[0].message.content.strip()
            # Clean SQL (remove markdown formatting if present)
            sql = sql.replace("```sql", "").replace("```", "").strip()
            return sql
        
        except Exception as e:
            return f"Error: {e}"
```

### Checklist
- [ ] Groq API key obtained and in .env
- [ ] EmbeddingService created and tested
- [ ] LLMService created and tested
- [ ] Can generate embeddings for text
- [ ] Can generate answers with the LLM

---

# Phase 4: Hybrid Search (Dense + BM25)
**Time: 3-4 hours | Difficulty: ⭐⭐⭐**

### What You'll Learn
- What BM25 (keyword search) is and why it's important for medical text
- How to implement hybrid search combining vectors and keywords
- Why medical queries need both

### Learning Resources
| Topic | Resource | Time |
|-------|----------|------|
| BM25 Explained | [Okapi BM25 Wikipedia](https://en.wikipedia.org/wiki/Okapi_BM25) | 15 min |
| BM25 in Practice | [Elasticsearch BM25 Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html) | 20 min |
| Hybrid Search | [Weaviate: Hybrid Search](https://weaviate.io/blog/hybrid-search-explained) | 20 min |
| Reciprocal Rank Fusion | [RRF Fusion Tutorial](https://towardsdatascience.com/combining-search-results-with-reciprocal-rank-fusion-4e67940fbee9) | 15 min |

### Implementation Tasks

**Step 4.1: Implement BM25 scoring**
```bash
# Add to requirements.txt
pip install rank-bm25
```

```python
# Create: src/bm25_search.py

from rank_bm25 import BM25Okapi
from typing import List, Dict, Tuple
import re

class BM25SearchEngine:
    """
    Implement sparse keyword search using BM25.
    This is essential for medical terminology matching.
    """
    
    def __init__(self):
        self.bm25 = None
        self.documents = []  # Keep reference to original docs
    
    def index_documents(self, chunks: List[Dict]):
        """
        Index chunks for BM25 search.
        
        Args:
            chunks: [{"text": "...", "metadata": {...}}, ...]
        """
        # Tokenize documents
        tokenized_docs = []
        self.documents = chunks
        
        for chunk in chunks:
            # Simple tokenization (in production, use more sophisticated NLP)
            text = chunk["text"].lower()
            # Remove punctuation and split
            tokens = re.findall(r'\w+', text)
            tokenized_docs.append(tokens)
        
        # Initialize BM25
        self.bm25 = BM25Okapi(tokenized_docs)
        print(f"✅ Indexed {len(chunks)} documents with BM25")
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[Dict, float]]:
        """
        Search for relevant documents using BM25.
        
        Returns: [(chunk_dict, score), ...]
        """
        if not self.bm25:
            print("⚠️  BM25 not initialized. Call index_documents() first.")
            return []
        
        # Tokenize query
        query_tokens = re.findall(r'\w+', query.lower())
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Rank by score
        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top results with scores
        results = []
        for idx, score in ranked[:limit]:
            if score > 0:  # Only return positive scores
                results.append((self.documents[idx], score))
        
        return results

# Test
if __name__ == "__main__":
    engine = BM25SearchEngine()
    
    chunks = [
        {"text": "Paracetamol 500mg twice daily for fever", "metadata": {}},
        {"text": "IV cannula size for paediatric patients", "metadata": {}},
        {"text": "Hospital parking policy", "metadata": {}}
    ]
    
    engine.index_documents(chunks)
    results = engine.search("paracetamol fever")
    
    for chunk, score in results:
        print(f"Score: {score:.2f} - {chunk['text'][:50]}...")
```

**Step 4.2: Implement hybrid search fusion**
```python
# Create: src/hybrid_search.py

from typing import List, Dict, Tuple
from src.bm25_search import BM25SearchEngine
from src.embeddings import EmbeddingService
from src.vector_store import QdrantVectorStore

class HybridSearchEngine:
    """
    Combine dense vector search with sparse BM25 search.
    Uses Reciprocal Rank Fusion (RRF) to merge results.
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = QdrantVectorStore()
        self.bm25_engine = BM25SearchEngine()
    
    def setup(self, chunks: List[Dict]):
        """
        Initialize both search engines.
        Must be called after loading all documents.
        """
        # Index for BM25
        self.bm25_engine.index_documents(chunks)
        print("✅ Hybrid search engine initialized")
    
    def reciprocal_rank_fusion(self, 
                               dense_results: List[Tuple[str, float]],
                               sparse_results: List[Tuple[str, float]],
                               k: int = 60) -> List[Tuple[str, float]]:
        """
        Merge two ranked lists using Reciprocal Rank Fusion.
        
        Formula: RRF(d) = sum of 1/(k + rank)
        
        Args:
            dense_results: [(chunk_id, score), ...]
            sparse_results: [(chunk_id, score), ...]
            k: parameter (60 is standard)
        
        Returns: Merged and ranked results
        """
        rrf_scores = {}
        
        # Dense results
        for rank, (chunk_id, score) in enumerate(dense_results):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + rank + 1)
        
        # Sparse results
        for rank, (chunk_id, score) in enumerate(sparse_results):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + rank + 1)
        
        # Sort by RRF score
        merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return merged
    
    def hybrid_search(self, query: str, user_role: str, 
                     limit: int = 10) -> List[Dict]:
        """
        Perform hybrid search (dense + sparse) with RBAC.
        
        Returns: [{"text": "...", "metadata": {...}, "score": 0.85}, ...]
        """
        # 1. Vector search
        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            return []
        
        dense_results_raw = self.vector_store.search_with_rbac(
            query_embedding, user_role, limit=limit*2
        )
        dense_results = [(r["text"], r["score"]) for r in dense_results_raw]
        
        # 2. BM25 search (TODO: Apply RBAC filter to BM25 results)
        sparse_results = self.bm25_engine.search(query, limit=limit*2)
        
        # 3. Fuse results using RRF
        merged = self.reciprocal_rank_fusion(
            dense_results, 
            sparse_results, 
            k=60
        )
        
        # 4. Prepare final results with metadata
        final_results = []
        seen = set()
        
        for chunk_text, rrf_score in merged[:limit]:
            # Find metadata from dense_results_raw
            for r in dense_results_raw:
                if r["text"] == chunk_text and chunk_text not in seen:
                    final_results.append({
                        "text": r["text"],
                        "metadata": r["metadata"],
                        "score": rrf_score
                    })
                    seen.add(chunk_text)
                    break
        
        return final_results

# Test
if __name__ == "__main__":
    hybrid = HybridSearchEngine()
    
    chunks = [
        {
            "text": "Paracetamol 500mg twice daily for fever treatment",
            "metadata": {"collection": "clinical", "section_title": "Treatments"}
        },
        {
            "text": "IV cannula size recommendations for paediatric",
            "metadata": {"collection": "nursing", "section_title": "Procedures"}
        }
    ]
    
    hybrid.setup(chunks)
    
    results = hybrid.hybrid_search(
        query="paracetamol for fever",
        user_role="doctor",
        limit=5
    )
    
    for r in results:
        print(f"Score: {r['score']:.3f} - {r['text'][:50]}...")
```

### Checklist
- [ ] BM25SearchEngine implemented
- [ ] HybridSearchEngine combining dense + sparse
- [ ] Reciprocal Rank Fusion working
- [ ] Test query returns results from both search types

---

# Phase 5: Reranking with Cross-Encoder
**Time: 2-3 hours | Difficulty: ⭐⭐⭐**

### What You'll Learn
- What cross-encoders do (score query + doc pairs jointly)
- Why reranking improves answer quality
- How to use sentence-transformers reranker

### Learning Resources
| Topic | Resource | Time |
|-------|----------|------|
| Cross-Encoders | [SBERT: Cross-Encoders](https://www.sbert.net/docs/pretrained_cross_encoders.html) | 20 min |
| Reranking 101 | [Cohere Reranking Explainer](https://txt.cohere.com/reranking/) | 15 min |
| Sentence-Transformers | [SBERT Docs](https://www.sbert.net/) | 20 min |
| Why Reranking Matters | [Dense Passage Retrieval](https://github.com/facebookresearch/DPR) | 15 min |

### Implementation Tasks

**Step 5.1: Install cross-encoder**
```bash
# Add to requirements.txt
pip install sentence-transformers
```

```python
# Create: src/reranker.py

from sentence_transformers import CrossEncoder
from typing import List, Dict
import torch

class MedicalReranker:
    """
    Rerank retrieved chunks using a cross-encoder.
    This model jointly scores the query and each chunk,
    producing more accurate relevance scores than vector similarity alone.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        """
        Initialize with a medical reranker.
        The ms-marco model works well for medical retrieval.
        
        Alternatives:
        - "cross-encoder/qnli-distilroberta-base" (good for clinical Q&A)
        - "cross-encoder/ms-marco-TinyBERT-L-2-v2" (faster, lighter)
        """
        print(f"Loading cross-encoder: {model_name}")
        self.model = CrossEncoder(model_name)
        print("✅ Cross-encoder loaded")
    
    def rerank(self, query: str, chunks: List[Dict], 
               top_k: int = 3) -> List[Dict]:
        """
        Rerank chunks based on relevance to query.
        
        Args:
            query: The user's question
            chunks: [{"text": "...", "metadata": {...}}, ...]
            top_k: Number of results to keep after reranking
        
        Returns:
            Top-k chunks sorted by reranker score
        """
        if not chunks:
            return []
        
        # Prepare pairs for cross-encoder
        # Format: [(query, chunk_text), ...]
        pairs = [[query, chunk["text"]] for chunk in chunks]
        
        # Get scores
        scores = self.model.predict(pairs)
        
        # Add scores to chunks
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
        
        # Sort by rerank score descending
        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        
        return reranked[:top_k]

# Test
if __name__ == "__main__":
    reranker = MedicalReranker()
    
    query = "What is the treatment for fever in children?"
    
    chunks = [
        {
            "text": "Paracetamol 500mg twice daily for fever",
            "metadata": {"source": "clinical.pdf"}
        },
        {
            "text": "Hospital parking is located at the south entrance",
            "metadata": {"source": "handbook.pdf"}
        },
        {
            "text": "For pediatric fever, use age-appropriate dosing",
            "metadata": {"source": "pediatrics.pdf"}
        }
    ]
    
    reranked = reranker.rerank(query, chunks, top_k=2)
    
    for chunk in reranked:
        print(f"Score: {chunk['rerank_score']:.3f} - {chunk['text'][:60]}...")
```

**Step 5.2: Integrate reranker into hybrid search**
```python
# Update: src/hybrid_search.py (add this method)

def hybrid_search_with_rerank(self, query: str, user_role: str, 
                             initial_limit: int = 20, 
                             final_limit: int = 3) -> List[Dict]:
    """
    Hybrid search + reranking pipeline.
    
    Flow:
    1. Hybrid search retrieves broad candidate set (20)
    2. Cross-encoder reranks to top candidates (3)
    3. Return top results
    """
    from src.reranker import MedicalReranker
    
    # Step 1: Hybrid retrieval (cast wide net)
    candidates = self.hybrid_search(
        query, user_role, limit=initial_limit
    )
    
    if not candidates:
        return []
    
    # Step 2: Rerank with cross-encoder
    reranker = MedicalReranker()
    reranked = reranker.rerank(query, candidates, top_k=final_limit)
    
    return reranked
```

### Checklist
- [ ] Cross-encoder model downloaded
- [ ] MedicalReranker class created
- [ ] Integration with hybrid search done
- [ ] Test: 20 candidates narrowed to 3 by reranker

---

# Phase 6: SQL RAG (Database Queries)
**Time: 3-4 hours | Difficulty: ⭐⭐⭐**

### What You'll Learn
- How to inspect database schemas
- How to use LLMs for SQL generation
- Error handling for SQL execution

### Learning Resources
| Topic | Resource | Time |
|-------|----------|------|
| SQL Basics | [SQL Tutorial - W3Schools](https://www.w3schools.com/sql/) | 1 hour |
| Text2SQL | [SemanticScholar: Text2SQL](https://arxiv.org/abs/2204.00498) | 15 min |
| LangChain SQL | [LangChain SQL Chain](https://python.langchain.com/docs/modules/agents/agent_types/sql_database) | 20 min |
| Database Security | [SQL Injection Prevention](https://www.owasp.org/index.php/SQL_Injection) | 15 min |

### Implementation Tasks

**Step 6.1: Inspect database schema**
```python
# Create: src/database.py

import sqlite3
from typing import Dict, List
import os

class DatabaseConnection:
    """Manage connection to mediassist.db"""
    
    def __init__(self, db_path: str = "data/mediassist.db"):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Open database connection"""
        if not os.path.exists(self.db_path):
            print(f"⚠️  Database not found at {self.db_path}")
            return False
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ Connected to {self.db_path}")
        return True
    
    def get_schema(self) -> Dict:
        """
        Retrieve full schema information.
        Returns structured info for LLM to understand tables.
        """
        if not self.conn:
            return {}
        
        cursor = self.conn.cursor()
        schema = {}
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Get columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            schema[table] = {
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "nullable": col[3] == 0
                    }
                    for col in columns
                ]
            }
        
        return schema
    
    def execute_query(self, sql: str) -> List[Dict]:
        """
        Execute SQL query safely.
        
        Returns: List of result rows as dicts
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            
            # Convert to list of dicts
            return [dict(row) for row in results]
        
        except sqlite3.Error as e:
            print(f"❌ SQL Error: {e}")
            return []
    
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()

# Inspect schema
if __name__ == "__main__":
    db = DatabaseConnection("data/mediassist.db")
    db.connect()
    
    schema = db.get_schema()
    
    import json
    print(json.dumps(schema, indent=2))
    
    db.close()
```

**Step 6.2: Create SQL RAG chain**
```python
# Create: src/sql_rag.py

from typing import Dict, List
from src.database import DatabaseConnection
from src.llm_service import LLMService
import re

class SQLRAGChain:
    """
    SQL RAG Pipeline:
    Question → SQL Query (LLM) → Execute → Answer (LLM)
    """
    
    def __init__(self, db_path: str = "data/mediassist.db"):
        self.db = DatabaseConnection(db_path)
        self.db.connect()
        self.llm = LLMService()
        self.schema = self.db.get_schema()
    
    def format_schema_for_llm(self) -> str:
        """
        Create a readable schema description for the LLM.
        """
        schema_text = "Database Schema:\n\n"
        
        for table, info in self.schema.items():
            schema_text += f"Table: {table}\n"
            schema_text += "Columns:\n"
            
            for col in info["columns"]:
                nullable = "nullable" if col["nullable"] else "NOT NULL"
                schema_text += f"  - {col['name']} ({col['type']}) {nullable}\n"
            
            schema_text += "\n"
        
        return schema_text
    
    def step1_translate_to_sql(self, question: str) -> str:
        """
        Step 1: Use LLM to translate question to SQL.
        """
        schema_text = self.format_schema_for_llm()
        
        system_prompt = """You are a SQL expert for a healthcare database.
Convert the user's question to a SQL query.
Return ONLY the SQL query, no markdown, no explanation.
Use proper SQL syntax for SQLite."""
        
        user_prompt = f"""{schema_text}

Question: {question}

Generate only the SQL query:"""
        
        from groq import Groq
        import os
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        sql = response.choices[0].message.content.strip()
        
        # Clean SQL (remove markdown backticks if present)
        sql = re.sub(r'```sql|```', '', sql).strip()
        
        return sql
    
    def step2_execute_query(self, sql: str) -> List[Dict]:
        """
        Step 2: Execute SQL safely.
        """
        print(f"🔍 Executing SQL: {sql[:100]}...")
        results = self.db.execute_query(sql)
        print(f"✅ Query returned {len(results)} rows")
        return results
    
    def step3_answer_with_results(self, question: str, 
                                  results: List[Dict]) -> str:
        """
        Step 3: Use LLM to generate natural language answer from results.
        """
        from groq import Groq
        import os
        import json
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        results_text = json.dumps(results, indent=2)
        
        system_prompt = """You are MediBot, a healthcare AI assistant.
Given SQL query results, provide a clear, concise answer to the user's question.
Be specific and cite any numbers."""
        
        user_prompt = f"""Question: {question}

Database Results:
{results_text}

Provide a natural language answer:"""
        
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content
    
    def answer(self, question: str) -> str:
        """
        Main entry point: Question → Answer
        Executes all 3 steps.
        """
        print(f"\n📊 SQL RAG: {question}")
        
        # Step 1: Translate to SQL
        sql = self.step1_translate_to_sql(question)
        print(f"Generated SQL: {sql}")
        
        # Step 2: Execute
        results = self.step2_execute_query(sql)
        
        if not results:
            return "No results found for that query."
        
        # Step 3: Generate answer
        answer = self.step3_answer_with_results(question, results)
        
        return answer

# Test
if __name__ == "__main__":
    chain = SQLRAGChain("data/mediassist.db")
    
    answer = chain.answer(
        "How many billing claims were submitted in the last month?"
    )
    
    print(f"\n✨ Answer: {answer}")
```

### Practice Exercises
- [ ] Inspect schema: `python -c "from src.database import *; ..."`
- [ ] Write 2-3 sample SQL queries manually
- [ ] Test SQL→LLM translation on those questions
- [ ] Verify results make sense

### Checklist
- [ ] Database connection working
- [ ] Schema inspection done
- [ ] SQL generation working
- [ ] SQL execution safe (no injection vulnerabilities)
- [ ] Answer generation from results working

---

# Phase 7: FastAPI Backend & Integration
**Time: 4-5 hours | Difficulty: ⭐⭐⭐**

### What You'll Learn
- How to build REST APIs with FastAPI
- Authentication tokens
- CORS and deployment basics

### Learning Resources
| Topic | Resource | Time |
|-------|----------|------|
| FastAPI Basics | [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) | 1 hour |
| Authentication | [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) | 45 min |
| Testing APIs | [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) | 30 min |
| Deployment | [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/) | 20 min |

### Implementation Tasks

**Step 7.1: Create FastAPI app**
```bash
# Add to requirements.txt
pip install fastapi uvicorn pydantic python-jose[cryptography]
```

```python
# Create: src/main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import os
from dotenv import load_dotenv

# Import your modules
from src.hybrid_search import HybridSearchEngine
from src.sql_rag import SQLRAGChain
from src.rbac_config import ROLE_COLLECTION_MATRIX, get_accessible_collections

load_dotenv()

app = FastAPI(
    title="MediBot API",
    description="Healthcare RAG system with RBAC",
    version="1.0.0"
)

# CORS (allow frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engines
hybrid_search = HybridSearchEngine()
sql_rag = SQLRAGChain()

# ====== DATA MODELS ======

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

class ChatRequest(BaseModel):
    question: str
    role: str  # Passed from frontend after auth

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict]  # [{"source_document": "...", "section_title": "...", "collection": "..."}]
    retrieval_type: str  # "hybrid_rag" or "sql_rag"
    role: str

# ====== AUTHENTICATION ======

# Demo credentials (in production, use a real database)
DEMO_USERS = {
    "dr.mehta": {"password": "password123", "role": "doctor"},
    "nurse.priya": {"password": "password123", "role": "nurse"},
    "billing.ravi": {"password": "password123", "role": "billing_executive"},
    "tech.anand": {"password": "password123", "role": "technician"},
    "admin.sys": {"password": "password123", "role": "admin"}
}

@app.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Authenticate user and return session token.
    """
    user = DEMO_USERS.get(req.username)
    
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # In production, create a proper JWT token
    # For now, use a simple token
    token = f"token_{req.username}_{user['role']}"
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"]
    )

# ====== CORE ENDPOINTS ======

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main chat endpoint.
    Routes to hybrid RAG or SQL RAG based on question type.
    """
    question = req.question.strip()
    role = req.role
    
    # Validate role exists
    if role not in ROLE_COLLECTION_MATRIX:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    print(f"\n🤖 Chat request from {role}: {question}")
    
    # Detect if analytical question (for SQL RAG)
    is_analytical = any(keyword in question.lower() for keyword in [
        "how many", "count", "total", "statistics", "trending",
        "which", "list", "what are"
    ])
    
    # Check if user has access to SQL RAG
    can_access_sql = role in ["billing_executive", "admin"]
    
    if is_analytical and can_access_sql:
        # ===== SQL RAG =====
        print("→ Routing to SQL RAG")
        
        try:
            answer = sql_rag.answer(question)
            
            return ChatResponse(
                answer=answer,
                sources=[],  # SQL RAG doesn't have traditional sources
                retrieval_type="sql_rag",
                role=role
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL RAG error: {e}")
    
    else:
        # ===== HYBRID RAG =====
        print("→ Routing to Hybrid RAG")
        
        try:
            # Hybrid search + reranking
            chunks = hybrid_search.hybrid_search_with_rerank(
                query=question,
                user_role=role,
                initial_limit=20,
                final_limit=3
            )
            
            if not chunks:
                accessible = get_accessible_collections(role)
                return ChatResponse(
                    answer=f"No relevant documents found in your accessible collections: {', '.join(accessible)}",
                    sources=[],
                    retrieval_type="hybrid_rag",
                    role=role
                )
            
            # Generate answer using LLM
            from src.llm_service import LLMService
            llm = LLMService()
            answer = llm.generate_answer(question, chunks)
            
            # Format sources
            sources = [
                {
                    "source_document": chunk["metadata"]["source_document"],
                    "section_title": chunk["metadata"]["section_title"],
                    "collection": chunk["metadata"]["collection"]
                }
                for chunk in chunks
            ]
            
            return ChatResponse(
                answer=answer,
                sources=sources,
                retrieval_type="hybrid_rag",
                role=role
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hybrid RAG error: {e}")

@app.get("/collections/{role}")
async def get_collections(role: str) -> Dict:
    """
    Get collections accessible to a role.
    """
    if role not in ROLE_COLLECTION_MATRIX:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    collections = get_accessible_collections(role)
    
    return {
        "role": role,
        "accessible_collections": collections
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "medibot-api"}

# ====== RUN =====

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 7.2: Create startup script**
```bash
# Create: run.sh

#!/bin/bash

# Start Qdrant
echo "Starting Qdrant..."
docker run -d -p 6333:6333 qdrant/qdrant:latest

sleep 2

# Start FastAPI
echo "Starting FastAPI..."
cd /path/to/medibot-project
source venv/bin/activate
python src/main.py
```

**Step 7.3: Test all endpoints**
```bash
# Create: test_api.sh

#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Testing Login ==="
curl -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "dr.mehta", "password": "password123"}'

echo -e "\n\n=== Testing Chat (Hybrid RAG) ==="
curl -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the treatment for fever?", "role": "doctor"}'

echo -e "\n\n=== Testing Chat (SQL RAG) ==="
curl -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many billing claims were processed?", "role": "billing_executive"}'

echo -e "\n\n=== Testing Collections ==="
curl "$BASE_URL/collections/doctor"

echo -e "\n\n=== Testing Health ==="
curl "$BASE_URL/health"
```

### Checklist
- [ ] FastAPI app created
- [ ] All 4 endpoints implemented
- [ ] RBAC enforced at endpoint level
- [ ] CORS configured
- [ ] Test endpoints working
- [ ] Error handling in place

---

# Phase 8: Next.js Frontend (Optional but Highly Recommended)
**Time: 5-6 hours | Difficulty: ⭐⭐⭐**

### What You'll Learn
- React hooks and state management
- API integration
- Role-based UI rendering

### Learning Resources
| Topic | Resource | Time |
|-------|----------|------|
| Next.js Basics | [Next.js Official Tutorial](https://nextjs.org/learn) | 1 hour |
| React Hooks | [React Hooks Documentation](https://react.dev/reference/react) | 45 min |
| API Calls in React | [Fetch API + React](https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Client-side_web_APIs/Fetching_data) | 30 min |
| Tailwind CSS | [Tailwind CSS](https://tailwindcss.com/docs) | 30 min |

### Quick Frontend Setup

```bash
# Create Next.js app
npx create-next-app@latest medibot-frontend
cd medibot-frontend
npm install axios

# Add to package.json
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

```typescript
// app/page.tsx - Login Screen

import { useState } from 'react';

const DEMO_USERS = [
  { username: 'dr.mehta', role: 'doctor' },
  { username: 'nurse.priya', role: 'nurse' },
  { username: 'billing.ravi', role: 'billing_executive' },
  { username: 'tech.anand', role: 'technician' },
  { username: 'admin.sys', role: 'admin' }
];

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();
      
      if (response.ok) {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('role', data.role);
        window.location.href = '/chat';
      } else {
        alert('Login failed');
      }
    } catch (error) {
      alert('Error: ' + error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-center text-gray-900 mb-8">🏥 MediBot</h1>
        
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
            <select
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">Select a demo user...</option>
              {DEMO_USERS.map(user => (
                <option key={user.username} value={user.username}>
                  {user.username} ({user.role})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <button
            type="submit"
            disabled={!username || loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

```typescript
// app/chat/page.tsx - Chat Interface

'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<any>;
  retrieval_type?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [userRole, setUserRole] = useState('');
  const [collections, setCollections] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load user role and collections
    const role = localStorage.getItem('role') || '';
    setUserRole(role);

    fetchCollections(role);
  }, []);

  const fetchCollections = async (role: string) => {
    try {
      const response = await axios.get(`http://localhost:8000/collections/${role}`);
      setCollections(response.data.accessible_collections);
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        question: input,
        role: userRole
      });

      const { answer, sources, retrieval_type } = response.data;

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        sources,
        retrieval_type
      }]);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}`
      }]);
    } finally {
      setInput('');
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">🏥 MediBot</h1>
        
        <div className="mb-6">
          <p className="text-sm font-medium text-gray-700 mb-2">Logged in as</p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="font-semibold text-blue-900 capitalize">{userRole}</p>
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-700 mb-3">Accessible Collections</p>
          <div className="space-y-2">
            {collections.map(col => (
              <div key={col} className="bg-green-50 border border-green-200 rounded px-3 py-2 text-sm text-green-900">
                {col}
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={() => {
            localStorage.clear();
            window.location.href = '/';
          }}
          className="w-full mt-8 bg-red-50 text-red-600 py-2 rounded-lg hover:bg-red-100 text-sm font-medium"
        >
          Logout
        </button>
      </div>

      {/* Chat */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-2xl rounded-lg p-4 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-900'
              }`}>
                <p className="mb-2">{msg.content}</p>
                
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-300 text-sm">
                    <p className="font-semibold mb-2">📚 Sources:</p>
                    {msg.sources.map((src, j) => (
                      <div key={j} className="text-xs bg-gray-100 p-2 rounded mb-1">
                        <p><strong>{src.source_document}</strong></p>
                        <p className="text-gray-600">{src.section_title}</p>
                      </div>
                    ))}
                  </div>
                )}

                {msg.retrieval_type && (
                  <div className="mt-2 text-xs bg-yellow-50 text-yellow-800 px-2 py-1 rounded inline-block">
                    {msg.retrieval_type === 'sql_rag' ? '📊 SQL RAG' : '🔍 Hybrid RAG'}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="text-center text-gray-500">MediBot is thinking...</div>}
        </div>

        {/* Input */}
        <form onSubmit={sendMessage} className="p-6 border-t border-gray-200 bg-white">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a medical question..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

### Checklist
- [ ] Next.js project created
- [ ] Login page with demo users
- [ ] Chat interface built
- [ ] API integration working
- [ ] RBAC display (role + accessible collections)
- [ ] Sources displayed for each answer
- [ ] Retrieval type shown

---

# Complete Project Checklist

## Phase 0: Prerequisites
- [ ] Python 3.9+ installed
- [ ] Virtual environment created
- [ ] Basic knowledge of RAG, APIs, databases

## Phase 1: Document Parsing
- [ ] Docling installed and working
- [ ] PDF → Markdown conversion tested
- [ ] Hierarchical chunker implemented
- [ ] Chunk metadata schema understood

## Phase 2: Vector Database
- [ ] Qdrant running locally
- [ ] Collection created
- [ ] RBAC metadata filtering verified
- [ ] Doctor can access clinical, nurse cannot

## Phase 3: Embeddings
- [ ] Groq API key configured
- [ ] Embedding generation working
- [ ] LLM answer generation working
- [ ] SQL translation working

## Phase 4: Hybrid Search
- [ ] BM25 indexing working
- [ ] Dense search working
- [ ] Reciprocal Rank Fusion implemented
- [ ] Hybrid results better than single method

## Phase 5: Reranking
- [ ] Cross-encoder model loaded
- [ ] Reranker narrows broad candidate set
- [ ] Integration with hybrid search done
- [ ] Quality improvement verified

## Phase 6: SQL RAG
- [ ] Database connection verified
- [ ] Schema inspection working
- [ ] SQL generation accurate
- [ ] Safety validation in place
- [ ] Answer generation from results working

## Phase 7: FastAPI Backend
- [ ] 4 endpoints working (/login, /chat, /collections, /health)
- [ ] RBAC enforced at retrieval layer
- [ ] Routing to hybrid or SQL RAG correct
- [ ] Error handling complete
- [ ] CORS configured

## Phase 8: Next.js Frontend
- [ ] Login with demo users
- [ ] Chat interface functional
- [ ] Role display and collections shown
- [ ] Sources cited
- [ ] RBAC message display

---

# Troubleshooting Guide

### Problem: Embeddings API errors
**Solution**: Check `GROQ_API_KEY` in .env, ensure it is valid, and check Groq rate limits.

### Problem: Vector database not connecting
**Solution**: Verify Qdrant is running (`curl http://localhost:6333/health`), check URL in code.

### Problem: RBAC filter not working
**Solution**: Debug the access_roles metadata, print what roles are being applied, check query filters in Qdrant logs.

### Problem: Reranker too slow
**Solution**: Use a lighter model like `ms-marco-TinyBERT`, reduce candidate set, cache cross-encoder results.

### Problem: SQL generation is wrong
**Solution**: Improve the schema description sent to LLM, add examples to the prompt, test with simple queries first.

---

# Next Steps After Completing This Project

1. **Production Hardening**
   - Use proper JWT tokens (not demo tokens)
   - Add database for users instead of hardcoded dict
   - Implement rate limiting
   - Add logging and monitoring

2. **Advanced RAG**
   - Implement query rewriting (break complex questions into sub-questions)
   - Add conversation history / multi-turn chat
   - Implement dynamic prompting based on retrieval
   - Add feedback loop (users rate answer quality)

3. **Scaling**
   - Move Qdrant to cloud (Qdrant Cloud)
   - Use serverless functions (AWS Lambda, Google Cloud Functions)
   - Add caching layer (Redis)
   - Implement async processing for large documents

4. **Safety**
   - Add PII detection to prevent leaking sensitive data
   - Implement answer confidence scores
   - Add hallucination detection
   - Audit all retrieval queries for compliance

---

**Good luck with your MediBot project! 🚀**
