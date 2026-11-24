# MediBot: Quick Reference & Resources
> Advanced RAG, Hybrid Search, Reranking & Role-Based Access Control

---

## 📋 Project Overview

**MediBot** is an AI-powered internal assistant for MediAssist Health Network that:
- Enforces role-based document access at the **vector store retrieval layer**
- Parses complex medical PDFs with structural awareness using Docling
- Combines dense vector search + BM25 keyword search (Hybrid RAG)
- Applies cross-encoder reranking to surface most relevant passages
- Answers analytical questions using SQL RAG over a relational database
- Exposes a FastAPI backend + Next.js frontend with RBAC messaging & source citations

---

## 👥 User Roles & Access Matrix

Access is enforced at the **Qdrant retrieval level** using metadata filters — not UI restrictions alone.

| Role | Department | Collections Accessible |
|---|---|---|
| `doctor` | Clinical | Clinical, Nursing, General |
| `nurse` | Clinical | Nursing, General |
| `billing_executive` | Billing & Insurance | Billing, General |
| `technician` | Medical Equipment | Equipment, General |
| `admin` | Executive / IT | **ALL** collections |

**Security Requirement:** A nurse must be **unable** to retrieve billing or equipment docs, even with adversarial prompts. RBAC filter applied before LLM sees results.

---

## 📂 Document Collections & Metadata

| Collection | Documents | Format | Accessible By |
|---|---|---|---|
| `general` | HR handbook, leave policy, code of conduct | PDF | All roles |
| `clinical` | Treatment protocols, drug formulary, diagnostics | PDF + tables | doctor, admin |
| `nursing` | ICU procedures, infection control guidelines | PDF | nurse, doctor, admin |
| `billing` | Billing codes, claim submission guide | PDF / Markdown | billing_executive, admin |
| `equipment` | Equipment manuals, calibration, maintenance | PDF | technician, admin |

**Metadata Schema for Each Chunk:**
```json
{
  "text": "chunk content here",
  "metadata": {
    "source_document": "clinical_handbook.pdf",
    "collection": "clinical",
    "access_roles": ["doctor", "admin"],
    "section_title": "Treatment Protocols",
    "chunk_type": "text"
  }
}
```

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NEXT.JS FRONTEND                            │
│                   (Login + Chat Interface)                           │
└────────────────────┬────────────────────────────────────────────────┘
                     │ HTTP Requests
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ /login    /chat    /collections    /health                 │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │ RBAC ENFORCER                                        │  │   │
│  │  │ (Metadata filter at Qdrant query level)             │  │   │
│  │  └───────────────────────┬──────────────────────────────┘  │   │
│  │                          │                                  │   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │ HYBRID SEARCH ENGINE                                │  │   │
│  │  │ 1. Dense: Sentence Transformers (384-dim)           │  │   │
│  │  │ 2. Sparse: BM25 keyword search                      │  │   │
│  │  │ 3. Fusion: Reciprocal Rank Fusion                   │  │   │
│  │  │ 4. Rerank: Cross-Encoder narrows to top-3           │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  │                       ↓                                  │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │ LLM ANSWER GENERATION (Groq Llama-3.3-70b)          │  │   │
│  │  │ - Create context from top-3 chunks                 │  │   │
│  │  │ - Generate answer with citations                   │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │ SQL RAG (For analytical questions)                  │  │   │
│  │  │ - Translate question to SQL with LLM                │  │   │
│  │  │ - Execute safely against database                   │  │   │
│  │  │ - Summarize results to natural language             │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────┬─────────────┬──────────────────────┬────────────────────────┘
      │             │                      │
      ↓             ↓                      ↓
