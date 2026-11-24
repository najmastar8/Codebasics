# pip install langgraph langchain-openai langchain-community faiss-cpu
from typing import TypedDict, List
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langgraph.graph import StateGraph, START, END

# 1. Index documents
docs = [
    "LangGraph builds stateful agent workflows as graphs.",
    "RAG retrieves relevant context and passes it to an LLM.",
    "FAISS is a library for fast vector similarity search.",
]
retriever = FAISS.from_texts(docs, OpenAIEmbeddings()).as_retriever(search_kwargs={"k": 2})
llm = ChatOpenAI(model="gpt-4o-mini")

# 2. State shared between nodes
class State(TypedDict):
    question: str
    context: List[str]
    answer: str

# 3. Nodes: each takes state, returns a partial update
def retrieve(state: State):
    hits = retriever.invoke(state["question"])
    return {"context": [d.page_content for d in hits]}

def generate(state: State):
    ctx = "\n".join(state["context"])
    prompt = f"Answer using only this context:\n{ctx}\n\nQuestion: {state['question']}"
    return {"answer": llm.invoke(prompt).content}

# 4. Graph: START -> retrieve -> generate -> END
g = StateGraph(State)
g.add_node("retrieve", retrieve)
g.add_node("generate", generate)
g.add_edge(START, "retrieve")
g.add_edge("retrieve", "generate")
g.add_edge("generate", END)
app = g.compile()

# 5. Run
print(app.invoke({"question": "What is RAG?"})["answer"])