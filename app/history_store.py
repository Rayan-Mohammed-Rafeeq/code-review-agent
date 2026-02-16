from __future__ import annotations

import hashlib
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class HistoryItem:
    id: str
    username: str
    created_at: float
    source_type: str  # text|file|github
    filename: str
    sha256: str
    language: str
    request: Dict[str, Any]
    response: Dict[str, Any]


class InMemoryHistoryStore:
    """Thread-safe in-memory *recent submissions* store.

    What it's for:
    - Power the UI's "Recent submissions" page.
    - Enable "Compare" between two recent review results.

    What it's *not*:
    - Not a durable database.
    - Not an audit log.

    Storage semantics:
    - Stored only in the API process memory (cleared on restart).
    - Not shared across multiple API instances.
    - Bounded by ``max_items_per_user``.

    This keeps the feature set dependency-free. For a real SaaS, swap this for
    a persistent store (SQLite/Postgres) and add user management.
    """

    def __init__(self, *, max_items_per_user: int = 50):
        self._max = max_items_per_user
        self._lock = threading.Lock()
        self._by_user: Dict[str, List[HistoryItem]] = {}

    def add(
        self,
        *,
        username: str,
        source_type: str,
        filename: str,
        code: str,
        language: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
    ) -> HistoryItem:
        item = HistoryItem(
            id=str(uuid.uuid4()),
            username=username,
            created_at=time.time(),
            source_type=source_type,
            filename=filename,
            sha256=hashlib.sha256(code.encode("utf-8", errors="ignore")).hexdigest(),
            language=language,
            request=request,
            response=response,
        )
        with self._lock:
            arr = self._by_user.setdefault(username, [])
            arr.insert(0, item)
            del arr[self._max :]
        return item

    def list(self, *, username: str, limit: int = 20) -> List[HistoryItem]:
        with self._lock:
            return list(self._by_user.get(username, [])[: max(1, limit)])

    def get(self, *, username: str, item_id: str) -> Optional[HistoryItem]:
        with self._lock:
            for it in self._by_user.get(username, []):
                if it.id == item_id:
                    return it
        return None
