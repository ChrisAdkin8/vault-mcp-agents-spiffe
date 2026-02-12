"""JSON log formatter for structured audit events."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Each output line is a self-contained JSON object suitable for ingestion
    by log aggregation systems (ELK, Splunk, CloudWatch, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
        }

        # Merge structured audit fields attached by AuditLogger.
        audit_data: dict[str, Any] | None = getattr(record, "audit_data", None)
        if audit_data is not None:
            payload.update(audit_data)
        else:
            payload["message"] = record.getMessage()

        return json.dumps(payload, default=self._serialize)

    @staticmethod
    def _serialize(obj: Any) -> Any:
        """Fallback serialiser for non-JSON-native types."""
        if isinstance(obj, frozenset):
            return sorted(obj)
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, datetime):
            return obj.isoformat() + "Z"
        return str(obj)
