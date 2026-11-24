"""Run the YouTube Recipe Writer local regression gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from tube_trainer.router import route_request


def routing_accuracy() -> float:
    rows = [json.loads(line) for line in (PROJECT / "evals" / "routing.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return 0.0
    correct = sum(route_request(row["request"]).intent == row["intent"] for row in rows)
    return correct / len(rows)


baseline = json.loads((PROJECT / "evals" / "baseline.json").read_text(encoding="utf-8"))
routing = routing_accuracy()
test_result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=PROJECT,
    check=False,
)
metrics = {
    "routing_accuracy": routing,
    "test_pass_rate": 1.0 if test_result.returncode == 0 else 0.0,
}
reports = PROJECT / "evals" / "reports"
reports.mkdir(parents=True, exist_ok=True)
(reports / "latest.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

failed = []
for metric, value in metrics.items():
    minimum = baseline.get(metric, 0.0) - baseline["margin"]
    if value < minimum:
        failed.append(f"{metric}={value:.3f} below {minimum:.3f}")

print(json.dumps(metrics, indent=2))
raise SystemExit(1 if failed else test_result.returncode)