┌────────────┐ ┌─────────────┐     ┌────────────────┐
│  QDRANT    │ │ Groq API +  │     │ SQLite Database│
│ Vector DB  │ │ Sentence    │     │   (Claims &    │
│            │ │ Transformers│     │ Maintenance)   │
│            │ │             │     │                │
└────────────┘ └─────────────┘     └────────────────┘
```

---

## 📦 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Document Parsing** | Docling | Structural PDF awareness (tables, headings, code) with hierarchical chunking |
| **Vector Store** | Qdrant | RBAC metadata filtering at retrieval layer, dense vector search |
| **Dense Search** | Sentence Transformers (`all-MiniLM-L6-v2`) | Semantic similarity (384-dim embeddings) |
| **Sparse Search** | rank-bm25 | Exact keyword matching for medical terms, drug names, ICD codes |
| **Search Fusion** | Reciprocal Rank Fusion (RRF) | Combine dense + sparse results into single ranked list |
| **Reranking** | Cross-Encoder (`ms-marco-MiniLM-L6-v2`) | Score query+chunk pairs jointly, narrow to top-3 |
| **LLM** | Groq-hosted Llama-3.3-70b | Fast answer generation with citations |
| **SQL RAG** | Native SQLite + LLM | Translate questions to SQL, execute safely, summarize results |
| **Backend** | FastAPI | Type-safe, async, CORS, automatic docs |
| **Frontend** | Next.js + React | Modern chat UI with role badges, source citations |
| **Database** | SQLite (`mediassist.db`) | `claims` and `maintenance_tickets` tables |

---

## 📡 FastAPI Endpoints

| Method | Endpoint | Input | Output |
|--------|----------|-------|--------|
| **POST** | `/login` | `{username, password}` | `{access_token, role}` |
| **POST** | `/chat` | `{question, role}` | `{answer, sources, retrieval_type, role}` |
| **GET** | `/collections/{role}` | Role in URL | `{accessible_collections: [...]}` |
| **GET** | `/health` | None | `{status: "ok"}` |

### `/chat` Response Format

```json
{
  "answer": "Paracetamol 500mg twice daily is recommended for fever...",
  "sources": [
    {
      "source_document": "clinical_handbook.pdf",
      "section_title": "Treatment Protocols",
      "collection": "clinical"
    }
  ],
  "retrieval_type": "hybrid_rag",
  "role": "doctor"
}
```

---

## 🔐 RBAC Security Model

**Critical Principle:** Filter applied at **Qdrant query time**, not after retrieval.

```python
# CORRECT - filter before retrieval
results = qdrant.search(
    query_vector=query_embedding,
    query_filter=Filter(
        must=[FieldCondition(key="access_roles", match=MatchValue(value="doctor"))]
    )
)
```

---

## 🎯 Evaluation Criteria (100 points total)

| Criterion | Points | How to Demonstrate |
|-----------|--------|-------------------|
| RBAC enforced at vector store layer | 25 | 3+ adversarial prompts in README showing RBAC blocks access |
| Document ingestion (Docling + hierarchical) | 20 | README shows chunk structure with section context preserved |
| Hybrid RAG (dense + BM25 + reranking) | 20 | Test retrievals with medical terms; verify better than dense-only |
| SQL RAG (plain Python function) | 15 | Works for 4+ analytical questions (claims, maintenance stats) |
| FastAPI backend | 10 | All endpoints working, RBAC server-side, sources in response |
| Next.js frontend | 5 | Login, chat, role badge, RBAC message, source citations |
| Code quality & README | 5 | Modular code, clear setup instructions, architecture diagram |

---

## 🔗 Key External Resources

### Learning Paths (in priority order)

#### 1. **RAG Fundamentals** (3-4 hours)
- 📚 [DeepLearning.AI: RAG Short Course](https://www.deeplearning.ai/short-courses/retrieval-augmented-generation-llms/) - START HERE
- 📚 [LlamaIndex RAG Concepts](https://docs.llamaindex.ai/en/stable/concepts/rag/)

#### 2. **Vector Databases** (2-3 hours)
- 📚 [Qdrant Official Documentation](https://qdrant.tech/documentation/)
- 📚 [Pinecone: Vector Database Guide](https://www.pinecone.io/learn/vector-database/)

#### 3. **LLM APIs & Embeddings** (2 hours)
- 📚 [Groq API Docs](https://console.groq.com/docs/api-reference)
- 📚 [Sentence Transformers](https://www.sbert.net/)

#### 4. **Document Parsing** (1.5 hours)
- 📚 [Docling GitHub](https://github.com/DS4SD/docling)
- 📚 [Docling Official Docs](https://ds4sd.github.io/docling/)

#### 5. **Backend** (2-3 hours)
- 📚 [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- 📚 [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

#### 6. **Frontend** (2-3 hours)
- 📚 [Next.js Learn](https://nextjs.org/learn)
- 📚 [React Hooks](https://react.dev/reference/react)

---

## 💡 Pro Tips

1. **Start Small**: Test with 5 PDFs first, not 1000
2. **Cache Embeddings**: Save to disk to avoid re-computing
3. **Debug RBAC**: Print before/after filtering to verify it works
4. **Extract SQL**: LLMs wrap SQL in markdown; extract before executing
5. **Monitor Costs**: Track Groq API token usage

---

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <your-repo>
cd medibot-project
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Qdrant
docker run -p 6333:6333 qdrant/qdrant:latest

# 4. Configure .env
cp .env.example .env
# Add your GROQ_API_KEY

# 5. Run backend
python -m uvicorn src.main:app --reload

# 6. Run frontend (in another terminal)
cd frontend && npm run dev

# 7. Open browser
# http://localhost:3000
# Login with: dr.mehta / password123
```

---

## 👥 Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| `dr.mehta` | `password123` | doctor |
| `nurse.priya` | `password123` | nurse |
| `billing.ravi` | `password123` | billing_executive |
| `tech.anand` | `password123` | technician |
| `admin.sys` | `password123` | admin |

---

**For detailed implementation, see MediBot_Learning_Guide.md**
