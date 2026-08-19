"""
Guardrail run logger.

Persists every PipelineResult to MongoDB so the dashboard and eval
runs have a full history to work with. Falls back to an in-memory
list if MongoDB isn't reachable (e.g. running the demo locally without
a Mongo instance) so the rest of the app never breaks because of logging.
"""

from datetime import datetime
from typing import Any, Optional

from guardrails.pipeline import PipelineResult

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class GuardrailLogger:
    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        db_name: str = "guardrails_toolkit",
        collection_name: str = "guardrail_runs",
    ):
        self._memory_log: list[dict] = []  # always kept as a fallback / quick access
        self.collection = None

        if mongo_uri and PYMONGO_AVAILABLE:
            try:
                client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
                client.admin.command("ping")  # fail fast if unreachable
                self.collection = client[db_name][collection_name]
            except Exception as e:
                print(f"[GuardrailLogger] Mongo unavailable, falling back to in-memory log: {e}")
                self.collection = None

    def log(self, result: PipelineResult, text: str = "", **context) -> None:
        record = {
            "stage": result.stage,
            "passed": result.passed,
            "timestamp": result.timestamp,
            "total_latency_ms": result.total_latency_ms,
            "input_text_preview": text[:200],
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "reason": c.reason,
                    "score": c.score,
                    "latency_ms": c.latency_ms,
                    "metadata": c.metadata,
                }
                for c in result.checks
            ],
        }

        self._memory_log.append(record)

        if self.collection is not None:
            try:
                self.collection.insert_one(dict(record))  # copy - insert_one mutates with _id
            except PyMongoError as e:
                print(f"[GuardrailLogger] failed to write to Mongo: {e}")

    def recent(self, limit: int = 50) -> list[dict]:
        """Used by the dashboard when Mongo isn't available, or for quick local checks."""
        if self.collection is not None:
            try:
                cursor = self.collection.find().sort("timestamp", -1).limit(limit)
                return list(cursor)
            except PyMongoError:
                pass
        return self._memory_log[-limit:][::-1]

    def stats(self) -> dict[str, Any]:
        """Quick summary - block rate per check, used by dashboard and eval."""
        records = self.recent(limit=10_000)
        total = len(records)
        if total == 0:
            return {"total_runs": 0}

        check_stats: dict[str, dict[str, int]] = {}
        for record in records:
            for check in record["checks"]:
                name = check["name"]
                check_stats.setdefault(name, {"total": 0, "failed": 0})
                check_stats[name]["total"] += 1
                if not check["passed"]:
                    check_stats[name]["failed"] += 1

        return {
            "total_runs": total,
            "overall_pass_rate": sum(r["passed"] for r in records) / total,
            "per_check": {
                name: {
                    "total": s["total"],
                    "failed": s["failed"],
                    "fail_rate": s["failed"] / s["total"],
                }
                for name, s in check_stats.items()
            },
        }