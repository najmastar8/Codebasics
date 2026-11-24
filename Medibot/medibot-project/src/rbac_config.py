from typing import Dict, List


ROLE_COLLECTION_MATRIX: Dict[str, List[str]] = {
	"doctor": ["clinical", "nursing", "general"],
	"nurse": ["nursing", "general"],
	"billing_executive": ["billing", "general"],
	"technician": ["equipment", "general"],
	"admin": ["clinical", "nursing", "billing", "equipment", "general"],
}

COLLECTIONS = frozenset(
	collection
	for collections in ROLE_COLLECTION_MATRIX.values()
	for collection in collections
)


def validate_role(role: str) -> str:
	"""Return a valid role or raise ValueError for an unknown role."""
	if role not in ROLE_COLLECTION_MATRIX:
		raise ValueError(f"Unknown role: {role}")
	return role


def get_accessible_collections(role: str) -> List[str]:
	"""Return the collections accessible to a validated role."""
	validate_role(role)
	return list(ROLE_COLLECTION_MATRIX[role])


def get_access_roles_for_collection(collection: str) -> List[str]:
	"""Return the roles allowed to access a validated collection."""
	if collection not in COLLECTIONS:
		raise ValueError(f"Unknown collection: {collection}")

	return [
		role
		for role, collections in ROLE_COLLECTION_MATRIX.items()
		if collection in collections
	]
