import os
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.hybrid_search import HybridSearchEngine
from src.rbac_config import (
	ROLE_COLLECTION_MATRIX,
	get_accessible_collections,
	validate_role,
)
from src.sql_rag import SQLRAGChain


load_dotenv()

app = FastAPI(title="MediBot API", version="1.0.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:3000"],
	allow_credentials=True,
	allow_methods=["GET", "POST"],
	allow_headers=["Authorization", "Content-Type"],
)

security = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "medibot-development-secret-change-me")
ACCESS_TOKEN_MINUTES = 60

DEMO_USERS: Dict[str, Dict[str, str]] = {
	"dr.mehta": {"password": "password123", "role": "doctor"},
	"nurse.priya": {"password": "password123", "role": "nurse"},
	"billing.ravi": {"password": "password123", "role": "billing_executive"},
	"tech.anand": {"password": "password123", "role": "technician"},
	"admin.sys": {"password": "password123", "role": "admin"},
}


class LoginRequest(BaseModel):
	username: str
	password: str


class LoginResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
	role: str


class ChatRequest(BaseModel):
	question: str
	# Kept for temporary frontend compatibility; authorization ignores it.
	role: Optional[str] = None


class ChatResponse(BaseModel):
	answer: str
	sources: List[Dict[str, Any]]
	retrieval_type: str
	role: str


_hybrid_search: Optional[HybridSearchEngine] = None
_sql_rag: Optional[SQLRAGChain] = None
_llm_service: Optional[Any] = None


def _create_access_token(username: str, role: str) -> str:
	now = datetime.now(timezone.utc)
	payload = {
		"sub": username,
		"role": role,
		"iat": now,
		"exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
	}
	return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _get_current_user(
	credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, str]:
	if credentials is None or credentials.scheme.lower() != "bearer":
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Bearer token required",
			headers={"WWW-Authenticate": "Bearer"},
		)

	try:
		payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
		username = payload.get("sub")
		role = payload.get("role")
		if not isinstance(username, str) or not isinstance(role, str):
			raise JWTError
		validate_role(role)
		if DEMO_USERS.get(username, {}).get("role") != role:
			raise JWTError
		return {"username": username, "role": role}
	except (JWTError, ValueError):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
			headers={"WWW-Authenticate": "Bearer"},
		)


def _get_hybrid_search() -> HybridSearchEngine:
	global _hybrid_search
	if _hybrid_search is None:
		_hybrid_search = HybridSearchEngine()
		indexed_chunks_path = os.path.join("data", "indexed_chunks.json")
		if os.path.exists(indexed_chunks_path):
			with open(indexed_chunks_path, encoding="utf-8") as indexed_file:
				_hybrid_search.setup(json.load(indexed_file))
	return _hybrid_search


def _get_sql_rag() -> SQLRAGChain:
	global _sql_rag
	if _sql_rag is None:
		_sql_rag = SQLRAGChain()
	return _sql_rag


def _get_llm_service() -> Any:
	global _llm_service
	if _llm_service is None:
		from src.llm_service import LLMService
		_llm_service = LLMService()
	return _llm_service


def _is_analytical(question: str) -> bool:
	keywords = (
		"how many",
		"count",
		"total",
		"average",
		"statistics",
		"trend",
		"list all",
	)
	question_lower = question.casefold()
	return any(keyword in question_lower for keyword in keywords)


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
	user = DEMO_USERS.get(request.username)
	if user is None or user["password"] != request.password:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid credentials",
		)

	return LoginResponse(
		access_token=_create_access_token(request.username, user["role"]),
		role=user["role"],
	)


@app.post("/chat", response_model=ChatResponse)
async def chat(
	request: ChatRequest,
	current_user: Dict[str, str] = Depends(_get_current_user),
) -> ChatResponse:
	question = request.question.strip()
	if not question:
		raise HTTPException(status_code=400, detail="Question cannot be empty")

	role = current_user["role"]
	try:
		if _is_analytical(question) and role in {"billing_executive", "admin"}:
			return ChatResponse(
				answer=_get_sql_rag().answer(question),
				sources=[],
				retrieval_type="sql_rag",
				role=role,
			)

		chunks = _get_hybrid_search().hybrid_search(question, role, limit=20)
		if not chunks:
			return ChatResponse(
				answer="No relevant documents found in your accessible collections.",
				sources=[],
				retrieval_type="hybrid_rag",
				role=role,
			)

		answer = _get_llm_service().generate_answer(question, chunks[:3])
		sources = [
			{
				"source_document": chunk["metadata"].get("source_document"),
				"section_title": chunk["metadata"].get("section_title"),
				"collection": chunk["metadata"].get("collection"),
			}
			for chunk in chunks[:3]
		]
		return ChatResponse(
			answer=answer,
			sources=sources,
			retrieval_type="hybrid_rag",
			role=role,
		)
	except Exception as error:
		raise HTTPException(status_code=500, detail="Unable to process chat request") from error


@app.get("/collections/{role}")
async def collections(
	role: str,
	current_user: Dict[str, str] = Depends(_get_current_user),
) -> Dict[str, Any]:
	if role not in ROLE_COLLECTION_MATRIX:
		raise HTTPException(status_code=400, detail="Invalid role")
	if role != current_user["role"]:
		raise HTTPException(status_code=403, detail="Cannot inspect another role's collections")
	return {"role": role, "accessible_collections": get_accessible_collections(role)}


@app.get("/health")
async def health() -> Dict[str, str]:
	return {"status": "ok"}
