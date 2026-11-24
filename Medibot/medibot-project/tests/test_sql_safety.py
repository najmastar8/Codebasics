import pytest

from src.sql_rag import SQLRAGChain


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO claims VALUES (1)",
        "UPDATE claims SET amount = 0",
        "DELETE FROM claims",
        "DROP TABLE claims",
        "ALTER TABLE claims ADD COLUMN secret TEXT",
        "ATTACH DATABASE 'secret.db' AS secret",
        "SELECT 1; DELETE FROM claims",
    ],
)
def test_sql_mutations_and_multiple_statements_are_rejected(sql):
    with pytest.raises(ValueError):
        SQLRAGChain.validate_sql(sql)


def test_read_only_select_is_allowed():
    assert SQLRAGChain.validate_sql("SELECT COUNT(*) FROM claims;") == (
        "SELECT COUNT(*) FROM claims"
    )


def test_with_query_is_allowed():
    sql = "WITH counts AS (SELECT 1 AS total) SELECT total FROM counts"
    assert SQLRAGChain.validate_sql(sql) == sql
