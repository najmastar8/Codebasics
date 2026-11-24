import pytest

from src.rbac_config import (
    get_access_roles_for_collection,
    get_accessible_collections,
    validate_role,
)


def test_nurse_cannot_retrieve_billing_documents():
    assert "billing" not in get_accessible_collections("nurse")
    assert "nurse" not in get_access_roles_for_collection("billing")


def test_technician_cannot_retrieve_clinical_documents():
    assert "clinical" not in get_accessible_collections("technician")
    assert "technician" not in get_access_roles_for_collection("clinical")


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        validate_role("billing_admin")
