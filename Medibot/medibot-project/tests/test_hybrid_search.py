from src.hybrid_search import HybridSearchEngine
from src.bm25_search import BM25SearchEngine


class FakeEmbeddings:
    def embed_text(self, query):
        return [0.0] * 384


class FakeVectorStore:
    def __init__(self):
        self.roles = []

    def search_with_rbac(self, embedding, role, limit):
        self.roles.append(role)
        return [
            {
                "chunk_id": "clinical-1",
                "score": 0.9,
                "text": "Paracetamol fever treatment",
                "metadata": {"access_roles": ["doctor", "admin"]},
            },
            {
                "chunk_id": "billing-1",
                "score": 0.8,
                "text": "Billing claim details",
                "metadata": {"access_roles": ["billing_executive", "admin"]},
            },
        ]


class FakeBM25:
    def index_documents(self, chunks):
        self.chunks = chunks

    def search(self, query, limit):
        return [
            {
                "chunk_id": "clinical-1",
                "score": 4.0,
                "text": "Paracetamol fever treatment",
                "metadata": {"access_roles": ["doctor", "admin"]},
            },
            {
                "chunk_id": "billing-1",
                "score": 3.0,
                "text": "Billing claim details",
                "metadata": {"access_roles": ["billing_executive", "admin"]},
            },
        ]


def test_rbac_is_applied_to_dense_and_sparse_results():
    vector_store = FakeVectorStore()
    engine = HybridSearchEngine(FakeEmbeddings(), vector_store, FakeBM25())

    results = engine.hybrid_search("paracetamol", "doctor", limit=20)

    assert vector_store.roles == ["doctor"]
    assert [result["chunk_id"] for result in results] == ["clinical-1"]
    assert all("billing" not in result["text"].lower() for result in results)


def test_rrf_combines_shared_results():
    engine = HybridSearchEngine(FakeEmbeddings(), FakeVectorStore(), FakeBM25())

    fused = engine.reciprocal_rank_fusion(
        [("shared", 0.9), ("dense-only", 0.8)],
        [("sparse-only", 4.0), ("shared", 3.0)],
    )

    assert fused[0][0] == "shared"
    assert fused[0][1] == 1 / 61 + 1 / 62


def test_bm25_tokenization_preserves_drug_names_and_icd_codes():
    tokens = BM25SearchEngine._tokenize("Paracetamol 500mg ICD-10 E11.9")

    assert "paracetamol" in tokens
    assert "500mg" in tokens
    assert "icd" in tokens
    assert "10" in tokens
    assert "e11" in tokens
    assert "9" in tokens
