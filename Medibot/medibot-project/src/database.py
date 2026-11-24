import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


class DatabaseConnection:
	"""Manage the MediAssist SQLite database and its analytical tables."""

	def __init__(self, db_path: Union[str, Path] = "data/mediassist.db") -> None:
		self.db_path = Path(db_path)
		self.connection: Optional[sqlite3.Connection] = None

	def connect(self) -> sqlite3.Connection:
		"""Open the database and create its parent directory when necessary."""
		self.db_path.parent.mkdir(parents=True, exist_ok=True)
		if self.connection is None:
			self.connection = sqlite3.connect(self.db_path)
			self.connection.row_factory = sqlite3.Row
		return self.connection

	def initialize_schema(self) -> None:
		"""Create claims and maintenance ticket tables if they do not exist."""
		connection = self.connect()
		connection.executescript(
			"""
			CREATE TABLE IF NOT EXISTS claims (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				claim_number TEXT NOT NULL UNIQUE,
				patient_id TEXT NOT NULL,
				provider_name TEXT NOT NULL,
				insurance_provider TEXT NOT NULL,
				claim_type TEXT NOT NULL,
				amount REAL NOT NULL CHECK (amount >= 0),
				status TEXT NOT NULL CHECK (
					status IN ('submitted', 'in_review', 'approved', 'denied', 'paid')
				),
				submitted_date TEXT NOT NULL,
				processed_date TEXT,
				created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
			);

			CREATE TABLE IF NOT EXISTS maintenance_tickets (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				ticket_number TEXT NOT NULL UNIQUE,
				equipment_id TEXT NOT NULL,
				equipment_name TEXT NOT NULL,
				issue_description TEXT NOT NULL,
				priority TEXT NOT NULL CHECK (
					priority IN ('low', 'medium', 'high', 'critical')
				),
				status TEXT NOT NULL CHECK (
					status IN ('open', 'in_progress', 'resolved', 'closed')
				),
				assigned_technician TEXT,
				created_date TEXT NOT NULL,
				resolved_date TEXT,
				downtime_hours REAL NOT NULL DEFAULT 0 CHECK (downtime_hours >= 0),
				created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
			);

			CREATE INDEX IF NOT EXISTS idx_claims_status
				ON claims(status);
			CREATE INDEX IF NOT EXISTS idx_claims_submitted_date
				ON claims(submitted_date);
			CREATE INDEX IF NOT EXISTS idx_maintenance_status
				ON maintenance_tickets(status);
			CREATE INDEX IF NOT EXISTS idx_maintenance_priority
				ON maintenance_tickets(priority);
			CREATE INDEX IF NOT EXISTS idx_maintenance_created_date
				ON maintenance_tickets(created_date);
			"""
		)
		connection.commit()

	def get_schema(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
		"""Return table and column information for the connected database."""
		connection = self.connect()
		table_rows = connection.execute(
			"SELECT name FROM sqlite_master "
			"WHERE type = ? AND name NOT LIKE ? ORDER BY name",
			("table", "sqlite_%"),
		).fetchall()

		schema: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
		for table_row in table_rows:
			table_name = table_row[0]
			columns = connection.execute(
				f'PRAGMA table_info("{table_name.replace(chr(34), chr(34) * 2)}")'
			).fetchall()
			schema[table_name] = {
				"columns": [
					{
						"name": column[1],
						"type": column[2],
						"not_null": bool(column[3]),
						"default": column[4],
						"primary_key": bool(column[5]),
					}
					for column in columns
				]
			}
		return schema

	def execute_query(
		self,
		sql: str,
		parameters: Sequence[Any] = (),
	) -> List[Dict[str, Any]]:
		"""Execute a parameterized read query and return rows as dictionaries."""
		if not sql.strip():
			raise ValueError("sql must be a non-empty string")
		if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
			raise ValueError("Only read-only SELECT and WITH queries are supported")

		cursor = self.connect().execute(sql, tuple(parameters))
		return [dict(row) for row in cursor.fetchall()]

	def close(self) -> None:
		"""Close the database connection if it is open."""
		if self.connection is not None:
			self.connection.close()
			self.connection = None


if __name__ == "__main__":
	database = DatabaseConnection()
	database.initialize_schema()
	print("Initialized claims and maintenance_tickets tables")
	database.close()
