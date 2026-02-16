from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class User:
    username: str


class InMemoryUserStore:
    """Extremely small demo user store.

    This exists only to support a SaaS-style Register/Login UX without pulling in
    a database dependency. It is NOT suitable for real production auth.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._users: Dict[str, User] = {}

    def exists(self, *, username: str) -> bool:
        u = (username or "").strip().lower()
        if not u:
            return False
        with self._lock:
            return u in self._users

    def create(self, *, username: str) -> User:
        u = (username or "").strip().lower()
        if not u:
            raise ValueError("Username is required")
        with self._lock:
            if u in self._users:
                raise ValueError("Username already exists")
            user = User(username=u)
            self._users[u] = user
            return user

    def get(self, *, username: str) -> Optional[User]:
        u = (username or "").strip().lower()
        if not u:
            return None
        with self._lock:
            return self._users.get(u)
